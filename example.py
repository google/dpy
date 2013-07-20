#!/usr/bin/python
import logging
from ioc import *

logging.basicConfig(level=logging.DEBUG)


@Inject
def foo(a, b=INJECTED, c=INJECTED):
  print a, b, c.d


@Injectable
@Eager
@Singleton
def b():
  print 'Creating b'
  return 'Injected[b]'


@Injectable
@Eager
@Singleton
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

with InjectScope('for D#1'):
  Injectable.value('d', 'Injected[d#1]')
  foo(4)
foo(4)
bar(3)

with InjectScope('for D#2'):
  Injectable.value('d', 'Injected[d#2]')
  foo(4)
  with InjectScope('Nested D#1-1') as scope:
    scope.InjectableValue('d', 'Injected[d#2-1]')
    foo(4)
    print scope
bar(3, val='Overwritten[val]')

try:
  Injectable.value('d', 'Should conflict')
except KeyError:
  print 'OK: Cannot define the same name twice....'
