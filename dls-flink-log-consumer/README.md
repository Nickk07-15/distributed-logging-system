# dls-flink-log-consumer

This directory contains the Flink job service for the distributed logging system.

## Purpose
Flink is used for real-time processing and aggregation of logs. It consumes logs from Kafka, processes them (e.g., filtering, windowing, enrichment), and writes results to Elasticsearch.

## Responsibilities
- Consume logs from Kafka
- Process, aggregate, and enrich log data in real time
- Write processed logs to Elasticsearch

## Technologies
- Apache Flink (Python API)
- Python client: `apache-flink`

## Getting Started
- [Flink Python API Docs](https://nightlies.apache.org/flink/flink-docs-release-1.17/docs/dev/python/overview/)

Subdirectories and implementation files to be added.
