#! /usr/bin/env python3

import os
import subprocess

ODIE_DIR = os.path.dirname(__file__)

subprocess.call([os.path.join(ODIE_DIR, 'create_garfield_models.py')])
subprocess.call([os.path.join(ODIE_DIR, 'create_fsmi_models.py')])
