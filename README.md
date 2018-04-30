# dPy

[![Build Status](https://travis-ci.org/google/dpy.png?branch=master)](https://travis-ci.org/google/dpy)

## Overview

**dPy** is a simple dependency injection library with serious power.

Yes, Python is a dynamic language so dependency injection is not necessary and might seem silly... but injection of components provides more than just the ability to test statically typed languages. It can make your code clearer, assist developers with straightforward modularization, and make testing super simple. Take a look at the examples below to see how your code can be transformed.

## Examples
Below are some simple examples for using dPy. For a complete usage example set that alse runs, check out `example.py`.

### Simple
Any argument can be turned into an injected argument.

```py
from dpy import IN, Inject, Injectable

@Inject
def Go(where=IN):  # Go is fully injected!
  print 'Hello ' + where

Injectable.value(where='World')

Go()  # Invokes the function `Go` which the argument `where`=='World'.
# "Hello World" is printed. Just like if we had done Go("World") or Go(where="World")
```

### Mixing
You don't have to inject all of your arguments!

```py
from dpy import IN, Inject, Injectable

@Inject
def Go(when, how='train', where=IN):  # Partial injection
  print 'We need the %s %s, %s!' % (where, how, when)

Injectable.value(where='California')

Go('now', how='car')  # Invokes the function `Go` with `when`=='now', `how`=='car', and `where`=='here'.
# "We need the California car, now!" is printed.
```

### Scoping
Scopes are useful when creating servers or threaded designs that revisit the same code with different data.
You'll probably want to swap out injections, scoping them to a particular stack or thread.
As you would hope, they use the current scope when they are requested (not the one in which they were defined).
If not using scopes, it's an error to set the same injectable key more than once!

```py
from dpy import IN, Inject, Injectable, Scope

@Inject
def Go(where=IN):
  print 'Hello ' + where

@Scope
def HandleRequest(request):
  Injectable.value(where=request.destination)
  Go()  # Invokes the function `Go` with `where`==request.destination.
```

Singletons have the behavior you would expect; they are single to their scope branch.

### Injection Types
There are different ways to specify injectables.

```py
from dpy import Injectable, Singleton

Injectable.value(foo=object())
# 1) Provides an injectable `foo`.
# This is the simplest way to create an injectable value.
# When injecting the key `foo`, it will always _be_ (i.e. `is`) the same object.
# In effect, the injectable `foo` is a singleton object.

@Injectable
def bar():
  """2) Provides an injectable `bar`.

  This function is run each time a `bar` injection is needed.
  In effect, no two injections of `bar` will ever be (i.e. `is`) the same object.
  """
  return object()

@Injectable
@Singleton
def cat():
  """3) Provides a singleton injectable `cat`.

  This function is only run once, no matter how many times the `cat` injection
  is needed. The return value is stored and the same value is returned each time.
  In effect, this is a lazily initialized version of #1.
  """
  return Object()

@Injectable.named('dog')
def ProvidePitbull():
  """Provides an injectable `dog`.

  This is functionally equivalent to #2. The only difference is
  the injectable key has been explicity set to `dog` instead of
  inferred from the function name.
  """
  return Object()
```

## Modules?
Injection modules? We don't need no stinking injection modules.

In dPy, Python modules serve as our injection modules. Provide whatever you want in your regular ol' module using the methods above and when you want to switch out the implementation, you can just switch which module you import.

Of course, you can also setup injectables behind conditionals if you like.

Modules may import their own dependencies or you might prefer to defer importing all your dependencies in a "main" module (or other organization). As long as all the dependencies are established at runtime, there's no problem.
    
## Testing
Testing is quite simple in dPy. The only concept dPy has of modules is as regular Python modules. There are no special injection modules. For a full, working example test, check out `example_test.py`.

In the normal mode, injections are automatically passed in for you to things labeled `Inject` or `Injectable`.
In test mode, this functionality is turned off!
Only normal arguments, or _specifically_ test injections may be used in test.

```py
@Injectable.value('bar', 'cat')

@Inject
def Foo(bar=IN): print(len(bar))

Foo()  # Normally, this prints `3`
# In test mode, this would raise an exception about expecting injection to occur.

Foo(bar='test')  # In test mode (and normal mode), this prints `4`
```
    
tl;dr: Using real injections is _not_ allowed in test mode!

### Enable test mode
Enabling test mode is one call in your test.
It may not be turned off once enabled, so feel free to put it at the top level of your test module.

```py
SetTestMode()
```

### Setup test mode injections
You might need to create special test injections depending on how you've structured your code.
Setting them up is straight-forward:

```py
SetUpTestInjecitons(
    foo=42,
    bar=1337,
)
```

See the best practices section for a warning about this, though.

## Best practices

### Things injected should be injected.
This prevents having to setup injections for test.

Injecting objects that are themselves injected is not required but alleviates the need to setup injections for test which may be confusing.

### Don't rely on injections for test.
It's best not to have to setup test injections. You should only need to use it when private methods are injected or call other injectable functions/constructors. In general, you should stick to injecting public methods. If you are using a lot of injections for test, it may be a sign of bad program design.

### Don't inject too much.
Dependency injection should be easy, not stressful. It's not a license for spaghetti code. Treat injections as called constructors. Don't overuse them, don't overthink them. Use them when they make sense. Use them when they'll make testing easier. Use them when they'll make your life easier, not the opposite!
