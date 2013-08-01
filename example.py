#!/usr/bin/python
#
# This example run a simple webserver that isolate the parameter injection out
# of the actual logic. The real logic method Hello is not depending on any of
# the handler logic and hence it can be easily tested.
#
# To test the example, try link:
#   http://localhost:8000/?greet=Greeting&user=My%20Friend
import BaseHTTPServer
import ioc
import logging
import urlparse
from jazz import jazz


logging.basicConfig(level=logging.DEBUG)


@ioc.Injectable
def user(params=ioc.IN):
  return params['user'][0] if 'user' in params else 'Anonymous'


@ioc.Injectable
def greet(params=ioc.IN):
  return params['greet'][0] if 'greet' in params else 'Hello'


@ioc.Inject
def Hello(greet=ioc.IN, app_name=ioc.IN, user=ioc.IN):
  return '<p>%s: %s %s</p>' % (app_name, greet, user)


class Handler(BaseHTTPServer.BaseHTTPRequestHandler):

  @ioc.Scope
  def do_GET(self):
    self.send_response(200)
    self.send_header('Content-type', 'text/html')
    self.end_headers()
    parsed = urlparse.urlparse(self.path)
    params = urlparse.parse_qs(parsed.query)

    # Inject request scoped shared variable.
    ioc.Injectable.value('params', params)

    self.wfile.write(Hello())


def RunServer():
  port = 8000
  httpd = BaseHTTPServer.HTTPServer(('', port), Handler)
  logging.info('Server running on port: %s', port)
  httpd.serve_forever()


def main():
  # Injecting global constant
  ioc.Injectable.value('app_name', 'Hello pyoc')
  ioc.Warmup()
  RunServer()


if __name__ == '__main__':
  main()
