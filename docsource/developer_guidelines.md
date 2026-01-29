## Developer Guidelines

### Contents
1. [Project Structure](#project-structure)
2. [Naming Conventions](#naming-conventions)
3. [Docstring Format](#docstring-format)
4. [Returning multiple variables from a function](#returning-multiple-variables-from-a-function)
5. [Logging Errors](#logging-errors)

###### Project Structure
```
distributed-logging-system/
├── .idea/
├── docsource/
│   ├── resources/
│   │   ├── ... images and diagrams ...
│   │   └── architecture.svg                    # product/project architecture
│   ├── application_config.md                   # configuration management file
│   ├── problem-statement.md                    # problem statement
│   └── developer_guidelines.md                 # developer guidelines
├── dls-elasticsearch/
│   ├── .idea/
│   ├── docsource/
│   │   ├── resources/
│   │   │   └── dls-elasticsearch_architecture.svg      # service architecture
│   │   └── dls-elasticsearch_release.rst
│   ├── config/
│   │   ├── defaults.json                       # base configuration
│   │   ├── dev.json                            # local config override (git ignored) 
│   │   └── dev.sample.json                     # local config override sample 
│   ├── docker/
│   │   ├── setup.sh                            # docker setup shell script 
│   │   └── Dockerfile                          # service level Dockerfile 
│   ├── requirements/
│   │   ├── dev.txt                             # dev requirements 
│   │   └── dist.txt                            # production requirements  
│   ├── modules/                                # all service level modules
│   │   ├── constants.py                        # service level constants                           
│   │   ├── helpers.py                          # service level utility functions 
│   │   ├── event_processor.py                  # event trigger file
│   │   └── ...
│   ├── scripts/                                # helper scripts for dev testing
│   ├── tests/
│   │   ├── integration/                        # all integration tests
│   │   │   └── fixtures/                       # fixtures for integration tests
│   │   └── unit/                               # all unit tests
│   ├── logs/                                   # local dev directory for logs (git ignored)
│   ├── tmp/                                    # local dev directory for downloads (git ignored)
│   ├── venv/                                   # local virtual environment setup (git ignored)
│   ├── .gitignore                              # service level .gitignore
│   ├── main.py                                 # service entry point
│   ├── monitoring.py                           # monitoring utils
│   ├── setup.sh                                # local service setup shell script
│   └── README.md                               # service level README file
├── libraries/                                  # common functionalities / abstractions across services
│   ├── .idea/
│   ├── venv/                                   # local virtual environment setup (git ignored)
│   ├── .gitignore                              # libraries level .gitignore
│   ├── apache/                                 # apache related abstractions (kafka, flink, etc)
│   ├── aws/                                    # aws related abstractions (s3, kinesis, sqs, etc)
│   ├── db/                                     # common db abstractions (mongo, psql, etc)
│   ├── messaging/                              # common messaging abstractions (rabbitmq, kafka, etc)
│   ├── exceptions/                             # exception directory
│   │   └── custom_exception.py                 # custom exceptions
│   ├── utils/                                  # common utility directory
│   │   ├── file_utils.py                       # All file/directory operations                           
│   │   ├── helpers.py                          # helper functions 
│   │   └── monitoring_utils.py                 # monitoring functions
│   ├── app_config.py                           # application level config setup file
│   ├── requirements.txt                        # dev requirements
│   └── setup.sh                                # local service setup shell script
├── .gitignore                                  # project level .gitignore
├── setup.sh                                    # local project setup shell script
├── scripts/                                    # project level adhoc scripts
└── README.md                                   # project level README
```

###### Naming Conventions
- file_name: sample_file.jpeg
- file: sample_file
- extension: jpeg
- file_path: /tmp/uuid/sample_file.jpeg
- file_relative_path: uuid/sample_file.jpeg

###### Docstring Format
Google style docstring format
```python
def add(number_1: int, number_2: int) -> int:
    """
    Given two numbers add them and return the output
    
    Args:
        number_1 (int): Integer number
        number_2 (int): Integer number
        
    Returns (int):
        Sum of two numbers
    """
    return number_1 + number_2
```

###### Returning multiple variables from a function
Return as a dictionary ideally
```python
import logging

logger = logging.getLogger(__name__)

# returning multiple values using python dictionary
def add(number_1, number_2) -> dict:
    """
    Given two numbers add them and return the output
    
    Args:
        number_1: Integer number
        number_2: Integer number
        
    Returns (dict):
        Sum of two numbers along with it's status
    """
    status = "success"
    try:
        if not (
                isinstance(number_1, int) and 
                isinstance(number_2, int)
        ):
            raise TypeError("Expected type int")
        return {
            "sum": number_1 + number_2,
            "status": status
        }
    except TypeError as error:
        logger.info(f"Type Error: {error}")
        logger.error(f"error: {error.__class__.__name__}")
        status = "fail"
    except Exception as error:
        logger.info(f"Error: {error}")
        logger.error(f"error: {error.__class__.__name__}")
        status = "fail"
    return {
        "sum": None,
        "status": status
    }

vals = add("swe", 5)
print(vals)
```

###### Logging Errors
- `logger.error` needs to preceded by `logger.info` with the details for debugging
```python
try:
    ...
except Exception as error:
    logger.info(f"Caught exception in function, error: {error}")
    logger.error(f"Error: {error.__class__.__name__}")
```
- `logger.error` can be skipped where we have `logger.exception` (this should preferably be in outermost `except`)
```python
try:
    ...
except Exception as error:
    logger.info(f"Caught exception in function, error: {error}")
    logger.error(f"Error: {error.__class__.__name__}")
    logger.exception(error)     # preferably be in outermost function's except
```
- The raise statement without any arguments re-raises the last exception.
This is helpful to keep the stacktrace for the last exception, else a new stacktrace is generated
```python
try:
    ...
except Exception as error:
    logger.info(f"Caught exception in function, error: {error}")
    logger.error(f"Error: {error.__class__.__name__}")
    raise
```