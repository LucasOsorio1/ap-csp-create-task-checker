line = input("names: ")
names = line.split(",")
def longest(items):
    best = ""
    for x in items:
        if len(x) > len(best):
            best = x
    return best
print(longest(names))
