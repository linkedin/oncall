from sqlalchemy import create_engine
import ssl

connect = None
DictCursor = None
IntegrityError = None


def init(config):
    global connect
    global DictCursor
    global IntegrityError

    connect_args = {}
    if config['conn'].get('use_ssl'):
        ssl_ctx = ssl.create_default_context()
        connect_args["ssl"] = ssl_ctx

    engine = create_engine(
        config['conn']['str'] % config['conn']['kwargs'],
        connect_args=connect_args,
        **config['kwargs']
    )

    dbapi = engine.dialect.dbapi
    IntegrityError = dbapi.IntegrityError

    DictCursor = dbapi.cursors.DictCursor
    connect = engine.raw_connection
