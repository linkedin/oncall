from ...constants import SUPPORTED_TIMEZONES
from ujson import dumps as json_dumps


def on_get(req, resp):
    resp.body = json_dumps(SUPPORTED_TIMEZONES)