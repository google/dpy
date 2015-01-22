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
    expect(InjectedFunc).toRaise(ioc.InjectionMissingError)

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

  def it_should_override_name_in_parent_scope(self):
    ioc.Injectable.value(val=42)

    @ioc.Inject
    def GetVal(val=ioc.IN):
      return val

    @ioc.Scope
    def ScopedFunc():
      ioc.Injectable.value(val=32)
      return GetVal()

    expect(GetVal()).toBe(42)
    expect(ScopedFunc()).toBe(32)

  def it_should_require_all_injections(self):

    @ioc.Inject
    def Injected(val=ioc.IN):
      return val
    expect(Injected).toRaise(ioc.InjectionMissingError)

  def it_should_allow_override_unprovided_injections(self):

    @ioc.Inject
    def Injected(val=ioc.IN):
      return val
    expect(Injected(val=42)).toEqual(42)

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


class IocInjectionSentinel(Describe):

  def it_should_raise_when_attrs_are_accessed(self):

    def InjectedFunc(val=ioc.IN):
      return val.Foo()

    expect(InjectedFunc).toRaise()

class IocTestMode(Describe):

  def before_each(self):
    reload(ioc)
    ioc.SetTestMode()

    @ioc.Inject
    def InjectedFunc(val=ioc.IN):
      return val

    self.injected_func = InjectedFunc
    self.injected_value = 42

    @ioc.Inject
    def MultiInjectedFunc(val=ioc.IN, add_val=ioc.IN):
      return val, add_val

    self.multi_injected_func = MultiInjectedFunc

    ioc.Injectable.value(val=self.injected_value)

  def it_should_allow_passing_args(self):
    expect(self.injected_func(val=99)).toBe(99)

  def it_should_not_inject(self):
    expect(self.injected_func).toRaise(ioc.TestInjectionsNotSetupError)

  def it_should_raise_missing_injection_errors(self):
    ioc.SetUpTestInjections(foo=32)
    expect(self.injected_func).toRaise(ioc.InjectionMissingError)

  def it_should_allow_passing_none(self):
    expect(self.injected_func(val=None)).toBeNone()

  def it_should_support_setting_multiple_test_injections(self):
    ioc.SetUpTestInjections(val=32, add_val=64)
    expect(self.multi_injected_func()).toEqual((32, 64))

  def it_should_support_overwriting_test_scope(self):
    ioc.SetUpTestInjections(val=32)
    expect(self.injected_func()).toBe(32)
    ioc.SetUpTestInjections(val=99)
    expect(self.injected_func()).toBe(99)

  def it_should_support_adding_to_test_scope(self):
    ioc.SetUpTestInjections(val=32)
    expect(self.injected_func()).toBe(32)
    ioc.SetUpTestInjections(add_val=64)
    expect(self.multi_injected_func()).toEqual((32, 64))

  def it_should_support_clearing_test_scope(self):
    ioc.SetUpTestInjections(val=32)
    ioc.TearDownTestInjections()
    expect(self.injected_func).toRaise(ioc.TestInjectionsNotSetupError)

  def it_should_support_injecting_functions(self):
    ioc.SetUpTestInjections(val=32)
    expect(self.injected_func()).toBe(32)

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

    ioc.SetUpTestInjections(baz=32)
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

  def it_should_work_with_super_classes_multiple_times(self):

    class Foo(object):
      def __init__(self):
        self.baz = 42

    class Bar(Foo):
      def __init__(self):
        super(Bar, self).__init__()

    expect(Bar().baz).toBe(42)
    expect(Bar().baz).toBe(42)


class IocSingleton(Describe):

  def before_each(self):
    reload(ioc)

  def it_should_support_singleton_functions(self):

    @ioc.Injectable
    @ioc.Singleton
    def singleton():  # pylint: disable=unused-variable
      return object()

    @ioc.Inject
    def ReturnSingleton(singleton=ioc.IN):
      return singleton

    expect(ReturnSingleton()).toBe(ReturnSingleton())

  def it_should_support_injectable_arg_in_singleton_functions(self):

    @ioc.Injectable
    @ioc.Singleton
    def singleton(val=ioc.IN):
      return val

    @ioc.Inject
    def ReturnSingletonVal(singleton=ioc.IN):
      return singleton

    val = object()
    ioc.Injectable.value(val=val)

    expect(ReturnSingletonVal()).toBe(val)

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

  def it_should_support_injectable_arg_in_singleton_classes(self):
    # pylint: disable=unused-variable

    @ioc.Injectable
    @ioc.Singleton
    class singleton(object):
      def __init__(self, val=ioc.IN):
        self.val = val

    @ioc.Inject
    def ReturnSingleton(singleton=ioc.IN):
      return singleton

    val = object()
    ioc.Injectable.value(val=val)

    expect(ReturnSingleton()).toBe(ReturnSingleton())
    expect(ReturnSingleton().val).toBe(val)

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


  class ScopedSingletonClass(Describe):

    def before_each(self):
      @ioc.Injectable.named('root_singleton')
      @ioc.Singleton
      class RootSingleton(object):
        def __init__(self):
          pass

      @ioc.Injectable.named('parent_singleton')
      @ioc.Singleton
      class ParentSingleton(object):
        def __init__(self, parent_val=ioc.IN):
          self.val = parent_val

      @ioc.Injectable.named('leaf_singleton')
      @ioc.Singleton
      class LeafSingleton(object):
        def __init__(self, leaf_val=ioc.IN):
          self.val = leaf_val

    def it_should_attach_to_root(self):
      @ioc.Inject
      def GetSingleton(root_singleton=ioc.IN):
        return root_singleton

      @ioc.Scope
      def ParentScope():
        @ioc.Scope
        def LeafScope():
          # Get root_singleton for the first time inside leaf scope.
          return GetSingleton()
        return LeafScope()

      # The singleton value should attach to the root scope.
      expect(ParentScope()).toBe(GetSingleton())

    def it_should_attach_to_parent(self):
      @ioc.Inject
      def GetSingleton(parent_singleton=ioc.IN):
        return parent_singleton

      @ioc.Scope
      def ParentScope():
        ioc.Injectable.value(parent_val=object())

        @ioc.Scope
        def LeafScope():
          # Get parent_singleton for the first time inside leaf scope.
          return GetSingleton()
        # The singleton should stay the same even leaf scope is popped.
        expect(LeafScope()).toBe(GetSingleton())

      ParentScope()
      # parent_singleton should have been popped.
      expect(GetSingleton).toRaise(ValueError)

    def it_should_attach_to_leaf(self):
      @ioc.Inject
      def GetSingleton(leaf_singleton=ioc.IN):
        return leaf_singleton

      @ioc.Scope
      def ParentScope():

        @ioc.Scope
        def LeafScope():
          ioc.Injectable.value(leaf_val=object())
          return GetSingleton()

        expect(LeafScope()).notToBeNone()
        # leaf_singleton should have been popped.
        expect(GetSingleton).toRaise(ValueError)

      ParentScope()

    def it_should_save_injectable_singleton_class(self):
      @ioc.Inject
      class RootInstance(object):
        def __init__(self, parent=ioc.IN):
          self.value = parent.value

      @ioc.Injectable.named('parent')
      @ioc.Singleton
      class ParentSingleton(object):
        def __init__(self, leaf_instance=ioc.IN):
          self.value = leaf_instance.value

      @ioc.Injectable.named('leaf_instance')
      class LeafInstance(object):
        value = 'Leaf Instance'

        def __init__(self):
          pass

      expect(RootInstance().value).toBe(LeafInstance.value)


  class ScopedSingletonFunction(Describe):

    def before_each(self):
      @ioc.Injectable
      @ioc.Singleton
      def root_singleton():
        return object()

      @ioc.Injectable
      @ioc.Singleton
      def parent_singleton(parent_val=ioc.IN):
        return object()

      @ioc.Injectable
      @ioc.Singleton
      def leaf_singleton(leaf_val=ioc.IN):
        return object()

    def it_should_attach_to_root(self):
      @ioc.Inject
      def GetSingleton(root_singleton=ioc.IN):
        return root_singleton

      @ioc.Scope
      def ParentScope():

        @ioc.Scope
        def LeafScope():
          # Get root_singleton for the first time inside leaf scope.
          return GetSingleton()
        return LeafScope()

      # The singleton value should attach to the root scope.
      expect(ParentScope()).toBe(GetSingleton())

    def it_should_attach_to_parent(self):
      @ioc.Inject
      def GetSingleton(parent_singleton=ioc.IN):
        return parent_singleton

      @ioc.Scope
      def ParentScope():
        ioc.Injectable.value(parent_val=object())

        @ioc.Scope
        def LeafScope():
          # Get parent_singleton for the first time inside leaf scope.
          return GetSingleton()
        # The singleton should stay the same even leaf scope is popped.
        expect(LeafScope()).toBe(GetSingleton())

      ParentScope()
      # parent_singleton should have been popped.
      expect(GetSingleton).toRaise(ValueError)

    def it_should_attach_to_leaf(self):
      @ioc.Inject
      def GetSingleton(leaf_singleton=ioc.IN):
        return leaf_singleton

      @ioc.Scope
      def ParentScope():

        @ioc.Scope
        def LeafScope():
          ioc.Injectable.value(leaf_val=object())
          return GetSingleton()

        expect(LeafScope()).notToBeNone()
        # leaf_singleton should have been popped.
        expect(GetSingleton).toRaise(ValueError)

      ParentScope()

    def it_should_track_recursive_dep_and_attach_to_the_deepest(self):
      @ioc.Injectable
      def parent_val(leaf_val=ioc.IN):
        return leaf_val

      @ioc.Inject
      def GetSingleton(parent_singleton=ioc.IN):
        return parent_singleton

      @ioc.Scope
      def ParentScope():

        @ioc.Scope
        def LeafScope():
          ioc.Injectable.value(leaf_val=object())
          expect(GetSingleton()).toBe(GetSingleton())
          return GetSingleton()

        expect(LeafScope()).notToBeNone()
        # parent_singleton should attach to leaf because parent_val depends on
        # leaf_val
        expect(GetSingleton).toRaise(ValueError)

      ParentScope()
      expect(GetSingleton).toRaise(ValueError)

if __name__ == '__main__':
  jazz.run()
