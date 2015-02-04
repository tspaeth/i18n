/**
 * Message Types Reference
 *
 * Actual types will be in AtScript.  However, this is the official type specification.
 */

type MessagePart = string|Placeholder|TagPair;

interface GetStableTypeName {
  (): string;
}

interface ToLongFingerprint {
  (): string;
}

interface MessagePartBase {
  // such as "NgExpr", "HtmlTagPair", etc.
  getStableTypeName: GetStableTypeName;
  toLongFingerprint: ToLongFingerprint;
}


class TextPart implements MessagePartBase {
  value: string;

  constructor(value: string) {
    this.value = value;
  }

  // degenerate case.
  toLongFingerprint(): string {
    return this.value;
  }

  getStableTypeName(): string {
    return "TextPart";
  }
}


interface Placeholder extends MessagePartBase {
  name: string;
  text: string;
  examples?: string[];
  comment?: string;
}

// TagPairs, when serialized, will use a pair of placeholders to represent
// their begin and end.  TagPairBeginRef and TagPairEndRef represent those placeholders.
class TagPairBeginRef implements Placeholder {
  name: string;
  text: string;
  examples?: string[];
  comment?: string;

  // TODO
  constructor(value: string) {
    this.value = value;
  }

  // degenerate case.
  toLongFingerprint(): string {
    return this.text;
  }

  getStableTypeName(): string {
    return "TagPairBegin";
  }
}

class TagPairEndRef implements Placeholder {
  name: string;
  text: string;
  examples?: string[];
  comment?: string;

  // TODO
  constructor(value: string) {
    this.value = value;
  }

  // degenerate case.
  toLongFingerprint(): string {
    return this.text;
  }

  getStableTypeName(): string {
    return "TagPairEnd";
  }
}



interface TagPair extends MessagePartBase {
  // tag name: e.g. "span" for the HTML <span> tag.
  tag: string;
  // original full begin tag with all attributes, etc. as is.
  begin: string;
  // original full end tag.
  end: string;
  parts?: MessagePart[];
  examples?: string[];
  tagFingerprintLong: string;  // canonical_key
  beginPlaceholderRef: TagPairRef; // ph_begin
  endPlaceholderRef: TagPairRef; // ph_end
}


class HtmlTagPair implements TagPair {
  value: string;

  constructor(value: string) {
    this.value = value;
  }

  // degenerate case.
  toLongFingerprint(): string {
    return this.value;
  }

  getStableTypeName(): string {
    return "TextPart";
  }
}


interface Message {
  id: string;
  meaning?: string;
  parts: MessagePart[]
}
