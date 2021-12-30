FROM python:3.6

ADD . /doosra-vpc-be
WORKDIR /doosra-vpc-be

# Install pre-requisites
RUN apt-get update && apt-get install -y \
    build-essential \
    default-libmysqlclient-dev \
    python3-dev \
    python3-lxml \
    gcc \
    qemu-utils \
    flex

# Set the C_FORCE_ROOT environment variable for the Celery process, replace later
ENV C_FORCE_ROOT true

RUN pip3 install --upgrade pip
RUN pip3 install -r /doosra-vpc-be/requirements.txt
