from apache.kafka import KafkaConsumerClient, KafkaConsumerConfig, KafkaRecordsConsumerAbstract

class SimpleProcessor(KafkaRecordsConsumerAbstract):
    def process_records(self, records, partition=None):
        for record in records:
            print(f"Received message: {record.value().decode()} from partition: {partition}")

consumer_config = KafkaConsumerConfig(
    group_id="test-group",
    bootstrap_servers="localhost:9092",
    batch_size=1
)
consumer = KafkaConsumerClient(consumer_config, ["test-topic"], SimpleProcessor())

try:
    consumer.poll_and_process()
except KeyboardInterrupt:
    print("Stopping consumer...")
    consumer.close()