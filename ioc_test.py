#!/usr/bin/python
import logging
import sys

import ioc
from jazz import jazz
from jazz.jazz import create_spy
from jazz.jazz import Describe
from jazz.jazz import expect

if 'debug' in sys.argv:
  logging.getLogger().setLevel(logging.DEBUG)


class Ioc(Describe):

  def before_each(self):
    reload(ioc)

  def it_should_inject(self):

    @ioc.Injectable
    def foo():  # pylint: disable=unused-variable
      return 42

    @ioc.Inject
    def bar(foo=ioc.IN):
      return foo

    expect(bar()).toBe(42)

  def it_should_allow_overwriting_injectables(self):

    @ioc.Injectable
    def foo():  # pylint: disable=unused-variable
      return 42

    @ioc.Inject
    def bar(foo=ioc.IN):
      return foo

    expect(bar(foo=99)).toBe(99)

  def it_should_support_naming_injectables(self):

    @ioc.Injectable.named('bar')
    def foo():  # pylint: disable=unused-variable
      return 42

    @ioc.Inject
    def bar(bar=ioc.IN):
      return bar

    expect(bar()).toBe(42)

  def it_should_allow_calling_injectables(self):

    @ioc.Injectable
    def foo(bar=ioc.IN):
      return 'foo %s' % bar

    ioc.Injectable.value(bar='bar')

    expect(foo()).toEqual('foo bar')
    expect(foo(bar='candybar')).toEqual('foo candybar')

  def it_should_support_singleton_functions(self):

    @ioc.Injectable
    @ioc.Singleton
    def singleton():  # pylint: disable=unused-variable
      return object()

    @ioc.Inject
    def ReturnSingleton(singleton=ioc.IN):
      return singleton

    expect(ReturnSingleton()).toBe(ReturnSingleton())

  def it_should_support_singleton_classes(self):
    # pylint: disable=unused-variable

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
    def singleton():  # pylint: disable=unused-variable
      spy()

    @ioc.Inject
    def ReturnSingleton(singleton=ioc.IN):
      return singleton
    ioc.Warmup()
    expect(spy.call_count).toBe(1)
    ReturnSingleton()
    expect(spy.call_count).toBe(1)

  def it_should_support_multiple_scopes(self):
    ioc.Injectable.value(root=99)

    @ioc.Inject
    def InjectedFunc(scoped=ioc.IN, root=ioc.IN):
      return scoped, root

    @ioc.Scope
    def ScopedFunc():
      ioc.Injectable.value(scoped=32)
      return InjectedFunc()

    expect(ScopedFunc()).toEqual((32, 99))
    expect(InjectedFunc).toRaise(ValueError)

  def it_should_support_multiple_threads(self):

    class T(ioc.threading.Thread):
      @ioc.Inject
      def run(self, bar=ioc.IN):
        self.setName(bar)

    ioc.Injectable.value(bar='baz')
    t = T()
    t.start()
    t.join()

    expect(t.name).toEqual('baz')

  def it_should_support_the_main_thread_adding_scopes_for_children(self):

    class T(ioc.threading.Thread):

      @ioc.Inject
      def run(self, bar=ioc.IN):
        self.setName(bar)
        expect(len(ioc._MyScopes())).toBe(2)


    @ioc.Scope
    def NewScope():
      expect(len(ioc._MyScopes())).toBe(2)
      ioc.Injectable.value(bar='baz')
      t = T()
      t.start()
      t.join()
      return t.name

    expect(len(ioc._MyScopes())).toBe(1)
    expect(NewScope()).toEqual('baz')


  def it_should_tolerate_layering_injection_wrappers(self):

    def InjectInjectable():
      @ioc.Inject
      @ioc.Injectable
      def foo(baz=ioc.IN):  # pylint: disable=unused-variable
        return baz

    def InjectableInject():
      @ioc.Injectable
      @ioc.Inject
      def bar(baz=ioc.IN):  # pylint: disable=unused-variable
        return baz

    ioc.Injectable.value(baz=42)  # To ensure that foo is wrapped.

    expect(InjectInjectable).notToRaise(AssertionError)
    expect(InjectableInject).notToRaise(AssertionError)

  def it_should_allow_calling_injectables_for_testability(self):

    @ioc.Injectable
    def foo(val=ioc.IN):
      return val

    expect(foo(val=99)).toBe(99)

  def it_should_detect_name_conflict_in_same_scope(self):

    def InjectValue():
      ioc.Injectable.value(val=42)

    InjectValue()
    expect(InjectValue).toRaise(ValueError)

  def it_should_detect_name_conflict_in_all_parent_scopes(self):
    ioc.Injectable.value(val=42)

    @ioc.Scope
    def ScopedFunc():
      ioc.Injectable.value(val=32)

    expect(ScopedFunc).toRaise(ValueError)

  def it_should_require_all_injections(self):

    @ioc.Inject
    def Injected(val=ioc.IN):
      return val
    expect(Injected).toRaise(ValueError)

  def it_should_not_mangle_classes(self):

    @ioc.Inject
    class Bar(object):
      def __init__(self):
        super(Bar, self).__init__()

    expect(Bar).notToRaise(TypeError)

  def it_should_allow_subclassing_injectables(self):

    @ioc.Inject
    class Foo(object):
      def __init__(self, bar=ioc.IN):
        self.bar = bar

    @ioc.Injectable
    class Bar(Foo): pass

    ioc.Injectable.value(bar=3)
    expect(Bar().bar).toBe(3)


class IocTestMode(Describe):

  def before_each(self):
    reload(ioc)
    ioc.SetTestMode()

    @ioc.Inject
    def InjectedFunc(val=ioc.IN):
      return val

    self.injected_func = InjectedFunc
    self.injected_value = 42

    ioc.Injectable.value(val=self.injected_value)

  def after_each(self):
    # We have to turn off test mode since we're reloading ioc.
    ioc.SetTestMode(enabled=False)

  def it_should_allow_passing_args(self):
    expect(self.injected_func(val=99)).toBe(99)

  def it_should_not_inject(self):
    expect(self.injected_func).toRaise(ioc.InjectionDuringTestError)

  def it_should_allow_passing_none(self):
    expect(self.injected_func(val=None)).toBeNone()

  def it_should_support_super_class_testing(self):

    @ioc.Inject
    class Foo(object):
      def __init__(self, baz=ioc.IN):
        self.baz = baz
      def method(self):
        return 99

    @ioc.Injectable
    class Bar(Foo):
      def __init__(self):
        super(Bar, self).__init__()

    ioc.SetSuperClassInjections(Foo, baz=32)
    ioc.Injectable.value(baz=42)

    b = Bar()
    expect(b.baz).toBe(32)
    expect(b.method()).toBe(99)

  def it_should_work_normally_for_non_injected_classes(self):

    class Foo(object):
      def __init__(self):
        self.baz = 42
      def method(self):
        return 99

    class Bar(Foo):
      def __init__(self):
        super(Bar, self).__init__()

    b = Bar()
    expect(b.baz).toBe(42)
    expect(b.method()).toBe(99)


if __name__ == '__main__':
  jazz.run()
