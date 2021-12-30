#!/usr/bin/env bash

rm celerybeat.pid

# directories for logs
mkdir -p /doosra-vpc-be/data/logs/scheduler


# Run celery worker for background tasks
sleep 1.5m  # compensate delay of mysql + web container setup

if [ "$DEPLOYED_INSTANCE" == "bleeding" ]; then
  celery -A doosra.tasks.celery_app.celery beat --loglevel=info --logfile=/doosra-vpc-be/data/logs/scheduler/${HOSTNAME}_celery.log
else
  celery -A doosra.tasks.celery_app.celery beat --loglevel=info
fi
