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

  def it_should_support_singletons(self):
    spy = create_spy('singleton')
    @ioc.Injectable
    @ioc.Singleton
    def singleton():
      spy()
    @ioc.Inject
    def foo(singleton=ioc.IN): pass
    foo()
    expect(spy.call_count).toBe(1)
    foo()
    expect(spy.call_count).toBe(1)

  def it_should_support_eager_singletons(self):
    spy = create_spy('singleton')
    @ioc.Injectable
    @ioc.Singleton.eager
    def singleton():
      spy()
    @ioc.Inject
    def foo(singleton=ioc.IN): pass
    ioc.Warmup()
    expect(spy.call_count).toBe(1)
    foo()
    expect(spy.call_count).toBe(1)
    foo()
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

    expect(InjectInjectable).toRaise(ValueError)
    expect(InjectableInject).toRaise(ValueError)

  def it_should_not_allow_calling_injectables(self):
    @ioc.Injectable
    def foo():
      return 42

    expect(foo).toRaise(ValueError)

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
