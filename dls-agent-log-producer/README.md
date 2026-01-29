# dls-agent-log-producer

This directory contains the Log Agent service for the distributed logging system.

## Purpose
The log agent collects logs from various services and forwards them to Kafka. It can be customized to collect logs from files, stdout, or other sources.

## Responsibilities
- Collect logs from application services
- Forward logs to Kafka for buffering
- Support different log sources and formats

## Technologies
- Python (custom agent)
- Python client: `kafka-python`

## Getting Started
- [Log Collection Patterns](https://www.elastic.co/guide/en/beats/filebeat/current/filebeat-overview.html)

Subdirectories and implementation files to be added.
