#!/usr/bin/python
import ioc
import logging
import sys
from jazz.jazz import *
from jazz import mock

if 'debug' in sys.argv:
  logging.getLogger().setLevel(logging.DEBUG)


class Ioc(Describe):

  def before_each(self):
    reload(ioc)

  def it_should_inject(self):

    @ioc.Injectable
    def foo():
      return 42

    @ioc.Inject
    def bar(foo=ioc.IN):
      return foo

    expect(bar()).toBe(42)

  def it_should_allow_overwriting_injectables(self):

    @ioc.Injectable
    def foo():
      return 42

    @ioc.Inject
    def bar(foo=ioc.IN):
      return foo

    expect(bar(foo=99)).toBe(99)

  def it_should_support_naming_injectables(self):

    @ioc.Injectable.named('bar')
    def foo():
      return 42

    @ioc.Inject
    def bar(bar=ioc.IN):
      return bar

    expect(bar()).toBe(42)

  def it_should_allow_calling_injectables(self):

    @ioc.Injectable
    def foo(bar=ioc.IN):
      return 'foo %s' % bar

    ioc.Injectable.value('bar', 'bar')

    expect(foo()).toEqual('foo bar')
    expect(foo(bar='candybar')).toEqual('foo candybar')

  def it_should_support_singleton_functions(self):
    @ioc.Injectable
    @ioc.Singleton
    def singleton():
      return object()
    expect(singleton()).toBe(singleton())

  def it_should_support_singleton_classes(self):
    @ioc.Injectable
    @ioc.Singleton
    class singleton(object):
      def __init__(self):
        self.bar = object()

    expect(singleton()).toBe(singleton())
    expect(singleton().bar).toBe(singleton().bar)

  def it_should_support_eager_singletons(self):
    spy = create_spy('singleton')
    @ioc.Injectable
    @ioc.Singleton.eager
    def singleton():
      spy()
    ioc.Warmup()
    expect(spy.call_count).toBe(1)
    singleton()
    expect(spy.call_count).toBe(1)
    singleton()
    expect(spy.call_count).toBe(1)

  def it_should_support_multiple_scopes(self):
    ioc.Injectable.value('root', 99)

    @ioc.Inject
    def InjectedFunc(scoped=ioc.IN, root=ioc.IN):
      return scoped, root

    @ioc.Scope
    def ScopedFunc():
      ioc.Injectable.value('scoped', 32)
      return InjectedFunc()

    expect(ScopedFunc()).toEqual((32, 99))
    expect(InjectedFunc).toRaise(ValueError)

  def it_should_error_when_layering_injection_decorators(self):

    def InjectInjectable():
      @ioc.Inject
      @ioc.Injectable
      def foo():
        pass

    def InjectableInject():
      @ioc.Injectable
      @ioc.Inject
      def foo():
        pass

    expect(InjectInjectable).toRaise(AssertionError)
    expect(InjectableInject).toRaise(AssertionError)

  def it_should_allow_calling_injectables_for_testability(self):
    @ioc.Injectable
    def foo(val=ioc.IN):
      return val

    expect(foo(val=99)).toBe(99)

  def it_should_detect_name_conflict_in_same_scope(self):
    def InjectValue():
      ioc.Injectable.value('val', 42)

    InjectValue()
    expect(InjectValue).toRaise(ValueError)

  def it_should_detect_name_conflict_in_all_parent_scopes(self):
    ioc.Injectable.value('val', 42)

    @ioc.Scope
    def ScopedFunc():
      ioc.Injectable.value('val', 32)

    expect(ScopedFunc).toRaise(ValueError)

  def it_should_require_all_injections(self):
    @ioc.Inject
    def Injected(val=ioc.IN): pass
    expect(Injected).toRaise(ValueError)

  def it_should_not_mangle_classes(self):

    @ioc.Inject
    class bar(object):
      def __init__(self):
        super(bar, self).__init__()

    expect(bar).notToRaise(TypeError)

  def it_should_inject_classes(self):
    class bar(object):
      def __init__(self, x):
        self._x = x

    @ioc.Inject
    @ioc.Singleton
    class foo(bar):
      def __init__(self, x=ioc.IN):
        print 'init b', self, type(self)
        self._y = x + 5
        super(foo, self).__init__(x)
        print 'init a', self, self._y
      def bar(self):
        print 'bar   ', self
        print self._y
        return self._x

    print 'main  ', foo, type(foo)

    ioc.Injectable.value('x', 42)

    f = foo()
    print 'main 1', f, type(f)

    expect(f.bar()).toBe(42)
    expect(f._y).toBe(42 + 5)

    f = foo()
    print 'main 2', f, type(f)

    expect(f.bar()).toBe(42)
    expect(f._y).toBe(42 + 5)

class IocTestMode(Describe):

  def before_each(self):
    reload(ioc)
    ioc.SetTestMode()

    @ioc.Inject
    def InjectedFunc(val=ioc.IN):
      return val

    self.InjectedFunc = InjectedFunc
    self.injected_value = 42

    ioc.Injectable.value('val', self.injected_value)

  def it_should_allow_passing_args(self):
    expect(self.InjectedFunc(val=99)).toBe(99)

  def it_should_not_inject(self):
    expect(self.InjectedFunc).toRaise(ioc.InjectionDuringTestError)

  def it_should_allow_passing_none(self):
    expect(self.InjectedFunc(val=None)).toBeNone()


if __name__ == '__main__':
  run()
