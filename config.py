#! /usr/bin/env python3

from default_config import *
try:
    from local_config import *
except ImportError as e:
    if e.name != 'local_config':
        raise
