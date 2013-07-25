#!/usr/bin/python
import logging
import sys
import threading
from ioc import *

logging.basicConfig(level=logging.DEBUG)


@Inject
def foo(a, b=INJECTED, c=INJECTED):
  print a, b, c.d


@Injectable
@Singleton(eager=True)
def b():
  print 'Creating b'
  return 'Injected[b]'


@Injectable
@Singleton(eager=True)
class c(object):
  def __init__(self, b=INJECTED):
    print 'Initing c'
    self.d = 43


@Inject
class bar(object):
  def __init__(self, a, b=INJECTED, c=INJECTED, val=INJECTED):
    print a, b, c.d, val


@Injectable
def d(b=INJECTED):
  return 'Injected[d#0]'


Injectable.value('val', 'Injected[val]')

Warmup()

foo(4)
bar(3)
bar(3, val='Overwritten[val]')

try:
  Injectable.value('d', 'Should conflict')
except KeyError:
  print 'OK: Cannot define the same name twice....'

@Inject
def PrintThreadName(thread_name=IN):
  sys.stdout.write('Hello from %s!\n' % thread_name)

class T(threading.Thread):

  @Scope
  def run(self):
    thread_name = threading.current_thread().name
    Injectable.value('thread_name', thread_name)
    for _ in xrange(4):
      PrintThreadName()

T().start()
T().start()
