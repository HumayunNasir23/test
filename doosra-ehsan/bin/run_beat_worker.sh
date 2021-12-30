#!/usr/bin/env bash

# directories for logs

CONCURRENCY="${BEAT_WORKER_CONCURRENCY:-100}"

mkdir -p /doosra-vpc-be/data/logs/beat_worker

# Run celery worker for background tasks
sleep 10s  # compensate delay of mysql + web container setup
if [ "$FLASK_CONFIG" == "production" ]; then
  if [ "$DEPLOYED_INSTANCE" == "bleeding" ]; then
    celery -A doosra.tasks.celery_app.celery worker -Q beat_queue --pool=gevent -c $CONCURRENCY --loglevel=info --logfile=/doosra-vpc-be/data/logs/beat_worker/${HOSTNAME}_celery.log
  else
    celery -A doosra.tasks.celery_app.celery worker -Q beat_queue --pool=gevent -c $CONCURRENCY --loglevel=info
  fi
else
    celery -A doosra.tasks.celery_app.celery worker -Q beat_queue --pool=gevent -c $CONCURRENCY --loglevel=info
fi
