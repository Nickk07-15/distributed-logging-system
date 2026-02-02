python3.11 -m venv venv
source venv/bin/activate
mkdir -p logs
pip install -r requirements/dist.txt
pip install -r requirements/dev.txt
cp config/dev.sample.json config/dev.json
deactivate