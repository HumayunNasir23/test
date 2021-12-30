#!/usr/bin/env bash

mkdir -p /doosra-vpc-be/data/logs/workflow_manager

celery -A doosra.tasks.celery_app.celery worker -Q workflow_queue --pool=solo --loglevel=info
