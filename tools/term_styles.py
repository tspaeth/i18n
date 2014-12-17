#!/usr/bin/env python3
# -*- coding: utf-8 -*-

import logging
logger = logging.getLogger(__name__)

try:
  import pygments, pygments.lexers, pygments.formatters
except ImportError:
  pygments = None


class Error(Exception):
  pass


import sys, os, errno, io, subprocess, re, textwrap
import collections, functools, itertools

class DummyTermColor(object):
  def colored(self, text, *args, **kwargs):
    return text

termcolor = DummyTermColor()

if sys.stdout.isatty():
  try: import termcolor
  except ImportError: pass


def style_h1(s):
  return termcolor.colored(s, "blue", attrs=["bold"])

def style_h2(s):
  return termcolor.colored(s, "blue")

def style_label(s):
  return termcolor.colored(s, "blue")

def style_user_text(s):
  # return termcolor.colored(s, on_color="on_cyan", attrs=["bold"])
  return termcolor.colored(s, attrs=["underline"])

def style_placeholder(s):
  return termcolor.colored(s, "magenta")

def style_carriage_return(s):
  return termcolor.colored(s, attrs=["bold"])

def style_html(html):
  if not pygments:
    return html
  return pygments.highlight(html,
                            pygments.lexers.HtmlLexer(),
                            pygments.formatters.Terminal256Formatter(style="default"))
