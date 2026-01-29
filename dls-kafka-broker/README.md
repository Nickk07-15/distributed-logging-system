# dls-kafka-broker

This directory contains the Kafka service for the distributed logging system.

## Purpose
Kafka acts as a message queue and buffer for logs. It decouples log producers (log agents) from consumers (Flink job), ensuring reliable delivery and scalability.

## Responsibilities
- Receive logs from log agents
- Buffer and queue logs for downstream processing
- Ensure reliable, scalable log delivery

## Technologies
- Apache Kafka
- Python client: `kafka-python`

## Getting Started
- [Apache Kafka Quickstart](https://kafka.apache.org/quickstart)

Subdirectories and implementation files to be added.
