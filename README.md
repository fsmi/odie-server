# odie-server #

Postgres backend for [odie](https://github.com/fsmi/odie-client).

## Setup ##

You'll need a running postgres instance with two databases called "garfield" and "fsmi".  
(execute `createdb garfield` and `createdb fsmi` as your postgres user (or use the `-O` parameter) to create them.)

Use `fill_data.py` to create all necessary schemas and tables in your local postgresql instance and to fill it with some sample data.
If you want to set up the database but don't want any sample data to be created in there, use `create_schemas_and_tables.py`.
