FROM ubuntu:22.04 AS base
COPY ./dls-kafka-broker/ /app/
COPY ./libraries/ /libraries/
RUN sh /app/docker/setup.sh
WORKDIR /app/
ENV PYTHONPATH="/libraries:/app:${PYTHONPATH}"
CMD ["python3","./main.py"]