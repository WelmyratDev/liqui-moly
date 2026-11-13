PY ?= python

runserver:
	$(PY) manage.py runserver

migrations:
	$(PY) manage.py makemigrations

migrate:
	$(PY) manage.py migrate

collectstatic:
	$(PY) manage.py collectstatic --noinput

createsuperuser:
	$(PY) manage.py createsuperuser

test:
	$(PY) manage.py test

check:
	$(PY) manage.py check --deploy

thumbnails:
	$(PY) manage.py warm_thumbnails

# Was called "loaddata" but actually dumps the DB to data.json (keep it out of git!)
dumpdata:
	$(PY) manage.py dumpdata --natural-foreign --natural-primary -e contenttypes -e auth.Permission --indent 4 > data.json

# Run on the server from /home/ubuntu/liqui_moly/liquimoly with the venv active
deploy:
	pip install -r req.txt
	$(PY) manage.py migrate --noinput
	$(PY) manage.py collectstatic --noinput
	$(PY) manage.py check --deploy
	$(PY) manage.py warm_thumbnails
	sudo supervisorctl restart liquimoly
