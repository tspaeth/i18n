#!/usr/bin/env python3
# -*- coding: utf-8 -*-

import logging
logger = logging.getLogger(__name__)

class Error(Exception):
  pass

from . import message
from . import term_printer
from . import term_styles as S


class MessagePrinter(object):
  def __init__(self, printer=None):
    self.printer = printer if printer else term_printer.TermPrinter()

  def _write_user_text(self, text):
    p = self.printer
    with p.show_nl(style=S.style_carriage_return):
      p.write(text, style=S.style_user_text)

  def _print_label_and_text(self, label, text, oneline=False):
    p = self.printer
    if oneline:
      p.write(label, style=S.style_label)
      p.write(": ")
      self._write_user_text(text)
    else:
      p.print(label, style=S.style_label)
      with self.printer.indent():
        self._write_user_text(text)
    p.print()

  def _write_placeholder(self, placeholder):
    p = self.printer
    p.print(S.style_placeholder(placeholder.name))
    with p.indent():
      if placeholder.comment:
        self._print_label_and_text("comment", placeholder.comment, oneline=True)
      if placeholder.examples:
        if len(placeholder.examples) == 1:
          p.write(S.style_h2("example"))
          p.write(": ")
          example = placeholder.examples[0]
          p.print(example)
        else:
          p.print(S.style_h2("Examples"))
          with p.indent():
            for example in placeholder.examples:
              p.print(example)

  def _write_placeholders(self, placeholders_by_name):
    p = self.printer
    p.print(S.style_h2("Placeholders"))
    with p.indent():
      for (name, placeholder) in placeholders_by_name.items():
        self._write_placeholder(placeholder)

  def _write_message_parts(self, parts):
    p = self.printer
    for part in parts:
      if isinstance(part, str):
        self._write_user_text(part)
      elif isinstance(part, message.Placeholder):
        p.write(part.name, style=S.style_placeholder)
      elif isinstance(part, message.TagPair):
        p.write(part.ph_begin.name, style=S.style_placeholder)
        p.write(" ")
        self._write_message_parts(part.parts)
        p.write(part.ph_end.name, style=S.style_placeholder)
      else:
        raise Error("Unexpected condition")
      p.write(" ")

  def print_message(self, msg):
    p = self.printer
    p.print("{0}: id={1}".format(S.style_h1("MESSAGE"), msg.id))
    with p.indent():
      self._write_message_parts(msg.parts); p.print()
      if msg.meaning:
        self._print_label_and_text("meaning", msg.meaning)
      if msg.comment:
        self._print_label_and_text("comment", msg.comment)
      self._write_placeholders(msg.placeholders_by_name)
