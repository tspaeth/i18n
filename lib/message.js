"use strict";

var parseHtml = require('./parse_html').parseHtml;

var rawHtml = "<div a1='v1'>t1<span>s</span>t2</div>";


parseHtml(rawHtml).done(function(dom) {
  console.log(dom);
});
