var counts = {};
var words = getText("box").split(" ");
function tally(list) {
  for (var i = 0; i < list.length; i++) {
    if (counts[list[i]]) { counts[list[i]]++; } else { counts[list[i]] = 1; }
  }
}
tally(words);
setText("out", counts[words[0]]);
