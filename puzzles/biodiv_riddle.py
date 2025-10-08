import unicodedata
from .base import Puzzle

def _norm(s: str) -> str:
    s = ''.join(c for c in unicodedata.normalize('NFKD', s or '') if not unicodedata.combining(c))
    return s.strip().upper()

class BiodivRiddlePuzzle(Puzzle):
    def __init__(self):
        self.expected = "ABEILLE"
        self.hints = [
            "Mon premier est la première lettre de l’alphabet…",
            "Mon deuxième est le cri du veau (béé)…",
            "Mon troisième se prononce comme une petite île en vieux français (île)…"
        ]
        self.debrief = "Bravo ! Sans les abeilles, ~80% des plantes à fleurs ne survivraient pas."

    def get_prompt(self):
        riddle = (
            "Mon premier est la première lettre de l’alphabet.\n"
            "Mon deuxième est le cri du veau.\n"
            "Mon troisième se prononce comme une petite île en vieux français.\n"
            "Mon tout est un insecte pollinisateur essentiel à la vie sur Terre.\n\n"
            "🕒 Vous avez 2 minutes pour répondre."
        )
        return {
            "type": "riddle",
            "title": "Salle 2 — Biodiversité (devinette)",
            "instruction": riddle,
        }

    def validate(self, submission):
        ans = _norm(submission.get("answer", ""))
        return ans == self.expected
