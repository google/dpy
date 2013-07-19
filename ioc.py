import functools
import inspect
import logging


INJECTED = object()
_GOB = {}
_EAGER = []


def Injectable(f):
  f._ioc_injectable = True
  injectable = Inject(f)
  _GOB[f.__name__] = injectable
  return injectable


def _InjectableValue(name, v):
  def Callable():
    return v
  Callable.__name__ = name
  Injectable(Callable)

Injectable.value = _InjectableValue

def Eager(f):
  f._ioc_eager = True
  return f


def Singleton(f):
  f._ioc_singleton = True
  return f


def Warmup():
  for f in _EAGER:
    f()


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
  if hasattr(f, '_ioc_injectable'):
    assert len(argspec.args) == len(injections), 'Injectables must be fully injected.'
  if hasattr(f, '_ioc_singleton'):
    logging.debug(name + ' is a singleton.')

    @functools.wraps(f)
    def Wrapper(*args, **kwargs):
      if not hasattr(f, '_ioc_value'):
        kwargs.update({injection: _GOB[injection]() for injection in injections})
        f._ioc_value = c(*args, **kwargs)
      return f._ioc_value
  else:
    logging.debug(name + ' is a factory.')

    @functools.wraps(f)
    def Wrapper(*args, **kwargs):
      kwargs.update({injection: _GOB[injection]() for injection in injections})
      result = c(*args, **kwargs)
      return result

  if hasattr(f, '_ioc_eager'):
    logging.debug(name + ' is eager.')
    _EAGER.append(Wrapper)

  return Wrapper

