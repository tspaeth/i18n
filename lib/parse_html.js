"use strict";

var htmlparser = require("htmlparser2");
var Q = require("q");

var parseHtml = Q.nfbind(function newParser(html, handler) {
  var parser = new htmlparser.Parser(new htmlparser.DomHandler(handler));
  parser.write(html);
  parser.done();
});

exports.parseHtml = parseHtml;
