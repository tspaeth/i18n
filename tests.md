- placeholder names
  - error if it's one of the reserved names or invalid.
- placeholder canonicalization
  - if same placeholder text is seen, use the already made
    up placeholder ID for it.
  - when a placeholder name is repeated, the
    canonicalization, (type, canonical_text), must match
    exactly.
  - placeholder examples should be merged
  - tagged placeholders should be serialized correctly
- warnings
  - warn on empty {{ }} syntax
  - warn on nested {{ syntax, e.g. {{ foo + "{{x}}" }},
    which should be legal but doesn't work in angularjs
- preserve whitespace behavior
  - whitespace in attributes should always be preserved
  - whitespace in html should be canonicalized away
    - the rewritten template should strip out the whitespace
      of the message itself and move it in the surrounding
      HTML.  (is that ever not possible?)
    - should the prefix and suffix whitespace be stored as
      part of the message?  if yes, how does it work with
      sub-messages?
      - caveat: if a directive wants to inspect the actual
        spacing of an expression, we should not attempt to
        destroy the spacing too much.  however, this is
        rendered a bit moot since bidi support will do much
        worse.
- style
  - warn if there is space before or after the | in
    i18n-ph(NAME|example).  warn if it ends with a space,
    begins with a space, etc.
