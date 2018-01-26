#!/usr/bin/python
"""Tests for example module."""
import example
from jazz import jazz


class HelloTest(jazz.Describe):

  def before_each(self):
    example.ioc.SetTestMode()

  def it_should_hello(self):
    msg = example.hello(
        greet='Greeting', app_name='Hello Method', user='Test User')
    jazz.expect(msg).toEqual('<p>Hello Method: Greeting Test User</p>')


if __name__ == '__main__':
  jazz.run()
