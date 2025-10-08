from .base import Puzzle

class RiddleBeePuzzle(Puzzle):
    """
    Salle 2 — Devinette (ABEILLE)
    Mauvaise réponse : pénalité gérée dans app.py (-30s).
    """
    def __init__(self):
        self.answer = "ABEILLE"
        self.hints = [
            "Mon premier est la première lettre de l’alphabet.",
            "Mon deuxième est le cri du veau.",
            "Mon troisième se prononce comme une petite île en vieux français.",
        ]
        self.debrief = "Bravo ! Sans les abeilles, ~80% des plantes à fleurs dépendent de la pollinisation."

    def get_prompt(self):
        return {
            "type": "riddle",
            "title": "Salle 2 — Devinette Biodiversité",
            "instruction": (
                "Mon premier est la première lettre de l’alphabet.<br>"
                "Mon deuxième est le cri du veau.<br>"
                "Mon troisième se prononce comme une petite île en vieux français.<br>"
                "Mon tout est un insecte pollinisateur essentiel à la vie sur Terre."
            ),
        }

    def validate(self, submission):
        ans = (submission.get("answer") or "").strip().upper()
        return ans == self.answer

