import os
import logging
import json
import boto3
import uuid
import copy
from logging.handlers import RotatingFileHandler
from types import SimpleNamespace
from utils.monitoring_utils import Metrics, Tags

logger = logging.getLogger()
cfg = None
masked_json_cfg = None
env = os.getenv('ENVIRONMENT', 'dev').lower()
override_ssm = os.getenv('SSM', None)


def set_trace(trace_id: str = None, add: bool = False):
    prefix = ''
    if add:
        prefix = ContextFilter.trace_id + '-'
    if trace_id:
        ContextFilter.trace_id = prefix + str(trace_id)
    else:
        ContextFilter.trace_id = prefix + str(uuid.uuid4().hex)[:8]


class ContextFilter(logging.Filter):
    """This helper class adds `context` information for each log record to help
    with parsing. The following identifiers are added
        - process_tag
        - trace_id
    """
    process_tag = 'null'
    trace_id = ''

    def filter(self, record):
        if not hasattr(record, 'process_tag'):
            record.process_tag = ContextFilter.process_tag
        if not hasattr(record, 'trace_id'):
            record.trace_id = ContextFilter.trace_id
        if record.name == 'werkzeug':
            return False
        return True


def reconfigure_logger(use_console_logger: bool = False):
    root = logging.getLogger()
    if root.handlers:
        for handler in root.handlers:
            root.removeHandler(handler)
    log_format = cfg.LOGGER.log_format.format(process_tag=cfg.LOGGER.process_tag)
    log_path = os.path.join(cfg.LOGGER.log_dir_root, f'{cfg.LOGGER.process_tag}.log')

    ContextFilter.process_tag = cfg.LOGGER.process_tag
    context_filter = ContextFilter()
    if use_console_logger:
        _handler = logging.StreamHandler()
    else:
        _handler = RotatingFileHandler(log_path,
                                       mode='a', maxBytes=500 * 1024 * 1024,
                                       backupCount=10, encoding=None, delay=False)
    _handler.addFilter(context_filter)

    logging.basicConfig(
        handlers=[_handler],
        level=cfg.LOGGER.log_level,
        format=log_format,
        datefmt='%Y-%m-%d %H:%M:%S')


def reconfigure_monitors(prefix, default_tags):
    Metrics.prefix = prefix
    Tags.default_tags = default_tags


def read_from_file(file_name):
    if not os.path.exists(file_name):
        logger.warning('Config file not found: %s', file_name)
        return {}
    with open(file_name, "r") as config_file:
        str_config = config_file.read()
        json_config = json.loads(str_config)
        service_name = json_config.get("SERVICE_NAME", "")
        json_config = json.loads(str_config
                                 .replace("{env}", env)
                                 .replace("{service_name}", service_name))
        return json_config


def read_ssm_config(ssm_key_format, force=False, service_name=None):
    ssm_key = None
    try:
        aws_region = os.getenv('AWS_REGION', 'us-west-1')
        ssm_key = ssm_key_format.format(env=env, service_name=service_name)
        if env != 'dev' or force:
            logger.info('Fetching ssm parameters for key: %s' % ssm_key)
            client = boto3.client('ssm', region_name=aws_region)
            response = client.get_parameter(Name=ssm_key, WithDecryption=True)
            ssm_response = json.loads(response['Parameter']['Value'])
            ssm_response['SSM_KEY_FORMAT'] = ssm_key
        else:
            ssm_response = {}
    except Exception:
        logger.critical(f'Unable to read parameters from SSM: {ssm_key}')
        raise SystemExit(-1)
    return ssm_response


def nested_set(dct, keys, value):
    for key in keys[:-1]:
        dct = dct.setdefault(key, {})
    dct[keys[-1]] = value


def nested_get(dct, keys):
    for key in keys:
        try:
            dct = dct[key]
        except KeyError:
            return None
    return dct


def update_secrets(json_dict: dict):
    service_name = json_dict.get("SERVICE_NAME")
    for config in json_dict.get("SECRETS").values():
        if isinstance(config, dict) and config.get("enabled"):
            secrets = read_ssm_config(config['ssm_key'], force=True, service_name=service_name)
            if not secrets:
                continue
            for path in config.get('values', {}):
                nested_set(json_dict, path.split('.'), nested_get(secrets, config['values'][path].split('.')))
    return json_dict


def mask_str(unmasked_value: str):
    masked_value = None
    if unmasked_value:
        str_len = len(unmasked_value)
        if str_len > 4:
            mask_chars = str_len - 4
            masked_value = f'{unmasked_value[:2]}{"*" * (mask_chars-1)}{unmasked_value[2+mask_chars:]}'
        else:
            masked_value = f'{"*" * str_len}'
    return masked_value


def mask_secrets(json_dict: dict):
    for config in json_dict.get("SECRETS").values():
        if isinstance(config, dict):
            for path in config.get('values', {}):
                unmasked_value = nested_get(json_dict, path.split('.'))
                nested_set(json_dict, path.split('.'), mask_str(unmasked_value))
    return json_dict


def parse(json_dict: dict) -> SimpleNamespace:
    """
    Converts dict item to SimpleNamespace obj
    :param json_dict:
    :return:
    """
    x = SimpleNamespace()
    _ = [setattr(x, k, parse(v)) if isinstance(v, dict) else setattr(x, k, v) for k, v in json_dict.items()]
    return x


def merge(a: dict, b: dict, path: str = None):
    """
    overwrites values of b into a
    :param a:
    :param b:
    :param path:
    :return:
    """
    if path is None:
        path = []
    for key in b:
        if key in a:
            if isinstance(a[key], dict) and isinstance(b[key], dict):
                merge(a[key], b[key], path + [str(key)])
            elif a[key] == b[key]:
                pass  # same leaf value
            else:
                a[key] = b[key]
        else:
            a[key] = b[key]
    return a


def initialize():
    config_file_path = 'config/defaults.json'
    dev_config_file_path = 'config/dev.json'
    logger.info("Reading from config file %s" % config_file_path)

    global cfg
    cfg = read_from_file(config_file_path)

    ssm_key_format = override_ssm if override_ssm else cfg['SSM_KEY_FORMAT']
    ssm_cfg = read_ssm_config(ssm_key_format, service_name=cfg.get('SERVICE_NAME'))

    if ssm_cfg:
        logger.info("Reading from ssm config params.")
        cfg = merge(cfg, ssm_cfg)
    elif os.path.exists(dev_config_file_path):
        logger.info("Reading from dev config params.")
        local_cfg = read_from_file(dev_config_file_path)
        cfg = merge(cfg, local_cfg)
    if cfg.get("SECRETS").get("enabled"):
        cfg = update_secrets(cfg)

    evaluate_masked_json_config(cfg)
    cfg = parse(cfg)


def evaluate_masked_json_config(json_cfg):
    global masked_json_cfg
    masked_json_cfg = copy.deepcopy(json_cfg)
    masked_json_cfg = mask_secrets(masked_json_cfg)


def print_app_config():
    logger.info("Merged app_config cfg:\n" + json.dumps(masked_json_cfg, indent=4) + "\n")


def validate_ssm(expected_service_name):
    if override_ssm and cfg.SERVICE_NAME != expected_service_name:
        logger.critical(f'Invalid SSM Key was read: {override_ssm}')
        raise SystemExit(-1)
    logger.info(f'Valid SSM Key was read: {override_ssm}')


# Read parameters from SSM or config/*.json file.
initialize()
reconfigure_logger()
