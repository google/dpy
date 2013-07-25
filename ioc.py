import functools
import inspect
import logging
import threading


IN = INJECTED = object()


class _Scope(object):

  def __init__(self, name):
    self.name = name
    self._GOB = {}
    self._EAGER = []

  def Injectable(self, f):
    f._ioc_injectable = True
    injectable = Inject(f)
    self._GOB[f.__name__] = injectable
    return injectable

  def __contains__(self, name):
    return name in self._GOB

  def Inspect(self, name):
    return self._GOB[name]

  def Warmup(self):
    logging.debug('Warming up: ' + self.name)
    for eager in self._EAGER:
      eager()
    logging.debug('Hot: ' + self.name)

  def __str__(self):
    return 'Scope %r : %r' % (self.name, self._GOB.keys())

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
    for scope in reversed(_DATA.scopes):
      if injection in scope:
        arguments[injection] = scope.Inspect(injection)()
        break
    else:
      raise ValueError('The injectable named %r was not found.' % injection)


def Inject(f):
  c = f
  name = f.__name__
  if type(f) == type:
    f = f.__init__
  try:
    argspec = inspect.getargspec(f)
  except TypeError:
    raise ValueError('Built-ins (and classes without an __init__) cannot be injected.')
  injections = argspec.args[-len(argspec.defaults):] if argspec.defaults else []
  injections = tuple(injection for i, injection in enumerate(injections)
                     if argspec.defaults[i] is INJECTED)
  if hasattr(c, '_ioc_injectable'):
    self = 1 if inspect.isclass(c) else 0
    assert len(argspec.args) - self == len(injections), 'Injectables must be fully injected.'

  if hasattr(f, '_ioc_singleton'):
    logging.debug(name + ' is a singleton.')

    @functools.wraps(f)
    def Wrapper(*args, **kwargs):
      if not hasattr(c, '_ioc_value'):
        _FillInInjections(injections, kwargs)
        c._ioc_value = c(*args, **kwargs)
      return c._ioc_value
  else:
    logging.debug(name + ' is a factory.')

    @functools.wraps(f)
    def Wrapper(*args, **kwargs):
      _FillInInjections(injections, kwargs)
      return c(*args, **kwargs)

  if hasattr(c, '_ioc_eager'):
    logging.debug(name + ' is eager.')
    _DATA.scopes[-1]._EAGER.append(Wrapper)

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
  @Singleton
  def Callable(): pass
  Callable.__name__ = name
  Callable._ioc_value = value
  Injectable(Callable)
Injectable.value = _InjectableValue


def Eager(f):
  f._ioc_eager = True
  return f


def Singleton(f):
  f._ioc_singleton = True
  return f


def Warmup():
  logging.debug('Warming up ALL')
  for scope in _DATA.scopes:
    scope.Warmup()
  logging.debug('Hot ALL')
