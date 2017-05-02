# Copyright (c) LinkedIn Corporation. All rights reserved. Licensed under the BSD-2 Clause license.
# See LICENSE in the project root for license information.

from webassets import script
import sys

from oncall.ui import assets_env


def main():
    script.main(sys.argv[1:], env=assets_env)


if __name__ == '__main__':
    main()
