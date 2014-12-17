#!/usr/bin/env python3
# -*- coding: utf-8 -*-

__all__ = "pp pf".split()

import pprint
import lxml.html

class PrettyPrinter(pprint.PrettyPrinter, object):
  def __init__(self, *args, **kwargs):
    self._pp = pprint.PrettyPrinter(*args, **kwargs)
    return super(PrettyPrinter, self).__init__(*args, **kwargs)


  # Args: (obj, context, maxlevels, level)
  #   obj: the object to be presented.
  #   context: dictionary which contains the id() of objects that are part of the
  #       current presentation context (direct and indirect containers for
  #       object that are affecting the presentation) as the keys.
  #       Recursive calls to format() should add additional
  #   maxlevels: requested recursion limit; 0 implies no limit.  Passed this
  #       unmodified to recursive calls.
  #   level: current level; recursive calls should be passed a value less than
  #       that of the current call.
  #
  # Returns: (formatted_value, is_readable, was_recursion_detected).
  #   was_recursion_detected: if an object needs to be presented which is
  #       already represented in context, then set was_recursion_detected=True.
  def format(self, obj, context, maxlevels, level):
    if isinstance(obj, lxml.html.HtmlElement):  # isinstance(obj, lxml.etree._Element)
      return (lxml.html.tostring(obj, pretty_print=True).decode("utf-8"), True, (id(obj) in context))
    return super(PrettyPrinter, self).format(obj, context, maxlevels, level)

__pretty_printer = PrettyPrinter()

pp = __pretty_printer.pprint
pf = __pretty_printer.pformat
