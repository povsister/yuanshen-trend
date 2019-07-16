from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
import traceback
from json import dumps
from urllib.parse import urlparse, unquote
from sourcelib.basiclib import get_query_as_dict

from sourcelib.TapTap import SourceTapTap


class YS_Factory:

    @staticmethod
    def factory(url, action):
        CLASS_DICT = {
            'www.taptap.com': SourceTapTap
        }
        parsed_url = urlparse(url)
        selected_class = CLASS_DICT.get(parsed_url.netloc)
        return selected_class(parsed_url, action)


class YS_HTTPHandler(BaseHTTPRequestHandler):

    __software_version = 'ys-trend/0.1'

    def __writeHeaders(self):
        self.send_header('Content-type', 'application/json')
        self.send_header('X-Powered-By', self.__software_version)
        self.end_headers()

    def __respond(self, code, js):
        self.send_response(code)
        self.send_header('Content-Length', str(len(js)))
        self.__writeHeaders()
        self.wfile.write(js)
        self.wfile.flush()

    def respond(self, js):
        self.__respond(200, js)

    def respondNotFond(self):
        js = dumps({
            'msg': 'not implemented'
        }).encode('utf8')
        self.__respond(404, js)

    def do_GET(self):
        # Incoming request like http://127.0.0.1:1551/?url=xxx&action=xxx
        # self.path looks like /?url=xxx&action=xxx
        print('[Query Path]:', unquote(self.path))
        query = get_query_as_dict(self.path)
        try:
            if query.get('url') is not None:
                lib = YS_Factory.factory(query['url'], query)
                data = lib.getJSON()
                self.respond(data)
            else:
                self.respondNotFond()
        except Exception:
            traceback.print_exc()


if __name__ == '__main__':
    server = ThreadingHTTPServer(('', 1571), YS_HTTPHandler)
    server.serve_forever()
