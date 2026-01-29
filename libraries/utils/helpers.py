"""
Common Helper functionality for all the services
"""

import os
import logging
import json
from dataclasses import dataclass
from time import time
from decimal import Decimal
from functools import wraps
from abc import ABC, abstractmethod
from datadog import statsd

from monitoring_utils import Metrics, Tags
from aws.sqs import EventProcessorBaseAbstract

logger = logging.getLogger(__name__)


def timeit(func):
    """
    :param func:
    :return:
    """

    @wraps(func)
    def timeit_wrapper(*args, **kwargs):
        """
        :param args:
        :param kwargs:
        :return:
        """
        start_time = time()
        result = func(*args, **kwargs)
        end_time = time()
        logger.info(f"[TIMEIT] Time taken by {func.__name__} is {end_time - start_time} seconds")
        return result

    return timeit_wrapper


def get_val(obj, *keys, default=None) -> any:
    """
    Get value from nested dict
    """
    for key in keys:
        try:
            obj = obj[key]
        except KeyError:
            return default
        except IndexError:
            return default
        except Exception as error:
            logger.warning(f"Error while getting value from nested dict: {error.__class__.__name__}")
            return default
    return obj


def set_val(obj, keys, val, default=None) -> any:
    *keys, last_key = keys
    for key in keys:
        try:
            if isinstance(obj, dict):
                obj = obj.setdefault(key, {})
            elif isinstance(obj, list):
                while len(obj) <= key:
                    obj.append(default)
                obj = obj[key]
            else:
                raise ValueError("obj must be a dictionary or a list")
        except (KeyError, IndexError, TypeError):
            return default
        except Exception as error:
            logger.warning(f"Error while setting value in nested dict: {error.__class__.__name__}")
            return default
    try:
        if isinstance(obj, dict):
            obj[last_key] = val
        elif isinstance(obj, list):
            while len(obj) <= last_key:
                obj.append(default)
            obj[last_key] = val
        else:
            raise ValueError("obj must be a dictionary or a list")
    except Exception as error:
        logger.warning(f"Error while setting value in nested dict: {error.__class__.__name__}")
        return default


class Singleton(type):
    """
    Singleton class to create only one instance of the class in the application
    """
    _instances = {}

    def __call__(cls, *args, **kwargs):
        if cls not in cls._instances:
            cls._instances[cls] = super(Singleton, cls).__call__(*args, **kwargs)
        return cls._instances[cls]


class DecimalEncoder(json.JSONEncoder):
    """
    Class to encode Decimal values to float for json serialization
    """
    def default(self, obj):
        if isinstance(obj, Decimal):
            return f"`{str(obj)}`"      # ` is special, will be removed later
        return super(DecimalEncoder, self).default(obj)


class AbstractDictObject(ABC):
    def __init__(self, dictionary):
        fields = self.__class__.__dict__["__annotations__"].items()
        for k, cls in fields:
            setattr(self, k, cls(dictionary.get(k)))

    def to_dict(self):
        """
        returns dict representation of object
        """
        return self.__dict__.copy()

    def from_dict(self, dict_val):
        """
        from dict to construct object
        """
        self.__dict__.update(dict_val)


@dataclass
class ProcessMessage:
    def __init__(self, msg):
        self.message_type: str = msg.get("message_type")
        self.body: dict = msg.get("body")


class ProcessConsumerAbstract(ABC):
    @abstractmethod
    def __init__(self, msg_body: dict):
        """
        Initializes the task
        Args:
            msg_body (dict): Message body
        """
        pass

    def process(self, msg_body: dict) -> bool:
        """
        Executes the task
        Args:
            msg_body (dict): Message body

        Returns (tuple):
        """
        pass


class TaskConsumerAbstract(ABC):
    @abstractmethod
    def __init__(self, msg_body: dict):
        """
        Initializes the task
        Args:
            msg_body (dict): Message body
        """
        pass

    @abstractmethod
    def execute(self, msg_body: dict) -> bool:
        """
        Executes the task
        Args:
            msg_body (dict): Message body

        Returns (bool): True if task is executed successfully, False otherwise
        """
        pass


# Registry Design Pattern
class ProcessRegistry(metaclass=Singleton):
    def __init__(self):
        self.reg = {}

    def register(self):
        def _add(processor: type[ProcessConsumerAbstract]):
            self.reg[processor.__name__] = processor

        _add(FirstProcessor)  # this process FirstProcessor message
        _add(SecondProcessor)  # this process SecondProcessor message
        _add(ThirdProcessor)  # this process ThirdProcessor message

    def get_tasker(self, msg_type: str, msg_body: dict) -> ProcessConsumerAbstract:
        return self.reg.get(msg_type)(msg_body)


class TaskRegistry(metaclass=Singleton):
    def __init__(self):
        self.reg = {}

    def register(self):
        def _add(tasker: type[TaskConsumerAbstract]):
            self.reg[tasker.__name__] = tasker

        _add(FirstProcessor)
        _add(SecondProcessor)
        _add(ThirdProcessor)

    def get_tasker(self, msg_type: str, msg_body: dict) -> TaskConsumerAbstract:
        return self.reg.get(msg_type)(msg_body)


class FirstProcessor(ProcessConsumerAbstract, TaskConsumerAbstract):
    def __init__(self, msg_body: dict):
        self.msg_body = msg_body

    def process(self, msg_body: dict) -> bool:
        # Process the message
        logger.info(f"Processing FirstProcessor message: {msg_body}")
        return True

    def execute(self, msg_body: dict) -> bool:
        # Execute the task
        logger.info(f"Executing FirstProcessor task: {msg_body}")
        return True


class SecondProcessor(ProcessConsumerAbstract, TaskConsumerAbstract):
    def __init__(self, msg_body: dict):
        self.msg_body = msg_body

    def process(self, msg_body: dict) -> bool:
        # Process the message
        logger.info(f"Processing SecondProcessor message: {msg_body}")
        return True

    def execute(self, msg_body: dict) -> bool:
        # Execute the task
        logger.info(f"Executing SecondProcessor task: {msg_body}")
        return True


class ThirdProcessor(ProcessConsumerAbstract, TaskConsumerAbstract):
    def __init__(self, msg_body: dict):
        self.msg_body = msg_body

    def process(self, msg_body: dict) -> bool:
        # Process the message
        logger.info(f"Processing ThirdProcessor message: {msg_body}")
        return True

    def execute(self, msg_body: dict) -> bool:
        # Execute the task
        logger.info(f"Executing ThirdProcessor task: {msg_body}")
        return True


class TaskEventProcessor(EventProcessorBaseAbstract):
    process_id = -1

    @staticmethod
    def setup():
        """
        initializes sentry
        """
        TaskEventProcessor.process_id = os.getpid()
        TaskRegistry().register()
        logger.info(f"Process Id of Processor : {TaskEventProcessor.process_id}")

    @staticmethod
    @statsd.timed(Metrics.EXEC_TIME, tags=Tags.add(["func:process"]))
    def process(record):
        try:
            logger.info(f"msg: {record}")
            task_message = ProcessMessage(record)
            tasker: TaskConsumerAbstract = TaskRegistry().get_tasker(task_message.message_type, task_message.body)
            return record.get("__message_id"), tasker.execute(task_message.body)
        except Exception as error:
            logger.info(f"Server: Unable to process message: {record}, error: {error}")
            logger.exception(f"Server: Unable to process message: {error.__class__.__name__}")
            return record.get("__message_id"), False
