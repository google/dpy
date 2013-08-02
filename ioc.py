"""pyoc is a simple, thread-safe, Python dependency injection library.

pyoc is designed to easily allow inversion of control without messy overhead.
It is quick to define and use injectable objects in your code.

Example:
  @pyoc.Injectable
  def user():
    return 'Anonymous'

  pyoc.Injectable.value('greet', 'Hello')

  @pyoc.Inject
  def Hello(greet=ioc.IN, user=ioc.IN):
    return '%s %s' % (greet, user)

  Hello()  # This will print 'Hello Anonymous'
"""
import functools
import inspect
import logging
import threading


IN = INJECTED = object()
_IN_TEST_MODE = False


class Error(Exception):
  """Base Error class of ioc module."""


class InjectionDuringTestError(Error):
  """When injection happened when the test mode is enabled."""


class _Scope(object):

  def __init__(self, name):
    self.name = name
    self._gob = {}
    self._eagers = []

  def Injectable(self, f):
    f.ioc_injectable = True
    injectable = Inject(f)
    self._gob[f.__name__] = injectable
    if hasattr(c, 'ioc_eager'):
      self._eagers.append(Wrapper)
    return injectable

  def __contains__(self, name):
    return name in self._gob

  def __getitem__(self, name):
    return self._gob[name]

  def Warmup(self):
    logging.debug('Warming up: ' + self.name)
    for eager in self._eagers:
      eager()
    logging.debug('Hot: ' + self.name)

  def __str__(self):
    return 'Scope %r : %r' % (self.name, self._gob.keys())

  def __enter__(self):
    if not hasattr(_DATA, 'scopes'):
      _DATA.scopes = [_ROOT_SCOPE]
    _DATA.scopes.append(self)

  def __exit__(self, t, v, tb):
    _DATA.scopes.pop()


_ROOT_SCOPE = _Scope('root')
_DATA = threading.local()
_DATA.scopes = [_ROOT_SCOPE]


def _FillInInjections(injections, arguments):
  for injection in injections:
    if injection in arguments: continue
    if _IN_TEST_MODE:
      raise InjectionDuringTestError(
          'Test mode enabled. Injection arguments are required.')
    for scope in reversed(_DATA.scopes):
      if injection in scope:
        arguments[injection] = scope[injection]()
        break
    else:
      raise ValueError('The injectable named %r was not found.' % injection)


def Inject(f):
  """Function wrapper that will examine the kwargs and wrap when necessary.

  Args:
    f: Function to inject into.

  Returns:
    Return a wrapped function of the original one with all the pyoc.IN value
    being fill in the real values.
  """
  c = f
  name = f.__name__
  if type(f) == type:
    f = f.__init__
  try:
    argspec = inspect.getargspec(f)
  except TypeError:
    raise ValueError(
        'Built-ins (and classes without an __init__) cannot be injected.')
  injections = argspec.args[-len(argspec.defaults):] if argspec.defaults else []
  injections = tuple(injection for i, injection in enumerate(injections)
                     if argspec.defaults[i] is INJECTED)
  if hasattr(c, 'ioc_injectable'):
    argspec_len = (len(argspec.args) - 1
                   if inspect.isclass(c) else len(argspec.args))
    assert argspec_len == len(injections), 'Injectables must be fully injected.'

  if hasattr(f, 'ioc_singleton'):
    logging.debug(name + ' is a singleton.')

    @functools.wraps(f)
    def Wrapper(*args, **kwargs):
      if not hasattr(c, 'ioc_value'):
        _FillInInjections(injections, kwargs)
        c.ioc_value = c(*args, **kwargs)
      return c.ioc_value
  else:
    logging.debug(name + ' is a factory.')

    @functools.wraps(f)
    def Wrapper(*args, **kwargs):
      _FillInInjections(injections, kwargs)
      return c(*args, **kwargs)

  return Wrapper


def Scope(f):
  @functools.wraps(f)
  def Wrapper(*args, **kwargs):
    with _Scope(f.__name__):
      return f(*args, **kwargs)
  return Wrapper


def Injectable(f):
  for scope in _DATA.scopes:
    if f.__name__ in scope:
      raise KeyError('Injectable %r already exist in scope %r.' %
                     (f.__name__, scope.name))
  _DATA.scopes[-1].Injectable(f)


def _InjectableValue(name, value):

  @Singleton()
  def Callable():
    pass
  Callable.__name__ = name
  Callable.ioc_value = value

  Injectable(Callable)
Injectable.value = _InjectableValue


def Singleton(eager=None):
  def Decorator(f):
    if eager:
      f.ioc_eager = True
    f.ioc_singleton = True
    return f
  return Decorator


def Warmup():
  logging.debug('Warming up ALL')
  for scope in _DATA.scopes:
    scope.Warmup()
  logging.debug('Hot ALL')


def SetTestMode(enabled=True):
  """Enter or leave the test mode."""
  global _IN_TEST_MODE
  _IN_TEST_MODE = enabled
