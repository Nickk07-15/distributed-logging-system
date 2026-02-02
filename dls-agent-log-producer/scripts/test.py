from apache.kafka import KafkaProducerClient

producer_config = {
    "bootstrap.servers": "localhost:9092",
}

producer = KafkaProducerClient(producer_config)
producer.put_record("test-topic", {"message": "Hello, Kafka!"})
print("Message sent to Kafka topic 'test-topic'")