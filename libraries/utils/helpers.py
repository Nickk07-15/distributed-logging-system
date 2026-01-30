"""
Common Helper functionality for all the services
"""
import logging
from time import time
from functools import wraps
from typing import Any

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


def get_val(obj, *keys, default=None) -> Any:
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


def set_val(obj, keys, val, default=None) -> Any:
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
