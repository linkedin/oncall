from gevent.pywsgi import WSGIServer, WSGIHandler
import sys
from oncall import utils
from oncall.app import get_wsgi_app


class RawURIWSGIHandler(WSGIHandler):
    def get_environ(self):
        env = super(RawURIWSGIHandler, self).get_environ()
        env['RAW_URI'] = self.path
        return env


if __name__ == '__main__':
    application = get_wsgi_app()
    config = utils.read_config(sys.argv[1])
    addr = (config['server']['host'], config['server']['port'])
    print 'Listening on %s...' % (addr,)
    WSGIServer.handler_class = RawURIWSGIHandler
    WSGIServer(addr, application).serve_forever()
