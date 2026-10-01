var a = [4, 8];
function half(x) { if (x > 2) { return x / 2; } for (var i=0;i<a.length;i++){ x = x / a[i]; } return x; } // done
console.log(half(a[0]));
