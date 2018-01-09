from ... import db
from ujson import dumps as json_dumps


def on_get(req, resp):
    """
    Get all contact modes
    """
    connection = db.connect()
    cursor = connection.cursor()
    cursor.execute('SELECT `name` FROM `contact_mode`')
    data = [row[0] for row in cursor]
    cursor.close()
    connection.close()
    resp.body = json_dumps(data)
