# odie-server #

Postgres backend for [odie](https://github.com/fsmi/odie-client).

## Setup ##

To install python-level dependencies: `pip install -r requirements.txt`  
You'll need a running postgres instance with two databases called "garfield" and "fsmi".  
(execute `createdb garfield` and `createdb fsmi` as your postgres user (or use the `-O` parameter) to create them.)

Use `scripts/fill_data.py` to create all necessary schemas and tables in your local postgresql instance and to fill it with some sample data.
If you want to set up the database but don't want any sample data to be created in there, use `scripts/create_schemas_and_tables.py`.

To run the server, execute `./run_odie.py`.

## Development ##

Odie is made of three logical units: the database models (found in `db/`), the api (for regular users) and the admin interface (for direct db access).

Here's a small map of the api side of the project:
* `serialization_schemas.py`:  
  If you want to see what the JSON odie expects looks like, look here. We're using [marshmallow](marshmallow.readthedocs.org) for all our (de)serialization needs.
* `db/accounting.py`  
  The accounting backend. We insert all accounting information into the `garfield` database through this. Should garfield itself ever die and get replaced with something else, this is where you'll need to add new accounting hooks.
* `db/*.py`  
  Declarative definition of the database tables we use. These include parts of the `garfield` database (into which we save all documents and their associated data) and parts of the `fsmi` database (which we query for user auth)
* `api_utils.py`  
  We're using Flask, Flask-login, SQLAlchemy, jsonquery and marshmallow. That means a lot of work is done for us and what's left of most API endpoints is mostly boilerplate for stringing all of this together. `api_utils.py` is where we abstract all of that away, too, so most API endpoints can be generated with a simple call to `api_utils.endpoint`. Also found there: grab bag of small utility functions that would only clutter routes.py.

The admin panel is built using Flask-Admin. Since this already does all of the heavy lifting for us, we only massage / tweak it to fit our needs.

The rest of the files should be fairly straight-forward. Godspeed.
