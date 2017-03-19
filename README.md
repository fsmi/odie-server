# odie-server #

[![Gitter](https://badges.gitter.im/gitterHQ/gitter.png)](https://gitter.im/fsmi/odie?utm_source=badge&utm_medium=badge&utm_campaign=pr-badge&utm_content=badge)

Postgres backend for [odie](https://github.com/fsmi/odie-client). See Odie in action at [our student council site](https://fsmi.uni-karlsruhe.de/odie).

## Setup ##

To install python-level dependencies: `pip install -r requirements.txt`  
You'll need a running postgres instance with two databases called "garfield" and "fsmi".  
(execute `createdb garfield` and `createdb fsmi` as your postgres user (or use the `-O` parameter) to create them.)

Use `scripts/fill_data.py` to create all necessary schemas and tables in your local postgresql instance and to fill it with some sample data.
If you want to set up the database but don't want any sample data to be created in there, use `scripts/create_schemas_and_tables.py`.

To run the server, execute `./scripts/run_odie.py`.

## Development ##

Odie is made of three logical units: the database models (found in `db/`), the api (for regular users) and the admin interface (for direct db access).

Here's a small map of the api side of the project:
* `routes/*.py`  
  The flask routes live here. We're using [marshmallow](http://marshmallow.readthedocs.org) for all our (de)serialization needs so we don't have to implement shotgun parsers everywhere.
* `db/accounting.py`  
  The accounting backend. We insert all accounting information into the `garfield` database through this. Should garfield itself ever die and get replaced with something else, this is where you'll need to add new accounting hooks.
* `db/*.py`  
  Declarative definition of the database tables we use. These include parts of the `garfield` database (into which we save all documents and their associated data) and parts of the `fsmi` database (which we query for user auth)
* `api_utils.py`  
  We're using Flask, Flask-login, SQLAlchemy, jsonquery and marshmallow. That means a lot of work is done for us and what's left of most API endpoints is mostly boilerplate for stringing all of this together. `api_utils.py` is where we abstract all of that away, too, so most API endpoints can be generated with a simple call to `api_utils.endpoint`. Also found there: grab bag of small utility functions that would only clutter routes.py.
* `barcode/barcode.py`  
  This is where barcode scanner support lives. It also handles putting barcodes on transcripts.
* `admin/`
  Database admin panel. The admin panel is built using Flask-Admin, which means it runs entirely server-side, unlike the rest of odie. Since this already does all of the heavy lifting for us, we only massage / tweak it to fit our needs. Coaxing it into doing what we need it to can be a bit fiddly. Before adding "just one more patch", please consider whether a rewrite wouldn't be more appropriate. (don't let fsdeluxe happen again.)

The rest of the files should be fairly straight-forward. Godspeed.
