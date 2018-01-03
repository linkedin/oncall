from ... import db
from ujson import dumps as json_dumps


def on_get(req, resp):
    """
    Get all contact modes
    """
    connection = db.connect()
    cursor = connection.cursor(db.DictCursor)
    cursor.execute('SELECT `name`, `label` FROM `contact_mode`')
    data = cursor.fetchall()
    cursor.close()
    connection.close()
    resp.body = json_dumps(data)
