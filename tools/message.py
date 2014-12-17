#!/usr/bin/env python3
# -*- coding: utf-8 -*-

import logging
logger = logging.getLogger(__name__)

import cgi
import itertools
from collections import deque, OrderedDict, namedtuple, defaultdict
import re
import hashlib

from .pretty_print import pp, pf

class Error(Exception):
  pass

class LintError(Error):
  pass

# Callback:  During (pseudo-)translation, we parse the source files and want to
# perform DOM transforms.  For each extracted message, we would see if we have
# a translated version of the message available and if it is, transform the DOM
# node or attribute to by replacing the original message parts with the
# translated versions.
# Note that the message ID fingerprinting will ensure that the DOM structures
# are compatible.  However, whenever the user had overridden the message ID in
# either the old or newly extracted message, we should still perform an
# explicit check to confirm that the structures and placeholders are still
# compatible.
class OnParseBase(object):
  def on_attrib(self, message, node, attr): pass
  def on_node(self, message, node): pass


# Escaping Contexts.
# A message can be either plain text, html text (whitespace coalescing doesn't
# change the fingerprint) or HTML dom nodes.
# The escaping context is the surrounding context in which the message appears.
# For instance, the following two messages wlll be considered identical and
# only translated once.
#   1. <!--i18n-->1,"2",3<!--/i18n-->
#   2. <foo bar="1,&quot;,2,&quot;3" i18n-bar>
# However, they will be escaped differently when they are substituted back into
# the DOM (the attribute will need to be escaped for use in as an attribute.)
CONTEXT_RAW = 0
CONTEXT_HTML = 1
CONTEXT_ATTRIBUTE_VALUE = 2

def _escape(text, escaping_context):
  if escaping_context == CONTEXT_RAW:
    return text
  elif escaping_context == CONTEXT_HTML:
    return cgi.escape(text)
  elif escaping_context == CONTEXT_ATTRIBUTE_VALUE:
    return cgi.escape(text, True)
  else:
    raise Error("Unknown escaping context: {0}".format(escaping_context))


# TODO: Messages could optionally link to the SourceFile(s) from which they
# were extracted.  This isn't strictly necessary but nice to have.  This
# information can be exposed in XLIFF files (<header><skl><external-file href=...">)
# At the minimum, we want to store the filename here.  We might also store the
# line number and file sha1 (e.g. "git rev-parse HEAD:path/to/file").
# In the prototype web UI of extracted messages, they server can then allow one
# to click through the extracted messages and see all the places they were
# extracted from and exactly what the file looked like at that point.  (For
# GitHub or other recognized projects, it could link directly to the GitHub.)
# - filename
# - line and column number
# - blob sha
# - URL
class SourceFile(object): pass
class SourceReference(object): pass


# SPECIAL PLACEHOLDERS
#
# EMBEDDED_MESSAGES
#
# String id: required
# List<Text or PlaceholderRef> parts
# Map<PH_NAME, Placeholder> placeholders
# examples
# sources
#
# id: the canonical fingerprint of this message.  Messages are immutable.
class Message(object):
  def __init__(self, id, meaning, comment, parts, placeholders_by_name):
    self.id = id
    self.meaning = meaning
    self.comment = comment
    self.parts = parts
    self.placeholders_by_name = placeholders_by_name

  def _unparse_part(self, part):
    return part if isinstance(part, str) else part.unparse()

  def unparse(self):
    return "".join(map(self._unparse_part, self.parts))

  # Pretty printing for developers.
  def __str__(self):
    kvs = [(k, v) for (k, v) in
           ((k, getattr(self, k)) for k in "id meaning comment parts".split())
           if v]
    return 'Message(%s)' % ", ".join("%s=%s" % (k, (pf(v) if v is list else repr(v))) for (k, v) in kvs)

  def __repr__(self):
    return str(self)


ParsedComment = namedtuple("ParsedComment", ("meaning", "comment"))

def parse_raw_comment(raw_comment):
  parts = tuple(raw_comment.split("|", 1))
  parts = [part.strip() for part in parts]
  if len(parts) == 1:
    return ParsedComment(None, parts[0])
  meaning = parts[0]
  comment = parts[1]
  if not meaning:
    raise LintError("meaning was explicitly specified but is empty")
  return ParsedComment(meaning, comment)


def get_fingerprint(obj):
  return obj if isinstance(obj, str) else obj.get_fingerprint()


# Used by the message builder.
# Store all placeholders and tag pairs with or without IDs/names until the
# point at which we can definitively assign IDs to them in a deterministic
# fashion.  Sub-messages will use this same registry for placeholders in order
# to support export formats that require placeholders to be unique across the
# entire message.
class PlaceholderRegistry(object):
  def __init__(self):
    self._names_seen = set()
    self._by_canonical = OrderedDict()
    self._counts_by_prefix = defaultdict(lambda: itertools.count(1))
    self.counter = itertools.count(1)

  def to_dict(self):
    for placeholder_or_tag in self._by_canonical.values():
      self._ensure_name(placeholder_or_tag)
    result = OrderedDict()
    for placeholder_or_tag in self._by_canonical.values():
      if isinstance(placeholder_or_tag, Placeholder):
        result[placeholder_or_tag.name] = placeholder_or_tag
      elif isinstance(placeholder_or_tag, TagPair):
        tag_pair = placeholder_or_tag
        result[tag_pair.ph_begin.name] = tag_pair.ph_begin
        result[tag_pair.ph_end.name] = tag_pair.ph_end
      else:
        raise Error("Internal Error")
    return result

  def _generate_name_hint(self, placeholder):
    if isinstance(placeholder, TagPair):
      # TODO: Define and use a FIXED mapping registry for HtmlTagPair's.  For instance,
      # the <a> tag can be "LINK" instead of "A".  Such a mapping cannot be
      # changed later because it would break message fingerprinting.
      MAPPINGS = defaultdict(dict, {
        HtmlTagPair.__name__: dict(A="LINK")
      })
      return MAPPINGS.get(placeholder.__class__.__name__).get(placeholder.tag.upper(), placeholder.tag.upper())
    else:
      # TODO: Here too, define and use a more friendly fixed mapping for auto-generating placeholder names.
      # For NgExpr, while it might be nice to use the actual expression, this
      # is not advisable because a change in the expression should not result
      # in a retranslation.
      return "EXPRESSION" if isinstance(placeholder, NgExpr) else "PH"

  def _ensure_names_for_tag(self, placeholder):
    if placeholder.ph_begin.name:
      return
    name_hint = self._generate_name_hint(placeholder)
    begin_basename = ph_begin_name = name_hint + "_BEGIN"
    end_basename   = ph_end_name   = name_hint + "_END"
    counter = self._counts_by_prefix[begin_basename]
    while (ph_begin_name in self._names_seen or ph_end_name in self._names_seen):
      count = next(counter)
      ph_begin_name = '{0}_{1}'.format(begin_basename, count)
      ph_end_name =   '{0}_{1}'.format(end_basename,   count)
    self._names_seen.add(ph_begin_name)
    self._names_seen.add(ph_end_name)
    placeholder.ph_begin.name = ph_begin_name
    placeholder.ph_end.name = ph_end_name

  def _ensure_name_for_placeholder(self, placeholder):
    if placeholder.name:
      return
    basename = name = self._generate_name_hint(placeholder)
    counter = self._counts_by_prefix[basename]
    while name in self._names_seen:
      name = '{0}_{1}'.format(basename, next(counter))
    self._names_seen.add(name)
    placeholder.name = name

  def _ensure_name(self, placeholder):
    if isinstance(placeholder, TagPair):
      self._ensure_names_for_tag(placeholder)
    else:
      self._ensure_name_for_placeholder(placeholder)

  # Tag order is important for message fingerprinting.  The placeholder names
  # that are auto-generated should be deterministic but not conflict with any
  # explicitly coded placeholders seen later.  So we just note the tag at this
  # point and fix it's name later.
  def reserve_new_tag(self, tagName):
    canonical_key = "TAG_{0}_{1}".format(tagName, next(self.counter))
    self._by_canonical[canonical_key] = None
    return canonical_key

  def update_placeholder(self, placeholder):
    if isinstance(placeholder, TagPair):
      return self._update_tag_placeholder(placeholder)
    else:
      return self._update_simple_placeholder(placeholder)

  def _update_tag_placeholder(self, placeholder):
    # TODO: Support explicit placeholder names for tags instead of synthesizing
    # them?
    # We don't want to dedupe tagged placeholders so we're going to treat this
    # as a complete new instance.  (e.g. not obvious what kind of UI we would
    # use if collapsed identical message parts.)
    canonical_key = placeholder.get_fingerprint()
    self._by_canonical[canonical_key] = placeholder
    return placeholder

  def _update_simple_placeholder(self, placeholder):
    canonical_key = placeholder.get_fingerprint()
    existing_placeholder = self._by_canonical.get(canonical_key)
    if existing_placeholder is not None:
      num_names = bool(placeholder.name) + bool(existing_placeholder.name)
      if num_names == 2:
        # These two names should match.
        if placeholder.name != existing_placeholder.name:
          raise Error("The same placeholder occurs more than once with a different placeholder name.")
      elif num_names == 1:
        if placeholder.name is None:
          placeholder.name = existing_placeholder.name
        else:
          existing_placeholder.name = placeholder.name
      # TODO: merge the examples from both placeholders
    else:
      self._by_canonical[canonical_key] = placeholder
    return placeholder


# Escape sequences for fingerprinting.
# Fingerprinting requires unique digests for unique messages.  The approach is
# to construct a unique long string for unique messages and use a fixed and
# good fingerprinting algorithm to get a smaller digest out of it (64/128 bits
# should be sufficient.)  These escape sequences are used in generating the
# unique long string per message.
ESCAPE_CHAR = "\x10"
ESCAPE_END = ESCAPE_CHAR + "."
BEGIN_TEXT = ESCAPE_CHAR + "'"
BEGIN_PH = ESCAPE_CHAR + "X"
BEGIN_TAG = ESCAPE_CHAR + "<"
END_TAG = ESCAPE_CHAR + ">"


def _escape_text_for_message_id(text):
  return text.replace(ESCAPE_CHAR, ESCAPE_CHAR+ESCAPE_CHAR)


class MessageBuilder(object):
  def __init__(self, raw_comment=None, parent=None, raw_message=None):
    self.parent = parent
    parsed_comment = parse_raw_comment(raw_comment)
    self.meaning = parsed_comment.meaning
    self.comment = parsed_comment.comment
    self.placeholder_registry = parent.placeholder_registry if parent else PlaceholderRegistry()
    if isinstance(raw_message, str):
      self.parts = parse_message_text_for_ng_expressions(raw_message, self.placeholder_registry)
    else:
      self.parts = parse_node_contents(raw_message, self.placeholder_registry)

  def _gen_id_parts_for_subparts(self, parts):
    placeholders = {}
    for part in parts:
      if isinstance(part, str):
        yield "{0}{2}{1}".format(BEGIN_TEXT, ESCAPE_END, _escape_text_for_message_id(part))
      elif isinstance(part, Placeholder):
        placeholders[part.name] = part
      elif isinstance(part, TagPair):
        yield "{0}{1},{2}{3}".format(BEGIN_TAG, part.ph_begin.name, type(part).__name__, ESCAPE_END)
        for i in self._gen_id_parts_for_subparts(part.parts):
          yield i
      else:
        raise Error("Encountered unknown message part type while computing message ID: {0}".format(type(part)))
    for name in sorted(placeholders):
      placeholder = placeholders[name]
      yield "{0}{1},{2}{3}".format(BEGIN_PH, name, type(placeholder).__name__, ESCAPE_END)

  def _gen_id_parts(self):
    # The comment does not contribute to the hash.
    # Placeholders are allowed to move around so their order should not change the ID.
    # TagPair's (HtmlTagPair) nesting should be preserved.  They can't be
    #   removed.  Placeholders inside tag pairs may be reordered.  However,
    #   you shouldn't introduce new placeholders or increase/decrease their count.
    #   TODO: pluralization is a different beast wrt placeholders.
    yield _escape_text_for_message_id(self.meaning or "")
    # TODO: Incorporate namespace/"project ID"?
    for i in self._gen_id_parts_for_subparts(self.parts):
      yield i

  def _compute_id(self):
    hasher = hashlib.md5()
    for part in self._gen_id_parts():
      hasher.update(part.encode("utf-8"))
    return hasher.hexdigest()

  def build(self):
    id = self._compute_id()
    placeholders_by_name = self.placeholder_registry.to_dict()
    return Message(id=id,
                   meaning=self.meaning,
                   comment=self.comment,
                   parts=self.parts,
                   placeholders_by_name=placeholders_by_name)


I18N_ATTRIB_PREFIX="i18n-"


class MessagePart(object):
  def get_fingerprint(self):
    raise NotImplementedError("Override in subclass")

  def unparse(self):
    raise NotImplementedError("Override in subclass")


# TODO: I've liberally used CLASS.__name__ all over the place for simplicity.
# However, this should be a FIXED unique name in all implementations.  There
# will be a fixed set of known placeholder and tag types regardless of
# implementation class names and that's the name we should use.  If a brand new
# type is added, we would give it a brand new unique name and update all the
# places where a type check is done: fingerprinting, escaping contexts, etc.
class Placeholder(MessagePart):
  def __init__(self, name, text, examples, comment):
    self.name = name
    self.text = text
    self.examples = examples
    self.comment = comment

  def __repr__(self):
    if self.name:
      return '%s[%s](%r)' % (self.name, self.__class__.__name__, self.text)
    else:
      return '%s(%r)' % (self.__class__.__name__, self.text)

  __str__ = __repr__


class TagPairBeginRef(Placeholder):
  def __init__(self, html_tag_pair, examples=None, comment=None):
    self.html_tag_pair = html_tag_pair
    name = None
    text = html_tag_pair.begin
    super(TagPairBeginRef, self).__init__(name, text, examples, comment)

class TagPairEndRef(Placeholder):
  def __init__(self, html_tag_pair, examples=None, comment=None):
    self.html_tag_pair = html_tag_pair
    name = None
    text = html_tag_pair.end
    super(TagPairEndRef, self).__init__(name, text, examples, comment)


class NgExpr(Placeholder):
  def __init__(self, name, text, examples, comment):
    super(NgExpr, self).__init__(name, text, examples, comment)

  def get_fingerprint(self):
    # TODO: do this right.
    return (type(self), self.text)

  def unparse(self):
    return "{{%s}}" % self.text


class TagPair(MessagePart):
  def __init__(self, tag, begin, end, parts, examples, canonical_key, ph_begin=None, ph_end=None):
    self.tag = tag
    self.begin = begin
    self.end = end
    self.parts = parts
    self.examples = examples
    self.canonical_key = canonical_key
    self.ph_begin = ph_begin if ph_begin else TagPairBeginRef(self)
    self.ph_end = ph_end if ph_end else TagPairEndRef(self)

  def unparse(self):
    raise NotImplementedError("Override in subclass")

  def __repr__(self):
    ph_begin_name, ph_end_name = self.ph_begin.name, self.ph_end.name
    if not ph_begin_name:
      ph_begin_name = self.tag.upper() + "_BEGIN_XX"
      ph_end_name = self.tag.upper() + "_END_XX"
    return '%s(%s…%s)%r%s' % (
        ph_begin_name,
        self.begin, self.end, self.parts,
        ph_end_name)


# TODO: must not de-dupe with other TagPair's even if they are an exact match
class HtmlTagPair(TagPair):
  def __init__(self, tag, begin, end, parts, examples, canonical_key):
    super(HtmlTagPair, self).__init__(tag, begin, end, parts, examples, canonical_key)
    self.ph_begin = TagPairBeginRef(self, examples=[self.begin],
                                    comment="Begin HTML <{0}> tag".format(self.tag))
    self.ph_end = TagPairEndRef(self, examples=[self.end],
                                comment="End HTML </{0}> tag".format(self.tag))

  # because the translator can change stuff in the middle.
  def get_fingerprint(self):
    return self.canonical_key
    # TODO: do this right.
    return (type(self), self.begin, self.end,
        tuple(map(get_fingerprint, self.parts)))

  def _unparse_parts(self, unparsed_parts):
    for part in self.parts:
      if isinstance(part, HtmlTagPair):
        part._unparse(unparsed_parts)
      else:
        unparsed_parts.append(cgi.escape(
          part if isinstance(part, str) else part.unparse()))

  def _unparse(self, unparsed_parts):
    unparsed_parts.append(self.begin)
    self._unparse_parts(unparsed_parts)
    unparsed_parts.append(self.end)

  def unparse(self):
    unparsed_parts = []
    self._unparse(unparsed_parts)
    return "".join(unparsed_parts)


def validate_valid_placeholder_name(ph_name):
  name = ph_name
  if not name:
    raise Error("invalid placeholder name: %r: empty name" % ph_name)
  if name.startswith("_") or name.endswith("_"):
    raise Error("invalid placeholder name: %r: can't begin or end with an underscore" % ph_name)
  # Ensure it's ascii?
  name = name.replace("_", "")
  if not name.isalnum() or name.upper() != name:
    raise Error("invalid placeholder name: %r: It may only be composed of capital letters, digits and underscores.")
  if name == "EMBEDDED_MESSAGES":
    raise Error("invalid placeholder name: %r: This name is reserved.")


ng_expr_ph_re = re.compile(r'i18n-ph\((.*)\)')
# text should not have the {{ }} around it.
def parse_ng_expression(text):
  text = text.strip()
  parts = text.rsplit("//", 1)
  comment = "Angular Expression"
  if len(parts) == 1:
    return NgExpr(name=None, text=text, examples=None, comment=comment)
  text = parts[0].strip()
  raw_comment = parts[-1].strip()
  m = ng_expr_ph_re.match(raw_comment)
  if not m:
    raise Error("Angular expression has a comment but it wasn't valid i18n-ph() syntax")
  ph_text = m.group(1).strip()
  parts = ph_text.split("|", 1)
  if len(parts):
    ph_name = parts[0].strip()
    example = parts[-1].strip()
  else:
    ph_name = ph_text
    example = None
  validate_valid_placeholder_name(ph_name)
  examples = None if not example else [example]
  return NgExpr(name=ph_name, text=text, examples=examples, comment=comment)


ng_expr_re = re.compile(r'\{\{\s*(.*?)\s*\}\}')
def parse_message_text_for_ng_expressions(text, placeholder_registry):
  parts = []
  splits = iter(ng_expr_re.split(text) + [""])
  for (txt, expr) in zip(splits, splits):
    if txt:
      parts.append(txt)
    expr = expr.strip()
    if expr:
      ng_expr = parse_ng_expression(expr)
      ng_expr = placeholder_registry.update_placeholder(ng_expr)
      parts.append(ng_expr)
  return parts


HtmlBeginEndTags = namedtuple("HtmlBeginEndTags", ("begin", "end"))


def _serialize_html_attr(name, value):
  if value is None:
    return name
  squote, dquote = "'", '"'
  have_squote, have_dquote = (squote in value), (dquote in value)
  quote_char = squote if (not have_squote and have_dquote) else dquote
  escaped_value = cgi.escape(value, (have_squote and have_dquote))
  return "{0}={2}{1}{2}".format(name, escaped_value, quote_char)


def _get_serialized_attrs(node):
  return " ".join(_serialize_html_attr(name, value)
                  for (name, value) in node.attrib.items())


def _get_html_begin_end_tags(node):
  serialized_attrs = _get_serialized_attrs(node)
  if serialized_attrs:
    serialized_attrs = " " + serialized_attrs
  begin = "<{0}{1}>".format(node.tag, serialized_attrs)
  end = "</{0}>".format(node.tag)
  return HtmlBeginEndTags(begin=begin, end=end)


def __parse_node(node, placeholder_registry):
  canonical_key = placeholder_registry.reserve_new_tag(node.tag)
  begin, end = _get_html_begin_end_tags(node)
  parts = []
  if node.text:
    parts.extend(parse_message_text_for_ng_expressions(node.text, placeholder_registry))
  for child in node:
    parts.append(__parse_node(child, placeholder_registry))
    if child.tail:
      parts.extend(parse_message_text_for_ng_expressions(child.tail, placeholder_registry))
  tag_pair = HtmlTagPair(tag=node.tag, begin=begin, end=end,
                         parts=parts, examples=None,
                         canonical_key=canonical_key)
  placeholder_registry.update_placeholder(tag_pair)
  return tag_pair


def parse_node_contents(root, placeholder_registry):
  parts = parse_message_text_for_ng_expressions(root.text, placeholder_registry)
  for child in root:
    parts.append(__parse_node(child, placeholder_registry))
    if child.tail:
      parts.extend(parse_message_text_for_ng_expressions(child.tail, placeholder_registry))
  return parts


def pretty_format_node_contents(node):
  parts = [node.text]
  for child in node:
    parts.append(pf(child))
  return " ".join(parts)


class MessageParser(object):
  __id = object()

  def __init__(self, on_parse, __private_constructor):
    if __private_constructor is not MessageParser.__id:
      raise Error("Private constructor")
    self.on_parse = on_parse
    self.nodes = deque()
    self.messages = OrderedDict()


  def _parse_i18n_attribs(self, node):
    # Do we have any i18n-FOO attributes?
    attribs = node.keys()
    i18n_attribs = [name for name in attribs if name.startswith(I18N_ATTRIB_PREFIX)]
    if not i18n_attribs:
      return
    for i18n_attrib in i18n_attribs:
      raw_comment = node.get(i18n_attrib)
      attr = i18n_attrib[len(I18N_ATTRIB_PREFIX):]
      raw_message = node.get(attr)
      message = MessageBuilder(raw_comment=raw_comment, raw_message=raw_message).build()
      # TODO(chirayu): what do you do when you have a message id conflict?
      self.messages[message.id] = message
      self.on_parse.on_attrib(message, node, attr)


  def _parse_messages_in_i18n_node(self, node):
    i18n = node.get("i18n")
    if i18n is None:
      return
    logger.debug("i18n=%r", i18n)
    message = MessageBuilder(raw_comment=i18n, raw_message=node).build()
    # message = MessageBuilder(raw_comment=i18n, raw_message=pretty_format_node_contents(node)).build()
    self.messages[message.id] = message
    self.on_parse.on_node(message, node)


  def _parse_messages(self, root):
    self.nodes.append(root)
    while self.nodes:
      node = self.nodes.popleft()
      self._parse_i18n_attribs(node)
      i18n = node.get("i18n")
      if i18n is not None:
        self._parse_messages_in_i18n_node(node)
        continue
      self.nodes.extend(node)

  @staticmethod
  def parse_messages(root, on_parse=None):
    if on_parse is None:
      on_parse = OnParseBase()
    parser = MessageParser(on_parse, MessageParser.__id)
    parser._parse_messages(root)
    return parser.messages

parse_messages = MessageParser.parse_messages


# What are the operations on messages?
#
# Display all placeholders?
# Show an example with placeholders replaced with examples?
# Get original text??
# Get original source reference?
#
# Compute message ID.
# Get placeholders by message ID?
# Format for presenters view?
# Format for developers view?
# Compare with another message?
#
# Builder pattern?
#
# Canonicalization of angular expressions.
