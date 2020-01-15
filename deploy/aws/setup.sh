#!/bin/bash

sudo apt update
sudo apt upgrade
sudo apt install \
    unzip openjdk-11-jdk awscli

sudo mkdir /data
sudo mkdir /scripts
sudo mkfs -t xfs /dev/nvme0n1
sudo mount /dev/nvme0n1 /data
sudo chmod 777 /data
sudo chmod 777 /scripts

git clone https://github.com/ChesterIcarus/DataProcessing.git /scripts

aws configure
aws s3 cp s3://icarus-simulation-data/matsim/run12/input.zip /data/input.zip
aws s3 cp s3://icarus-simulation-data/matsim/matsim-12.0-SNAPSHOT-release.zip /data/matsim-12.0-SNAPSHOT-release.zip

cd /data
unzip /data/input.zip
unzip /data/matsim-12.0-SNAPSHOT-release.zip
mkdir /data/output
