# odie-server #

Postgres backend for [odie](https://github.com/arrrrr/odie).

## Setup ##

The project targets Python 2.7, but Python 3 should work just as well.

1. Install Django and psycopg2: `pip install -r requirements.txt`
2. Create and populate the prfproto DB: `createdb prfproto && psql -d prfproto -f prfproto.sql` (assuming a local postgres DB and that your unix and postgres accounts coincide)
3. Create odie's own DB: `createdb odie && ./manage.py syncdb`
4. Insert your client by creating a local_settings.py file with something like `STATICFILES_DIR = ['path_to_your_client']`
5. Start the test server using `./manage.py runserver` and navigate to `http://localhost:8000/static/index.html` (assuming your client isn't too hipster for an index.html)
