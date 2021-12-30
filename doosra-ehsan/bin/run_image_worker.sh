#!/usr/bin/env bash

# directories for logs
mkdir -p /doosra-vpc-be/data/logs/image_worker


# Run celery worker for converting images
sleep 10s  # compensate delay of mysql + web container setup
if [ "$FLASK_CONFIG" == "production" ]; then
  if [ "$DEPLOYED_INSTANCE" == "bleeding" ]; then
    celery -A doosra.tasks.celery_app.celery worker -Q image_conversion_queue --pool=gevent --concurrency=100 --loglevel=info --logfile=/doosra-vpc-be/data/logs/image_worker/${HOSTNAME}_celery.log
  else
    celery -A doosra.tasks.celery_app.celery worker -Q image_conversion_queue --pool=gevent --concurrency=100 --loglevel=info
  fi
else
    celery -A doosra.tasks.celery_app.celery worker -Q image_conversion_queue --pool=gevent --concurrency=100 --loglevel=debug
fi
