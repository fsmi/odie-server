# fix up python path to enable all these scripts to live in a subdirectory
# I just wish python's relative "from .. import" did what it says on the tin

import sys
import os
sys.path.append(os.path.join(os.path.dirname(__file__), os.path.pardir))
sys.path.append(os.path.dirname(__file__))
