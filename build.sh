#!/usr/bin/env bash
set -o errexit

pip install -r requirements.txt
python manage.py collectstatic --noinput
# As migracoes rodam no preDeployCommand do render.yaml, depois do build.
