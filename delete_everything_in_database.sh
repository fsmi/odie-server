#! /usr/bin/env bash

echo "drop schema acl cascade;" | psql -d fsmi
echo "drop schema public cascade;" | psql -d fsmi
echo "drop schema odie cascade;" | psql -d fsmi
echo "drop schema documents cascade;" | psql -d fsmi
echo "create schema public;" | psql -d fsmi