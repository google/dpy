#!/usr/bin/python
import ioc
from jazz.jazz import *
from jazz import mock


class IocTest(Describe):

  def before_each(self):
    reload(ioc)

  def it_should_inject(self):

    @ioc.Injectable
    def foo():
      return 'foo'

    @ioc.Inject
    def bar(foo=ioc.IN):
      return foo

    expect(bar()).toEqual('foo')

  def it_should_allow_overwriting_injectables(self):

    @ioc.Injectable
    def foo():
      return 'foo'

    @ioc.Inject
    def bar(foo=ioc.IN):
      return foo

    expect(bar(foo=42)).toEqual(42)

  def it_should_support_singletons(self):
    spy = create_spy('singleton')
    @ioc.Injectable
    @ioc.Singleton()
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
    @ioc.Singleton(eager=True)
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
    ioc.Injectable.value('val', 42)
    @ioc.Inject
    def InjectedFunc(val=ioc.IN):
      return val
    @ioc.Scope
    def ScopedFunc():
      ioc.Injectable.value('val', 32)
      return InjectedFunc()
    expect(InjectedFunc()).toBe(42)
    expect(ScopedFunc()).toBe(32)

  def it_should_require_all_injections(self):
    @ioc.Inject
    def Injected(val=ioc.IN): pass
    expect(Injected).toRaise(ValueError)


if __name__ == '__main__':
  run()
