#!/usr/bin/env python3
"""
Kafka Initializer Module, config and starts a Kafka Broker
"""
import logging
import docker
from docker.errors import NotFound, APIError
from time import sleep


logger = logging.getLogger(__name__)


class KafkaInitializer:
    """
    Kafka Initializer Module, config and starts a Kafka Broker
    """
    kafka_props = None
    zookeeper_props = None
    _network_name = "dls-net"
    _zookeeper_container_name = "zookeeper"
    _kafka_broker_container_name = "kafka-broker"

    def __init__(self, kafka_props_: dict, zookeeper_props_: dict):
        self.kafka_props = kafka_props_
        self.zookeeper_props = zookeeper_props_
        self.docker_client = docker.from_env()

    def start(self):
        """
        Starts the Zookeeper and Kafka Broker containers using Docker SDK, mirroring deploy.sh logic.
        """

        # Clean up any existing containers
        self.__container_cleanup()

        # Create a Docker network `dls-network` if it doesn't exist
        self.__create_network()

        # Start Zookeeper and Kafka Broker containers
        # Zookeeper
        self.__start_zookeeper()

        # Kafka Broker
        self.__start_kafka_broker()

        logger.info("Zookeeper and Kafka Broker are deployed and running ...")

    def __container_cleanup(self):
        """
        Cleans up any existing containers with the same names to avoid conflicts.

        Returns:
            None

        Raises:
            APIError: If Docker API encounters an error during container removal.

        """
        for name in [self._zookeeper_container_name, self._kafka_broker_container_name]:
            try:
                container = self.docker_client.containers.get(name)
                logger.info(f"Cleaning up container {name} ...")
                container.stop()
                container.remove()
                logger.info(f"Cleaned up container {name} successfully.")
            except NotFound:
                logger.info(f"Container {name} not found, skipping cleanup ...")

            except APIError as api_error:
                logger.info(f"Error while cleaning up container {name}: {api_error}")
                logger.error(f"[ERROR] Error: {api_error}")
                raise

            except Exception as error:
                logger.info(f"Unexpected error while cleaning up container {name}: {error}")
                logger.error(f"[ERROR] Unexpected Error: {error}")
                raise

    def __create_network(self):
        """
        Creates a Docker network if it doesn't already exist.

        Returns:
            None

        """
        try:
            self.docker_client.networks.get(self._network_name)
            logger.info(f"Network {self._network_name} already exists.")
        except NotFound:
            self.docker_client.networks.create(self._network_name)
            logger.info(f"Created network: {self._network_name}")

    def __start_zookeeper(self):
        """
        Starts the Zookeeper Container

        Returns:
            None

        Raises:
            RuntimeError: If Zookeeper does not become ready within 20 seconds.

        """
        logger.info("Starting Zookeeper container ...")
        zookeeper_env = {key.upper(): str(value) for key, value in self.zookeeper_props if not key.startswith("__")}
        zookeeper_image = self.zookeeper_props.get("__image_name")
        try:
            zookeeper = self.docker_client.containers.run(
                zookeeper_image,
                name=self._zookeeper_container_name,
                network=self._network_name,
                ports={"2181/tcp": 2181},
                environment=zookeeper_env,
                detach=True,
                auto_remove=True
            )
            logger.info("Zookeeper container started.")
        except APIError as e:
            logger.error(f"Failed to start Zookeeper: {e}")
            raise

        # Wait for Zookeeper to be ready (max 20s)
        logger.info("Waiting for Zookeeper to be ready ...")
        ready = False
        for _ in range(20):
            try:
                exec_result = zookeeper.exec_run("nc -z localhost 2181")
                if exec_result.exit_code == 0:
                    logger.info("Zookeeper is up!")
                    ready = True
                    break
            except Exception:
                pass
            sleep(1)

        if not ready:
            logger.error("Zookeeper did not become ready in time.")
            raise RuntimeError("Zookeeper not ready")

    def __start_kafka_broker(self):
        """
        Starts the Kafka Broker Container

        Returns:
            None

        """
        # Start Kafka Broker
        logger.info("Starting Kafka Broker container ...")
        kafka_env = {key.upper(): str(value) for key, value in self.kafka_props.items() if not key.startswith("__")}
        kafka_image = self.kafka_props.get("__image_name")
        try:
            kafka = self.docker_client.containers.run(
                kafka_image,
                name=self._kafka_broker_container_name,
                network=self._network_name,
                ports={"9092/tcp": 9092},
                environment=kafka_env,
                detach=True,
                auto_remove=True
            )
            logger.info("Kafka Broker container started.")
        except APIError as e:
            logger.error(f"Failed to start Kafka Broker: {e}")
            raise

        # Optionally, create a test topic
        logger.info("Creating test topic 'test-topic' ...")
        try:
            exec_result = kafka.exec_run(
                "kafka-topics --create --topic test-topic --bootstrap-server localhost:9092 --partitions 1 --replication-factor 1"
            )
            if exec_result.exit_code == 0:
                logger.info("Test topic 'test-topic' created.")
            else:
                logger.warning(f"Failed to create test topic: {exec_result.output.decode()}")
        except Exception as e:
            logger.warning(f"Exception while creating test topic: {e}")
