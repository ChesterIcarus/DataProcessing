# Setting Up AWS

## Upload

```bash
aws s3 cp [run]/input.zip s3://icarus-simulation-data/matsim/[run]/input.zip
```

## Start

- select appropriate EC2 instance
- verify pricing
- configure security group
- confirm security keys

## Setup

- update and upgrade ubuntu and AWS system packages
- make a data directory
- make a scripts directory
- chmod on directories for non-sudo access
- format and mount additional storage to filesystem
- install additional packages (python, java, git, etc.)
- clone icarus repository from github
- install awscli tool
- configure awscli tool (login)
- fetch simulation input data from S3
- fetch matsim from S3
- unzip fetched data

## Run

- run matsim simulation

## Save

- zip final simulation output
- push output to S3
- terminate EC2 instance
- delete any additional storages
