#!/usr/bin/env python3
# -*- coding: utf-8 -*-

import logging
logger = logging.getLogger(__name__)

import sys, os, errno, io, subprocess, re, textwrap
import collections, functools, itertools
import contextlib


nop = lambda x: x


class TermPrinter(object):
  def __init__(self, out=sys.stdout):
    self._indent = ""
    self._out = out
    self._at_newline = True
    self._nl_char = ""
    self._nl_style = nop

  @contextlib.contextmanager
  def show_nl(self, char="↵", style=None):
    old_nl_char, old_nl_style = self._nl_char, self._nl_style
    self._nl_char, self._nl_style = char, (style if style else nop)
    try:
      yield self
    finally:
      self._nl_char, self._nl_style = old_nl_char, old_nl_style

  @contextlib.contextmanager
  def indent(self, spaces=2):
    old_indent = self._indent
    self._indent += " "*spaces
    try:
      yield self
    finally:
      self._indent = old_indent

  def _write_part_of_single_line(self, part, style):
    if not part:
      return
    if self._at_newline:
      self._out.write(self._indent)
      self._at_newline = False
    self._out.write(style(part))

  def _write_nl(self):
    if self._nl_char:
      self._out.write(self._indent)
      self._out.write(self._nl_style(self._nl_char))
    self._out.write("\n")
    self._at_newline = True

  def print(self, s="", style=None):
    self.write(s+"\n", style=style)

  def write(self, s, style=None):
    if not s:
      return
    if not style:
      style = nop
    parts_iter = iter(s.split("\n"))
    self._write_part_of_single_line(next(parts_iter), style=style)
    for part in parts_iter:
      self._write_nl()
      self._write_part_of_single_line(part, style=style)
