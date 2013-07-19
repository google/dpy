#!/usr/bin/python
import logging
from ioc import *

logging.basicConfig(level=logging.DEBUG)
@Inject
def foo(a, b=INJECTED):
  print a, b

@Injectable
@Eager
@Singleton
def b():
  print 'b'
  return 42

@Injectable
@Eager
@Singleton
def c():
  print 'c'
  return 43

@Inject
class bar(object):
  def __init__(self, a, b=INJECTED, c=INJECTED, val=INJECTED):
    print a, b, c, val

Injectable.value('val', 44)

Warmup()
print 'warm'

foo(4)
bar(3, c=5)
