# dPy

[![Build Status](https://travis-ci.org/google/dpy.png?branch=master)](https://travis-ci.org/google/dpy)

## Overview

**dPy** is a simple dependency injection libary with serious power.

Yes, Python is a dynamic language so dependency injection is not necessary, but injection provides more than just the ability to test static languages. It makes your code clearer, assists developers with straightforward modularization, and makes testing extremely simple. With dPy, the effects are even clearer.

## Examples
Here are some straightforward examples for using dPy. For a complete, working example, check out `example.py`.

### Simple
Any argument can be turned into an injected argument.

    import dpy
    
    def Go(where=dpy.IN):  # Go is fully injected!
      # Do something here...
    
    dpy.Injectable.value(where='here')
    
    Go()  # Invokes Go(where='here')

### Mixed
You don't have to have all of your arguments injected!

    import dpy
    
    def Go(when, how=TRAIN, where=dpy.IN):  # Partial injection
      # Do something here...
    
    dpy.Injectable.value(where='here')
    
    Go('now', how=CAR)  # Invokes Go('now', how='car', where='here')

### Scoped
When creating servers or other designs which revisit code (e.g. threads), you may want to swap out injections, scoping them to a particular stack. If you don't use a scope, it's an error to set the same injectable key more than once!

    import dpy
    
    def Go(when, how=TRAIN, where=dpy.IN):  # Partial injection
      # Do something here...
    
    @dpy.Scope
    def HandleRequest(request):
      dpy.Injectable.value(where=request.destination)
      Go()  # Invokes Go(where=request.destination)

### Injection Types
There are different ways to specify injectables.

    import dpy
    
    dpy.Injectable.value(foo=Object())
    # 1) This is the simplest way to create an injectable value.
    # When injecting the key `foo`, it will always _be_ that object.
    # In effect, the injectable `foo` is a singleton object.
    
    @dpy.Injectable
    def Foo():
      """2) Provides an injectable `Foo`.
      
      This function is ran for each function requesting a `Foo`.
      In effect, no two injections of `Foo` will be the same object.
      """
      return Object()
    
    @dpy.Injectable
    @dpy.Singleton
    def Bar():
      """3) Provides a singleton injectable `Bar`.
      
      This function is only ran once, no matter how many times a `Bar`
      is requested for injection. The return value is stored.
      In effect, this is a lazily initialized version of #1.
      """
      return Object()
    
    @dpy.Injectable.named('bar')
    def ProvideBar():
      """Provides an injectable `bar`.
      
      This is functionally equivalent to #2. The only differenc is
      the injectable key has been explicity set to `bar` instead of
      inferred from the function name.
      """
      return Object()

## Modules?
Injection modules? We don't need no stinking injection modules.

In dPy, Python modules serve as our injection modules. Provide whatever you want in your regular ol' module and when you want to switch out the implementation, you can just switch which module you import.

Of course, you may setup injectables behind conditionals if you want.
    
## Testing
Testing is really simple in dPy. The only concept of modules is the same concept as regular Python. There are no special injection modules. For an example test, check out `example_test.py`.

Normally, you may not call a function and override its injectable values. e.g. The following is an error:

    def Foo(bar=dpy.IN):
      # ...
    Foo(bar=42)
    
In test mode, this is not true. You may simply set any injectable value to whatever you want to test. In fact, using real injections in disallowed in test mode!

### Enable test mode
Enabling test mode is one call in your tests.

    dpy.SetTestMode()

### Setup test mode injections
Setting up your injectables for test in one call, too!

    dpy.SetUpTestInjecitons(
        foo=42,
        bar=1337,
    )

See the best practices section for a warning about this, though.

## Best practices

### Things injected should be injected.
This prevents having to setup injections for test.

Injecting objects that are themselves injected is not required but alleviates the need to setup injections for test which may be confusing.

### Don't rely on injections for test.
It's best not to have to setup test injections. You should only need to use it when private methods are injected or call other injectable functions/constructors. In general, you should stick to injecting public methods. If you are using a lot of injections for test, it may be a sign of bad program design.

### Don't inject too much.
Dependency injection should be easy, not stressful. It's not a license for spaghetti code. Treat injections as called constructors. Don't overuse them, don't overthink them. Use them when they make sense. Use them when they'll make testing easier. Use them when they'll make your life easier, not the opposite!
