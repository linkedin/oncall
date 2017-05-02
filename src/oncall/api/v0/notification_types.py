from ... import db
from ujson import dumps as json_dumps


def on_get(req, resp):
    connection = db.connect()
    cursor = connection.cursor(db.DictCursor)
    cursor.execute('SELECT `name`, `is_reminder` FROM `notification_type`')
    data = cursor.fetchall()
    cursor.close()
    connection.close()
    resp.body = json_dumps(data)
