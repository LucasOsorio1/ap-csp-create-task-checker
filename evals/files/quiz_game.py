import random

questions = ["What is 7 x 8?", "Capital of Florida?", "How many sides does a hexagon have?",
             "What gas do plants take in?"]
answers = ["56", "tallahassee", "6", "carbon dioxide"]
scores = []

def grade_quiz(player_answers, answer_key):
    correct = 0
    for i in range(len(answer_key)):
        if player_answers[i].strip().lower() == answer_key[i]:
            correct = correct + 1
        else:
            print("Missed question " + str(i + 1))
    return correct

def ask_all():
    responses = []
    for q in questions:
        responses.append(input(q + " "))
    return responses

rounds = int(input("How many rounds? "))
for r in range(rounds):
    player = ask_all()
    result = grade_quiz(player, answers)
    scores.append(result)
    print("Round", r + 1, "score:", result, "/", len(questions))
print("Best score:", max(scores))
