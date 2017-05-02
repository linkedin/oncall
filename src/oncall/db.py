# Copyright (c) LinkedIn Corporation. All rights reserved. Licensed under the BSD-2 Clause license.
# See LICENSE in the project root for license information.

from sqlalchemy import create_engine

connect = None
DictCursor = None
IntegrityError = None


def init(config):
    global connect
    global DictCursor
    global IntegrityError

    engine = create_engine(config['conn']['str'] % config['conn']['kwargs'],
                           **config['kwargs'])
    dbapi = engine.dialect.dbapi
    IntegrityError = dbapi.IntegrityError

    DictCursor = dbapi.cursors.DictCursor
    connect = engine.raw_connection
