#! /usr/bin/env python3

import os
import subprocess

ODIE_DIR = os.path.dirname(__file__)

# due to Flask-SQLA only using a single MetaData object even when handling multiple
# databases, we can't create let it create all our models at once (otherwise it
# tries to create Enums in all databases, which will fail due to missing schemas)
# We therefor create them db by db, only letting Flask-SQLA know about one db at a time.
# Hence subprocesses instead of simple imports
subprocess.call([os.path.join(ODIE_DIR, 'create_garfield_models.py')])
subprocess.call([os.path.join(ODIE_DIR, 'create_fsmi_models.py')])
