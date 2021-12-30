#!/usr/bin/env bash

celery -A doosra.tasks.celery_app.celery worker -Q workflow_initiator_queue --loglevel=info
