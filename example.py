#!/usr/bin/python
"""A simple example using dpy.

  This example run a simple webserver that isolate the parameter injection out
  of the actual logic. The real logic method Hello is not depending on any of
  the handler logic and hence it can be easily tested.

  To test the example, try link:
    http://localhost:8000/?greet=Greeting&user=My%20Friend
"""
import BaseHTTPServer
import logging
import urlparse

import ioc


logging.basicConfig(level=logging.DEBUG)


@ioc.Injectable
def user(params=ioc.IN):
  return params['user'][0] if 'user' in params else 'Anonymous'


@ioc.Injectable
def greet(params=ioc.IN):
  return params['greet'][0] if 'greet' in params else 'Hello'


@ioc.Inject
def hello(greet=ioc.IN, app_name=ioc.IN, user=ioc.IN):
  return '<p>%s: %s %s</p>' % (app_name, greet, user)


class Handler(BaseHTTPServer.BaseHTTPRequestHandler):

  @ioc.Scope
  def do_GET(self):
    self.send_response(200)
    self.send_header('Content-type', 'text/html')
    self.end_headers()
    parsed = urlparse.urlparse(self.path)
    params = urlparse.parse_qs(parsed.query)

    # Create injectable scoped to the function do_GET.
    ioc.Injectable.value(params=params)

    self.wfile.write(hello())


@ioc.Injectable
@ioc.Singleton
def server(port=ioc.IN):
  logging.info('Creating server on port: %s', port)
  return BaseHTTPServer.HTTPServer(('', port), Handler)


@ioc.Inject
def runServer(server=ioc.IN):
  server.serve_forever()


def main():
  # Creating global constant injectable
  ioc.Injectable.value(app_name='Hello dpy')
  ioc.Injectable.value(port=8000)
  ioc.Warmup()  # Start eager singletons
  ioc.DumpInjectionStack()  # Debug information

  runServer()


if __name__ == '__main__':
  main()
