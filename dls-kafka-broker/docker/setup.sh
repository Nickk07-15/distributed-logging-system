#!/bin/bash
set -e

export DEBIAN_FRONTEND="noninteractive"
export TZ=Etc/UTC
ln -snf /usr/share/zoneinfo/$TZ /etc/localtime && echo $TZ > /etc/timezone

apt update && apt upgrade -y
apt-get -y install gcc g++ make openjdk-11-jdk python3-pip curl libproj-dev \
                        proj-data proj-bin libgeos-dev libgdal-dev gdal-bin \
                        unzip unrar p7zip-full openssl cmake libtool \
                        software-properties-common

add-apt-repository ppa:deadsnakes/ppa -y
apt-get update
apt-get install -y python3.11 python3.11-dev

update-alternatives --install /usr/bin/python3 python3 /usr/bin/python3.11 1
curl -sS https://bootstrap.pypa.io/get-pip.py | python3.11

pip3 install testresources==2.0.1
python3 -m pip install --upgrade pip setuptools wheel

mkdir -p /app/logs/
mkdir -p /app/tmp/
pip3 install -r /app/requirements/dist.txt
