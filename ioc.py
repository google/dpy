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

  def __init__(self, f):
    self.func = f
    self._gob = {}
    self._eagers = []

  @property
  def name(self):
    if self.func:
      parent = (getattr(self.func, 'im_class', None) or
                getattr(self.func, '__module__'))
      return '%s.%s' % (parent, self.func.__name__)
    elif self is _ROOT_SCOPE:
      return 'Root'
    else:
      return 'No Name'

  def Injectable(self, f, name=None):
    """Adds a callable as an injectable to the scope.

    Args:
      f: A callable to add as an injectable.
      name: A name to give the injectable or None to use its name.
    Returns:
      The wrapped injectable function.
    """
    f.ioc_injectable = True
    injectable = Inject(f)
    if name:
      logging.debug('%r injectable added as %r to scope %r.',
                    f.__name__, name, self.name)
    else:
      logging.debug('%r injectable added to scope %r.', f.__name__, self.name)
      name = f.__name__
    self._gob[name] = injectable
    if hasattr(f, 'ioc_eager'):
      self._eagers.append(injectable)
    return injectable

  def __contains__(self, name):
    return name in self._gob

  def __getitem__(self, name):
    return self._gob[name]

  def Warmup(self):
    logging.debug('Warming up: %s', self.name)
    for eager in self._eagers:
      eager()
    logging.debug('Hot: %s', self.name)

  def __str__(self):
    a = ['Scope %r:' % self.name]
    for key in self._gob:
      a.append('\n  ')
      a.append(key)
    return ''.join(a)

  def __enter__(self):
    if not hasattr(_DATA, 'scopes'):
      _DATA.scopes = [_ROOT_SCOPE]
    _DATA.scopes.append(self)

  def __exit__(self, t, v, tb):
    _DATA.scopes.pop()


_ROOT_SCOPE = _Scope(None)
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


def _GetInjections(argspec):
  injections = argspec.args[-len(argspec.defaults):] if argspec.defaults else []
  return tuple(injection for i, injection in enumerate(injections)
               if argspec.defaults[i] is INJECTED)


def _CreateFactoryInjectableWrapper(f, injections):
  def Wrapper(*args, **kwargs):
    _FillInInjections(injections, kwargs)
    return f(*args, **kwargs)
  return Wrapper


def _CreateSingletonInjectableWrapper(f, then, injections):
  def Wrapper(*args, **kwargs):
    if not hasattr(f, 'ioc_value'):
      _FillInInjections(injections, kwargs)
      setattr(f, 'ioc_value', then(*args, **kwargs))
    return f.ioc_value
  Wrapper.ioc_wrapper = True
  return Wrapper


class _InjectFunction(object):
  ARGSPEC_ERR = 'Built-ins cannot be injected'
  FULL_INJECTABLE_ERR = 'Injectables must be fully injected.'
  ALREADY_INJECTED_ERR = 'Already been setup for injection.'
  NOT_INJECTABLE_ERR = 'Requested injectable is not callable.'
  SHORT_ARG_COUNT = 0

  def __init__(self, f):
    self.f = f
    self.name = f.__name__
    self.singleton = hasattr(f, 'ioc_singleton')
    self.injectable = hasattr(f, 'ioc_injectable')
    self._argspec = None
    self._injections = None

  @property
  def argspec(self):
    if not self._argspec:
      try:
        self._argspec = inspect.getargspec(self.argspec_callable)
      except TypeError:
        raise ValueError(self.ARGSPEC_ERR)
    return self._argspec

  @property
  def injections(self):
    if not self._injections:
      self._injections = _GetInjections(self.argspec)
    return self._injections

  def Check(self, argspec, injections):
    if self.injectable:
      argspec_len = len(self.argspec.args) - self.SHORT_ARG_COUNT
      assert argspec_len == len(injections), self.FULL_INJECTABLE_ERR
    assert callable(self.f), self.NOT_INJECTABLE_ERR
    assert not hasattr(self.f, 'ioc_wrapper'), self.ALREADY_INJECTED_ERR

  @property
  def argspec_callable(self):
    return self.f

  def __call__(self, *args, **kwargs):
    if self.singleton:
      wrapper =_CreateSingletonInjectableWrapper(self.f, self.argspec_callable, self.injections)
    else:
      wrapper = _CreateFactoryInjectableWrapper(self.argspec_callable, self.injections)
    return wrapper(*args, **kwargs)


class _InjectClass(_InjectFunction):
  ARGSPEC_ERR = 'Classes without an __init__ cannot be injected.'
  SHORT_ARG_COUNT = 1

  @property
  def argspec_callable(self):
    return self.f.__init__

  @property
  def wrapper(self):
    self.f.__init__ = super(_InjectClass, self).wrapper
    return self.f


def Inject(f):
  """Function wrapper that will examine the kwargs and wrap when necessary.

  Args:
    f: Function to inject into.

  Returns:
    Return a wrapped function of the original one with all the pyoc.IN value
    being fill in the real values.
  Raises:
    ValueError: If the argument is not a callable or is already injected.
  """
  inject = _InjectClass(f) if inspect.isclass(f) else _InjectFunction(f)
  return inject


def Scope(f):
  """Decorates a callable and creates a new injection Scope level."""
  @functools.wraps(f)
  def Wrapper(*args, **kwargs):
    with _Scope(f):
      return f(*args, **kwargs)
  return Wrapper


def _CheckAlreadyInjected(name):
  """Checks if an injectable name is already in use."""
  for scope in _DATA.scopes:
    if name in scope:
      raise ValueError('Injectable %r already exist in scope %r.' %
                       (name, scope.name))


def Injectable(f):
  """Decorates a callable and creates an injectable in the current Scope."""
  _CheckAlreadyInjected(f.__name__)
  return _DATA.scopes[-1].Injectable(f)


def _InjectableNamed(name):
  """Decorates a callable and creates a named injectable in the current Scope.

  Args:
    name: The name of the object to setup for injection.
  Returns:
    A decorator for an Injectable.
  """

  def Decorator(f):
    _CheckAlreadyInjected(name)
    return _DATA.scopes[-1].Injectable(f, name=name)
  return Decorator
Injectable.named = _InjectableNamed


def _InjectableValue(name, value):
  """Creates a named injectable value.

  Args:
    name: The name of the object to setup for injection.
    value: The value of the object to setup for injection.
  """

  @Singleton
  def Callable():
    pass
  Callable.__name__ = name
  Callable.ioc_value = value

  Injectable(Callable)
Injectable.value = _InjectableValue


def Singleton(f):
  """Decorates a callable and sets it as a singleton.

  Must be used in conjunction with a call to Injectable.

  Args:
    f: A callable to mark as an injectable singleton.
  Returns:
    The callable set to be a singleton when injected.
  """
  f.ioc_singleton = True
  return f


def _EagerSingleton(f):
  """Decorates a callable and sets it as an eager singleton.

  Must be used in conjunction with a call to Injectable.

  Args:
    f: A callable to mark as an injectable eager singleton.
  Returns:
    The callable set to be a eager singleton when injected.
  """
  f.ioc_eager = True
  return Singleton(f)
Singleton.eager = _EagerSingleton


def Warmup():
  """Instantiates all the eager singleton injectables."""
  logging.debug('Warming up ALL')
  for scope in _DATA.scopes:
    scope.Warmup()
  logging.debug('Hot ALL')


def DumpInjectionStack():
  for scope in _DATA.scopes:
    print scope


def SetTestMode(enabled=True):
  """Enter or leave the test mode."""
  global _IN_TEST_MODE
  _IN_TEST_MODE = enabled
