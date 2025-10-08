from .base import Puzzle

class BiodivRiddlePuzzle(Puzzle):
    def __init__(self):
        self.answer = "ABEILLE"
        self.debrief = "Bravo ! Sans les abeilles, ~80% des plantes à fleurs dépendent de la pollinisation."

    def get_prompt(self):
        text = (
            "Mon premier est la première lettre de l’alphabet.\n"
            "Mon deuxième est le cri du veau.\n"
            "Mon troisième se prononce comme une petite île en vieux français.\n"
            "Mon tout est un insecte pollinisateur essentiel à la vie sur Terre."
        )
        return {"type":"riddle","title":"Salle 2 — Devinette Biodiversité",
                "instruction":text}

    def validate(self, submission):
        ans = (submission.get("answer","") or "").strip().upper()
        return ans == self.answer

