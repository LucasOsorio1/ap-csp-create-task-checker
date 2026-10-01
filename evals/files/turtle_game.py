import turtle

colors = ["red"]
t = turtle.Turtle()

def move_up():
    t.setheading(90)
    t.forward(20)
    t.color(colors[0])

screen = turtle.Screen()
screen.onkey(move_up, "Up")
screen.listen()
turtle.done()
