var links = ["https://a.com", "http://b.org", "ftp://c.net"];
function countSecure(urls) {
  var n = 0;
  for (var i = 0; i < urls.length; i++) {
    if (/^https:\/\//.test(urls[i])) {
      n = n + 1;
    }
  }
  return n;
}
setText("out", countSecure(links));
