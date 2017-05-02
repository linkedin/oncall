# Copyright (c) LinkedIn Corporation. All rights reserved. Licensed under the BSD-2 Clause license.
# See LICENSE in the project root for license information.

import os
from oncall import utils
from oncall.app import init

init(utils.read_config(os.environ['CONFIG']))
from oncall.app import application  # noqa
