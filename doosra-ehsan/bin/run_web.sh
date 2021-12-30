#!/usr/bin/env bash

# run latest migrations
sleep 10s  # compensate delay of mysql container setup
python manage.py deploy

# directories for logs
mkdir -p /doosra-vpc-be/data/logs/web/

# run web server
if [ "$FLASK_CONFIG" == "production" ]; then
  if [ "$DEPLOYED_INSTANCE" == "bleeding" ]; then
    gunicorn --access-logfile "/doosra-vpc-be/data/logs/web/${HOSTNAME}_access.log" --error-logfile "/doosra-vpc-be/data/logs/web/${HOSTNAME}_error.log" --log-level info --worker-class gevent --workers=3 --timeout 60 --bind 0.0.0.0:8081 manage:app
  else
    gunicorn --access-logfile "-" --error-logfile "-" --log-level info --worker-class gevent --workers=3 --timeout 60 --bind 0.0.0.0:8081 manage:app
  fi
else
    gunicorn --reload --access-logfile "-" --error-logfile "-" --log-level info --worker-class gevent --workers=3 --timeout 60 --bind 0.0.0.0:8081 manage:app
fi
