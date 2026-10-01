const scores = [88, 92, 75];
const curve = (list, bonus) => {
  return list.map(s => (s + bonus > 100 ? 100 : s + bonus));
};
const label = n => {
  if (n >= 90) { return "A"; }
  return "B";
};
class Team {
  constructor(names) { this.names = names; }
  roster(prefix) {
    for (const n of this.names) { if (n) { console.log(prefix + n); } }
  }
}
console.log(curve(scores, 5).map(label));
new Team(["Ana", "Ben"]).roster("#");
