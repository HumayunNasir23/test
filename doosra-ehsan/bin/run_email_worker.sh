#!/usr/bin/env bash

# directories for logs
mkdir -p /doosra-vpc-be/data/logs/email_worker


# Run celery worker for sending emails
sleep 10s  # compensate delay of mysql + web container setup

if [ "$DEPLOYED_INSTANCE" == "bleeding" ]; then
    celery -A doosra.common.email.celery worker -Q emailq --loglevel=info --logfile=/doosra-vpc-be/data/logs/email_worker/${HOSTNAME}_celery.log
else
    celery -A doosra.common.email.celery worker -Q emailq --loglevel=info
fi
