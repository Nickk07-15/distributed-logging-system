#!/bin/bash

# Stop and remove old containers if they exist
(docker stop kafka-broker zookeeper || true)
(docker rm kafka-broker zookeeper || true)

# Create a user-defined network if it doesn't exist
docker network inspect dls-net >/dev/null 2>&1 || \
  docker network create dls-net

# Deploy Zookeeper using Docker on the custom network
docker run -d \
  --name zookeeper \
  --network dls-net \
  -p 2181:2181 \
  -e ZOOKEEPER_CLIENT_PORT=2181 \
  confluentinc/cp-zookeeper:7.4.0

# Wait for Zookeeper to be ready (max 20s)
echo "Waiting for Zookeeper to be ready..."
for i in {1..20}; do
  if docker exec zookeeper nc -z localhost 2181; then
    echo "Zookeeper is up!"
    break
  fi
  sleep 1
done

# Deploy Kafka Broker on the custom network
docker run -d \
  --name kafka-broker \
  --network dls-net \
  -p 9092:9092 \
  -e KAFKA_ZOOKEEPER_CONNECT=zookeeper:2181 \
  -e KAFKA_ADVERTISED_LISTENERS=PLAINTEXT://localhost:9092 \
  -e KAFKA_LISTENERS=PLAINTEXT://0.0.0.0:9092 \
  -e KAFKA_OFFSETS_TOPIC_REPLICATION_FACTOR=1 \
  -e KAFKA_BROKER_ID=1 \
  confluentinc/cp-kafka:7.4.0

echo "Zookeeper and Kafka Broker are deployed and running ..."

# Optional, for testing purposes, create a topic
docker exec kafka-broker \
  kafka-topics --create --topic test-topic \
  --bootstrap-server localhost:9092 \
  --partitions 1 --replication-factor 1
