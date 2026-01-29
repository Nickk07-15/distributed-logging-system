"""
Kafka Abstraction Layer (confluent-kafka)
-----------------------------------------
This module provides advanced Python abstractions for interacting with Apache Kafka using the confluent-kafka library.

Features:
- Modular producer and consumer classes
- Batching support
- Offset management and checkpointing
- Multiprocessing for consumer record processing
- Abstract base classes for event and batch processing
- Configuration helpers
- Logging, error handling, and metrics hooks

Installation:
    pip install confluent-kafka

Docs:
    https://docs.confluent.io/platform/current/clients/confluent-kafka-python/html/index.html
"""

import logging
import multiprocessing
import time
import uuid
import threading
from abc import ABC, abstractmethod
from collections import defaultdict
from dataclasses import dataclass, field
from typing import List, Dict, Optional, Type, Any
from confluent_kafka import Producer, Consumer, KafkaException, Message

logger = logging.getLogger("kafka")

@dataclass
class KafkaProcessRecordResponse:
    message_id: str
    status: bool
    data: dict

@dataclass
class KafkaConsumerConfig:
    group_id: str
    bootstrap_servers: str
    auto_offset_reset: str = "earliest"
    enable_auto_commit: bool = True
    poll_timeout: float = 1.0
    batch_size: int = 100
    process_count: int = 1
    checkpoint_freq_in_sec: int = 60

class KafkaMetrics:
    """
    Simple in-memory metrics tracker. Extend for Prometheus/StatsD integration.
    """
    def __init__(self):
        self.lock = threading.Lock()
        self.metrics = defaultdict(int)

    def inc(self, key, value=1):
        with self.lock:
            self.metrics[key] += value

    def get(self, key):
        with self.lock:
            return self.metrics.get(key, 0)

    def snapshot(self):
        with self.lock:
            return dict(self.metrics)

kafka_metrics = KafkaMetrics()

def kafka_error_handler(func):
    """
    Decorator for error handling and metrics in Kafka operations.
    """
    def wrapper(*args, **kwargs):
        try:
            return func(*args, **kwargs)
        except KafkaException as e:
            logger.error(f"KafkaException in {func.__name__}: {e}")
            kafka_metrics.inc('kafka_errors')
            # Optionally, re-raise or handle
        except Exception as e:
            logger.error(f"Exception in {func.__name__}: {e}")
            kafka_metrics.inc('general_errors')
            # Optionally, re-raise or handle
    return wrapper

class KafkaProducerClient:
    def __init__(self, config: Dict[str, Any]):
        self.producer = Producer(config)

    @kafka_error_handler
    def put_record(self, topic: str, data: dict, key: Optional[str] = None, on_delivery=None):
        value = str(data).encode("utf-8")
        self.producer.produce(topic, value=value, key=key, callback=on_delivery or self._delivery_report)
        kafka_metrics.inc('messages_produced')
        self.producer.flush()

    @kafka_error_handler
    def put_records(self, topic: str, records: List[dict], key_field: Optional[str] = None, on_delivery=None):
        for record in records:
            key = record.get(key_field) if key_field else None
            self.put_record(topic, record, key, on_delivery=on_delivery)
        self.producer.flush()

    def _delivery_report(self, err, msg):
        if err is not None:
            logger.error(f"Delivery failed for record {msg.key()}: {err}")
            kafka_metrics.inc('delivery_errors')
        else:
            logger.info(f"Record delivered to {msg.topic()} [{msg.partition()}] at offset {msg.offset()}")
            kafka_metrics.inc('messages_delivered')

class KafkaEventProcessorBaseAbstract(ABC):
    @staticmethod
    @abstractmethod
    def setup():
        pass

    @staticmethod
    @abstractmethod
    def process_batched_data(record_batch: List[Message]):
        pass

    @staticmethod
    @abstractmethod
    def process_single_record(record: Message):
        pass

class KafkaBatchManagerBaseAbstract(ABC):
    @staticmethod
    @abstractmethod
    def pre_process_records_batch(records: List[Message]) -> List[Message]:
        pass

    @staticmethod
    @abstractmethod
    def post_process_records_batch(records: List[Message], status: List[KafkaProcessRecordResponse]) -> List[KafkaProcessRecordResponse]:
        pass

class KafkaRecordsConsumerAbstract(ABC):
    @abstractmethod
    def process_records(self, records: List[Message], partition: str = None):
        pass

class KafkaRecordConsumerBaseImpl(KafkaRecordsConsumerAbstract):
    pool = None

    def __init__(self, processor: Type[KafkaEventProcessorBaseAbstract], process_count: int = 1, batch_manager: Type[KafkaBatchManagerBaseAbstract] = None):
        self.processes = process_count
        self.processor = processor
        self.batch_manager = batch_manager
        self.pool = multiprocessing.Pool(initializer=self.processor.setup, processes=self.processes)

    def process_records(self, records: List[Message], partition: str = None, debug: bool = False) -> int:
        start_time = time.time()
        logger.info(f"Total records to process: {len(records)}")
        if self.batch_manager:
            records = self.batch_manager.pre_process_records_batch(records)
        response = self.pool.map(self.processor.process_single_record, records)
        if self.batch_manager:
            response = self.batch_manager.post_process_records_batch(records, response)
        end_time = time.time()
        logger.info(f"Records processed in {end_time - start_time} sec")
        return sum([1 for record in response if record.status])

class KafkaConsumerClient:
    def __init__(self, config: KafkaConsumerConfig, topics: List[str], record_processor: KafkaRecordsConsumerAbstract):
        self.config = config
        self.topics = topics
        self.record_processor = record_processor
        self.consumer = Consumer({
            'bootstrap.servers': config.bootstrap_servers,
            'group.id': config.group_id,
            'auto.offset.reset': config.auto_offset_reset,
            'enable.auto.commit': config.enable_auto_commit
        })
        self.consumer.subscribe(topics)
        self.last_checkpoint_time = time.time()

    @kafka_error_handler
    def poll_and_process(self):
        batch = []
        while True:
            msg = self.consumer.poll(self.config.poll_timeout)
            if msg is None:
                continue
            if msg.error():
                logger.error(f"Kafka error: {msg.error()}")
                kafka_metrics.inc('consumer_errors')
                continue
            batch.append(msg)
            kafka_metrics.inc('messages_consumed')
            if len(batch) >= self.config.batch_size:
                self.record_processor.process_records(batch, partition=str(msg.partition()))
                kafka_metrics.inc('batches_processed')
                batch = []
            if time.time() - self.last_checkpoint_time > self.config.checkpoint_freq_in_sec:
                self.consumer.commit()
                self.last_checkpoint_time = time.time()

    def close(self):
        self.consumer.close()
        logger.info("Kafka consumer closed.")

# Advanced Feature Example: Dead Letter Queue (DLQ) for failed messages
class KafkaDLQProducer:
    def __init__(self, config: Dict[str, Any], dlq_topic: str):
        self.producer = Producer(config)
        self.dlq_topic = dlq_topic

    @kafka_error_handler
    def send_to_dlq(self, failed_message: Message, reason: str):
        data = {
            'topic': failed_message.topic(),
            'partition': failed_message.partition(),
            'offset': failed_message.offset(),
            'key': failed_message.key().decode() if failed_message.key() else None,
            'value': failed_message.value().decode() if failed_message.value() else None,
            'reason': reason,
            'timestamp': time.time()
        }
        self.producer.produce(self.dlq_topic, value=str(data).encode("utf-8"))
        self.producer.flush()
        kafka_metrics.inc('dlq_messages')
