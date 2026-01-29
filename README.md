# Distributed Logging System

[Problem Statement](docsource/problem-statement.md)


## Dev Setup
### Pre-requisites
```shell
python3.11 -m venv venv
source venv/bin/activate
pip3 install numpy==2.2.4
python
```

```python
import numpy as np
```

### Setup commands
Iff the pre-requisites are met, run the following commands
```shell
git clone git@github.com:Nickk07-15/distributed-logging-system.git
cd distributed-logging-system
chmod +X setup.sh
./setup.sh
```

#### [Developer Guidelines](docsource/developer_guidelines.md)

Current system follows a microservice level architecture maintained in a mono-repo pattern. Each service has its own setup and configuration files, while common libraries are shared across services.