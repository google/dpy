"""dpy is a simple, thread-safe, Python dependency injection library.

dpy is designed to easily allow inversion of control without messy overhead.
It is quick to define and use injectable objects in your code.

Example:
  @dpy.Injectable
  def user():
    return 'Anonymous'

  dpy.Injectable.value(greet='Hello')

  @dpy.Inject
  def Hello(greet=ioc.IN, user=ioc.IN):
    return '%s %s' % (greet, user)

  Hello()  # This will print 'Hello Anonymous'
"""
import collections
import functools
import inspect
import logging
import threading


_IN_TEST_MODE = False
_TEST_SCOPE = None

_MAIN_THREAD_ID = threading.currentThread().ident
_DATA = threading.local()


class Error(Exception):
  """Base Error class of ioc module."""


class InjectionMissingError(Error):
  """When an injection is requested, but not available."""


class InjectionNotPerformed(Error):
  """When an injection is requested, but the callable is not injected."""


class TestInjectionsNotSetupError(Error):
  """When injection is requested without a set up test scope."""


class _InjectionSentinel(object):
  
  def _DO_NOT_USE_INJECTION_SENTINEL(self):
    if _IN_TEST_MODE:
      raise TestInjectionsNotSetupError('Injection was expected in test mode!')
    raise InjectionNotPerformed('You forgot to mark something with @Inject or @Injectable.')
  
  def __call__(self):
    self._DO_NOT_USE_INJECTION_SENTINEL()
  
  def __len__(self):
    self._DO_NOT_USE_INJECTION_SENTINEL()
  
  def __str__(self):
    self._DO_NOT_USE_INJECTION_SENTINEL()

  def __getattr__(self, _):
    self._DO_NOT_USE_INJECTION_SENTINEL()


IN = INJECTED = _InjectionSentinel()


class _Scope(object):

  def __init__(self, f):
    self.func = f
    self._gob = {}
    self._eagers = []
    self.singletons = {}

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
    _ResetInjectionScopeMap()
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

  def __iter__(self):
    return iter(self._gob)

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
    _ResetInjectionScopeMap()
    _MyScopes().pop()


_ROOT_SCOPE = _Scope(None)  # Create Root scope
_BASE_SCOPES = [_ROOT_SCOPE]
_DATA.scopes = _BASE_SCOPES


def _MyScopes():
  if not hasattr(_DATA, 'scopes'):
    _DATA.scopes = _BASE_SCOPES[:]
  return _DATA.scopes


def _CurrentScope():
  return _MyScopes()[-1]


def _ResetInjectionScopeMap():
  """Delete the injection_scope_map to force the recalculate."""
  if hasattr(_DATA, 'injection_scope_map'):
    del _DATA.injection_scope_map


InjectionScope = collections.namedtuple('InjectionScope',
                                        ['idx', 'scope', 'callable'])


def _GetCurrentInjectionInfo():
  """Returns a dict contains the required injections' information.

  This method is used to provide information for filling injection and
  calculating scope dependency.
  """
  if not hasattr(_DATA, 'injection_scope_map'):
    injection_scope_map = {}
    for idx, scope in enumerate(reversed(_MyScopes())):
      for injection in scope:
        if injection not in injection_scope_map:
          injection_scope_map[injection] = InjectionScope(idx, scope,
                                                          scope[injection])
    _DATA.injection_scope_map = injection_scope_map
  return _DATA.injection_scope_map


def _FillInInjections(injections, arguments):
  injection_scope_map = _GetCurrentInjectionInfo()

  for injection in injections:
    if injection in arguments: continue
    try:
      if _IN_TEST_MODE:
        if _TEST_SCOPE is None:
          raise TestInjectionsNotSetupError(
              'Test injections have not been setup.')
        arguments[injection] = _TEST_SCOPE[injection]()
      else:
        arguments[injection] = injection_scope_map[injection].callable()
    except KeyError:
      raise InjectionMissingError(
          'The injectable named %r was not found.' % injection)


def _CalculateScopeDep(injections):
  """Returns the deepest required scope inside the current scope tree."""
  dep_scope_idx, dep_scope = len(_MyScopes()), _MyScopes()[0]  # root scope.
  injection_scope_map = _GetCurrentInjectionInfo()

  injection_queue = collections.deque(injections)
  while injection_queue:
    injection = injection_queue.popleft()
    if injection not in injection_scope_map:
      raise ValueError('The injectable named %r was not found.' % injection)

    idx, scope, callable_func = injection_scope_map[injection]

    # Get all injections and put into queue.
    while hasattr(callable_func, 'ioc_wrapper'):
      callable_func = callable_func.ioc_wrapper  # Get the original callable.
    if inspect.isclass(callable_func):
      argspec = inspect.getargspec(callable_func.__init__)
    else:
      argspec = inspect.getargspec(callable_func)
    injection_queue.extend(_GetInjections(argspec))

    if idx < dep_scope_idx:
      dep_scope_idx, dep_scope = idx, scope

  return dep_scope


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
  Wrapper.ioc_wrapper = f
  return Wrapper


def _CreateSingletonInjectableWrapper(f, injections):

  @functools.wraps(f)
  def Wrapper(*args, **kwargs):
    logging.debug(
        'Injecting singleton %r with %r - %r', f.__name__, injections, kwargs)
    for scope in _MyScopes():
      if f.__name__ in scope.singletons:
        return scope.singletons[f.__name__]

    # Couldn't find it in current scope tree.
    dep_scope = _CalculateScopeDep(injections)
    dep_scope.singletons[f.__name__] = f(*args, **kwargs)
    logging.debug(
        'Attaching singleton %r to scope %s', f.__name__, dep_scope.name)
    return dep_scope.singletons[f.__name__]
  Wrapper.ioc_wrapper = f
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
    """Checks if all the arguments are injected."""
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
    """Returns a wrapper that will call the function with injected arguments."""
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
    """Returns a wrapper that can be used to produce value for injection."""
    self.CheckInjectable()
    if self.singleton:
      return _CreateSingletonInjectableWrapper(self.wrapper, self.injections)
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
    self.f.__init__ = super(_InjectClass, self).wrapper
    return self.f


def _Inject(f):
  """Function wrapper that will examine the kwargs and wrap when necessary.

  Args:
    f: Function to inject into.

  Returns:
    Return a wrapped function of the original one with all the dpy.IN value
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
  """Checks if an injectable name is already in use in current scope."""
  curr_scope = _CurrentScope()
  if name in curr_scope:
    raise ValueError('Injectable %r already exist in scope %r.' %
                     (name, curr_scope.name))


def Injectable(f):
  """Decorates a callable and creates an injectable in the current Scope."""
  _CheckAlreadyInjected(f.__name__)
  return _CurrentScope().Injectable(f)


def _InjectableNamed(name):
  """Decorates a callable and creates a named injectable in the current Scope.

  Args:
    name: The name of the object to setup for injection.
  Returns:
    A decorator for an Injectable.
  """

  def Decorator(f):
    _CheckAlreadyInjected(name)
    return _CurrentScope().Injectable(f, name=name)
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
  assert len(kwargs) == 1, 'You can only create one injectable value at a time.'
  name, ioc_value = kwargs.popitem()
  Injectable(_CreateCallable(name, ioc_value))
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
  """Enters or leaves the test mode.

  Test mode means the following:
    - Injections are _prohibited_ and will cause an AssertionError to be raised.
    - Classes may have their injectable values set.
      ioc.SetClassInjections(InjectedCls, injected_arg=42)
      This functionality should be used for super classes.

  Args:
    enabled: True to enable the test mode, false to disable it.
  """
  global _IN_TEST_MODE
  _IN_TEST_MODE = enabled


def SetUpTestInjections(**kwargs):
  """Sets up injectable values for testing.

  Args:
    **kwargs: name and values for the injectables to be created.
  """
  global _TEST_SCOPE
  _TEST_SCOPE = _TEST_SCOPE or _Scope(None)
  for name, value in kwargs.iteritems():
    _TEST_SCOPE.Injectable(_CreateCallable(name, value))


def _CreateCallable(name, value):
  def Callable():
    return value
  Callable.__name__ = name
  return Callable


def TearDownTestInjections():
  """Tears down any injections set up for testing."""
  global _TEST_SCOPE
  _TEST_SCOPE = None
