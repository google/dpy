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
    @ioc.Inject
    def ReturnSingleton(singleton=ioc.IN):
      return singleton

    expect(ReturnSingleton()).toBe(ReturnSingleton())

  def it_should_support_singleton_classes(self):

    @ioc.Injectable
    @ioc.Singleton
    class singleton(object):
      def __init__(self):
        self.bar = object()

    @ioc.Inject
    def ReturnSingleton(singleton=ioc.IN):
      return singleton


    expect(ReturnSingleton()).toBe(ReturnSingleton())
    expect(ReturnSingleton().bar).toBe(ReturnSingleton().bar)

  def it_should_support_eager_singletons(self):
    spy = create_spy('eager')

    @ioc.Injectable
    @ioc.Singleton.eager
    def singleton():
      print 'foo'
      spy()

    @ioc.Inject
    def ReturnSingleton(singleton=ioc.IN):
      return singleton
    ioc.Warmup()
    expect(spy.call_count).toBe(1)
    ReturnSingleton()
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

  def it_should_error_when_layering_injection_wrappers(self):

    def InjectInjectable():
      @ioc.Inject
      @ioc.Injectable
      def foo(baz=ioc.IN):
        return baz

    def InjectableInject():
      @ioc.Injectable
      @ioc.Inject
      def bar(baz=ioc.IN):
        return baz

    ioc.Injectable.value('baz', 42)  # To ensure that foo is wrapped.

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
