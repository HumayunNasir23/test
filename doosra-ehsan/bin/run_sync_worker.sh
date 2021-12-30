#!/usr/bin/env bash

# directories for logs

CONCURRENCY="${WORKER_CONCURRENCY:-15}"

mkdir -p /doosra-vpc-be/data/logs/sync_worker

# Run celery worker for background tasks
sleep 10s  # compensate delay of mysql + web container setup
if [ "$FLASK_CONFIG" == "production" ]; then
  if [ "$DEPLOYED_INSTANCE" == "bleeding" ]; then
    celery -A doosra.tasks.celery_app.celery worker -Q sync_queue -c $CONCURRENCY --loglevel=info --logfile=/doosra-vpc-be/data/logs/sync_worker/${HOSTNAME}_celery.log
  else
    celery -A doosra.tasks.celery_app.celery worker -Q sync_queue -c $CONCURRENCY --loglevel=info
  fi
else
    celery -A doosra.tasks.celery_app.celery worker -Q sync_queue -c $CONCURRENCY --loglevel=info
fi
