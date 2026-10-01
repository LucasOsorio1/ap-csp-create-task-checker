var cities = getColumn("Daily Weather", "City");
var temps = getColumn("Daily Weather", "High Temperature");
var favorites = ["Miami"];

function filterByCity(city) {
  var matches = [];
  for (var i = 0; i < cities.length; i++) {
    if (cities[i] == city) {
      appendItem(matches, temps[i]);
    }
  }
  return matches;
}

onEvent("searchButton", "click", function() {
  var chosen = getText("cityInput");
  var results = filterByCity(chosen, favorites);
  setText("resultsLabel", "Highs: " + results.join(", "));
});

onEvent("favButton", "click", function() {
  setText("cityInput", favorites[0]);
});
