from abc import ABC
import logging

logger = logging.getLogger()
logging_counter = dict()


def batch_log_error(key: str, batch_size: int, message: str) -> None:
    """
    Batch the Error logs given the key and batch size and the message

    Args:
        key (str): The type of Error
        batch_size (int): The batch size of the error
        message (str): The message to be logged

    Returns (None):

    """
    if key not in logging_counter or logging_counter.get(key) >= batch_size:
        logging_counter[key] = 0
        logger.error(message)
    else:
        logging_counter[key] += 1
        logger.warning(f"ERROR: {message}")


class AddMonitoringPrefix(object):
    """
    Add Monitoring Prefix to the message

    Attributes:
        _arg (tuple): The arguments passed to the class
    """

    def __init__(self, arg):
        self._arg = arg
        prefix = getattr(arg, "prefix")
        for key in dir(arg):
            if not str(key).startswith("__"):
                val = str(getattr(arg, key))
                if not val.startswith(prefix):
                    setattr(self, key, f"{prefix}{val}")
                else:
                    setattr(self, key, val)


class AbstractMetrics(ABC):
    """
    Abstract Metrics class to add prefix to the metrics
    """
    prefix = "dp.service."


class AbstractTags(ABC):
    """
    Abstract Tags class to add prefix to the tags
    """
    default_tags: list = []

    @classmethod
    def add(cls, tags: list = []) -> list:
        """
        Add default_tags to the list of tags

        Args:
            tags (list): List of tags

        Returns (list):
            List of tags with default_tags added

        """
        tags.extend(cls.default_tags)
        return tags


@AddMonitoringPrefix
class Metrics(AbstractMetrics):
    """
    Metrics class to add prefix to the metrics
    """
    EXEC_TIME = "exec_time"


class Tags(AbstractTags):
    """
    Tags class to add prefix to the tags
    """
    pass
