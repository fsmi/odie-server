# fix up python path to enable all these scripts to live in a subdirectory
# I just wish python's relative "from .. import" did what it says on the tin

import sys
import os
sys.path = [os.path.join(os.path.dirname(__file__), os.path.pardir), os.path.dirname(__file__)] + sys.path
