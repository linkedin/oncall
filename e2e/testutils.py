# Copyright (c) LinkedIn Corporation. All rights reserved. Licensed under the BSD-2 Clause license.
# See LICENSE in the project root for license information.

def prefix(prefix_str):
    def wrapper(function):
        function.prefix = prefix_str
        return function
    return wrapper

def api_v0(path):
    return 'http://localhost:8080/api/v0/%s' % path