#!/bin/bash 

poetry init
poetry run pip install -r requirements.txt
poetry run python manage.py migrate
poetry run python seed.py
poetry run python manage.py runserver

