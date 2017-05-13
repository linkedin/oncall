from ... import iris
from ujson import dumps as json_dumps


def on_get(req, resp):
    if iris.settings is None:
        resp.body = json_dumps({'activated': False})
    else:
        resp.body = json_dumps(iris.settings)
