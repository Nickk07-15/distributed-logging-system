#!/usr/bin/env python3
"""
Main entry point for the Kafka Broker module, initializes and starts the Kafka Broker using the KafkaInitializer.
"""

import logging

from modules.initialize import KafkaInitializer

from app_config import print_app_config, set_trace, cfg


logger = logging.getLogger(__name__)


def main():
    """
    Main entry point for the Kafka Broker module, initializes and starts the Kafka Broker using the KafkaInitializer.

    """
    logger.info("Starting Kafka Broker")
    kafka_broker = KafkaInitializer(
        kafka_props_=vars(cfg.KAFKA_BROKER), zookeeper_props_=vars(cfg.ZOOKEEPER)
    )
    kafka_broker.start()


if __name__ == "__main__":
    logger.info("Starting dls-kafka-broker service ...")
    print_app_config()
    set_trace()
    main()
