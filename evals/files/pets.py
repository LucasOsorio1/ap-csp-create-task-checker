class Pet:
    def __init__(self, name, hunger):
        self.name = name
        self.hunger = hunger
pets = [Pet("Rex", 3), Pet("Tom", 5)]
for p in pets:
    if p.hunger > 4:
        print(p.name, "is hungry")
