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

_MAIN_THREAD_ID = threading.currentThread().ident
_DATA = threading.local()


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
    injected = _Inject(f)
    if name:
      logging.debug('%r injectable added as %r to scope %r.',
                    injected.name, name, self.name)
    else:
      logging.debug('%r injectable added to scope %r.',
                    injected.name, self.name)
      name = injected.name
    injectable = injected.injectable_wrapper
    self._gob[name] = injectable
    if injected.eager:
      self._eagers.append(injectable)
    return injected.wrapper

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
    if not self._gob:
      a.append('\n  None')
    for key in self._gob:
      a.append('\n  ')
      a.append(key)
    return ''.join(a)

  def __enter__(self):
    scopes = _MyScopes()
    if threading.currentThread().ident == _MAIN_THREAD_ID:
      _BASE_SCOPES.append(self)
    else:
      scopes.append(self)

  def __exit__(self, t, v, tb):
    _MyScopes().pop()


def _MyScopes():
  if not hasattr(_DATA, 'scopes'):
    _DATA.scopes = _BASE_SCOPES
  return _DATA.scopes


def _FillInInjections(injections, arguments):
  for injection in injections:
    if injection in arguments: continue
    if _IN_TEST_MODE:
      raise InjectionDuringTestError(
          'Test mode enabled. Injection arguments are required.')
    for scope in reversed(_MyScopes()):
      if injection in scope:
        arguments[injection] = scope[injection]()
        break
    else:
      raise ValueError('The injectable named %r was not found.' % injection)


def _GetInjections(argspec):
  if not argspec.defaults:
    return tuple()
  injections = argspec.args[-len(argspec.defaults):]
  injections = tuple(injection for i, injection in enumerate(injections)
                     if argspec.defaults[i] is INJECTED)
  return injections


def _CreateInjectWrapper(f, injections):
  if not injections:
    return f

  @functools.wraps(f)
  def Wrapper(*args, **kwargs):
    logging.debug('Injecting %r with %r - %r', f.__name__, injections, kwargs)
    _FillInInjections(injections, kwargs)
    return f(*args, **kwargs)
  Wrapper.ioc_wrapper = True
  return Wrapper


def _CreateSingletonInjectableWrapper(f):

  @functools.wraps(f)
  def Wrapper(*args, **kwargs):
    logging.debug('Injecting singleton %r', f.__name__)
    if not hasattr(f, 'ioc_value'):
      f.ioc_value = f(*args, **kwargs)
    return f.ioc_value
  Wrapper.ioc_singleton = True
  return Wrapper


class _InjectFunction(object):
  ARGSPEC_ERR = 'Built-ins cannot be injected'
  FULL_INJECTABLE_ERR = 'Injectables must be fully injected.'
  NOT_INJECTABLE_ERR = 'Requested injectable is not callable.'
  SHORT_ARG_COUNT = 0

  def __init__(self, f):
    self.f = f
    self.name = f.__name__
    self._argspec = None
    self._injections = None
    self._inject = None
    self._wrapper = None

  @property
  def argspec(self):
    if not self._argspec:
      try:
        self._argspec = inspect.getargspec(self.callable)
      except TypeError:
        raise ValueError(self.ARGSPEC_ERR)
    return self._argspec

  @property
  def injections(self):
    if not self._injections:
      self._injections = _GetInjections(self.argspec)
    return self._injections

  @property
  def already_injected(self):
    return hasattr(self.callable, 'ioc_wrapper')

  def CheckInjectable(self):
    argspec_len = len(self.argspec.args) - self.SHORT_ARG_COUNT
    assert argspec_len <= len(self.injections), self.FULL_INJECTABLE_ERR

  @property
  def singleton(self):
    return hasattr(self.f, 'ioc_singleton')

  @property
  def eager(self):
    return hasattr(self.f, 'ioc_eager')

  @property
  def callable(self):
    return self.f

  @property
  def wrapper(self):
    if not self._wrapper:
      assert callable(self.callable), self.NOT_INJECTABLE_ERR
      if self.already_injected:
        self._wrapper = self.callable
      else:
        self._wrapper = _CreateInjectWrapper(self.callable, self.injections)
    return self._wrapper

  def __call__(self, *args, **kwargs):
    if not self._inject:
      self._inject = self.wrapper
    return self._inject(*args, **kwargs)

  @property
  def injectable_wrapper(self):
    self.CheckInjectable()
    if self.singleton:
      return _CreateSingletonInjectableWrapper(self.f)
    else:
      return self.wrapper


class _InjectClass(_InjectFunction):
  ARGSPEC_ERR = 'Classes without an __init__ cannot be injected.'
  SHORT_ARG_COUNT = 1

  @property
  def callable(self):
    return self.f.__init__

  @property
  def wrapper(self):
    self.f.__init_ioc__ = self.f.__init__  # Backup the __init__.
    self.f.__init__ = super(_InjectClass, self).wrapper
    return self.f


def _Inject(f):
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
  logging.debug('Set up %r for injection', inject.name)
  return inject


def Inject(f):
  return _Inject(f).wrapper


def Scope(f):
  """Decorates a callable and creates a new injection Scope level."""
  @functools.wraps(f)
  def Wrapper(*args, **kwargs):
    with _Scope(f):
      return f(*args, **kwargs)
  return Wrapper


def _CheckAlreadyInjected(name):
  """Checks if an injectable name is already in use."""
  for scope in _MyScopes():
    if name in scope:
      raise ValueError('Injectable %r already exist in scope %r.' %
                       (name, scope.name))


def Injectable(f):
  """Decorates a callable and creates an injectable in the current Scope."""
  _CheckAlreadyInjected(f.__name__)
  return _MyScopes()[-1].Injectable(f)


def _InjectableNamed(name):
  """Decorates a callable and creates a named injectable in the current Scope.

  Args:
    name: The name of the object to setup for injection.
  Returns:
    A decorator for an Injectable.
  """

  def Decorator(f):
    _CheckAlreadyInjected(name)
    return _MyScopes()[-1].Injectable(f, name=name)
  return Decorator
Injectable.named = _InjectableNamed


def _InjectableValue(**kwargs):
  """Creates a named injectable value.

  Example:
    ioc.Injectable.value(bar=42)

  Args:
    **kwargs: A 1-length dict that has the name of the injectable as the key and
      the injectable value as the value.
  """

  @Singleton
  def Callable():
    pass
  assert len(kwargs) == 1, 'You can only create one injectable value at a time.'
  Callable.__name__, Callable.ioc_value = kwargs.popitem()
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
  for scope in _MyScopes():
    scope.Warmup()
  logging.debug('Hot ALL')


def DumpInjectionStack():
  for scope in _MyScopes():
    print scope


def SetTestMode(enabled=True):
  """Enter or leave the test mode."""
  global _IN_TEST_MODE
  _IN_TEST_MODE = enabled


_ROOT_SCOPE = _Scope(None)  # Create Root scope
_BASE_SCOPES = [_ROOT_SCOPE]
_DATA.scopes = _BASE_SCOPES
