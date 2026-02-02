apt-get update
apt update && apt upgrade -y
DEBIAN_FRONTEND="noninteractive" apt-get -y install gcc g++ make openjdk-11-jdk python3-pip curl libproj-dev \
                        proj-data proj-bin libgeos-dev libgdal-dev gdal-bin \
                        unzip unrar p7zip-full openssl cmake libtool
apt install software-properties-common -y
add-apt-repository ppa:deadsnakes/ppa -y
apt install python3.11 -y
update-alternatives --install /usr/bin/python3 python3 /usr/bin/python3.11 1
curl -sS https://bootstrap.pypa.io/get-pip.py | python3.11

pip3 install testresources==2.0.1
python3 -m pip install --upgrade pip setuptools
apt-get install python3.11-dev -y

ln -s /usr/bin/python3.11 /usr/bin/python3
mkdir -p /libraries/
mkdir -p /data/dls-kafka-broker/logs/
mkdir -p /tmp/
pip3 install -r /app/requirements/dist.txt
