#!/usr/bin/env python
# -*- coding: utf-8 -*-

import logging
logger = logging.getLogger(__name__)

import itertools
from collections import deque, OrderedDict, namedtuple, defaultdict
import lxml.html
import re


from . import message
from .pretty_print import pp, pf


class Error(Exception):
  pass


UMLAUT = "\u0308"

def _pseudo_translate_word(word):
  accented_word = "".join(c + UMLAUT if 33 <= ord(c) <= 126 else c for c in word)
  return word + " " + accented_word

def _pseudo_translate_text(text):
  return re.sub(r"\w+", lambda m: _pseudo_translate_word(m.group()), text)

def _pseudo_translate_part(part):
  if isinstance(part, str):
    return _pseudo_translate_text(part)
  elif isinstance(part, message.Placeholder):
    return part
  elif isinstance(part, message.TagPair):
    part.parts = list(map(_pseudo_translate_part, part.parts))
    return part
  else:
    raise Error("Unexpected condition")


def pseudo_translate(msg):
  msg.parts = list(map(_pseudo_translate_part, msg.parts))
  return msg
