from .base import Puzzle

class GaiaFinalPuzzle(Puzzle):
    """
    Codes A=245, B=380, C=120 => (A+B+C)/10 = 74.5 -> jour 74 de 2025 => 14 mars 2025
    On accepte plusieurs écritures simples : "14 mars 2025", "14/03/2025", "14-03-2025", "14 march 2025".
    """
    def __init__(self):
        self.A, self.B, self.C = 245, 380, 120
        self.debrief = "Jour de dépassement 2025 calculé à partir des codes. Protéger les écosystèmes est vital."

    def get_prompt(self):
        return {"type":"gaia","title":"Salle 4 — Réactiver Gaïa",
                "instruction":"Codes trouvés : A=245, B=380, C=120.\n"
                              "Calculez (A+B+C)/10 → numéro du jour 2025 → convertissez en date."}

    def validate(self, submission):
        ans = (submission.get("answer","") or "").strip().lower()
        accept = {"14 mars 2025","14/03/2025","14-03-2025","14 march 2025"}
        return ans in accept

