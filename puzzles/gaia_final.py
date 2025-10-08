from .base import Puzzle

class GaiaFinalPuzzle(Puzzle):
    """
    Salle 4 — Réactivation Gaïa
    A=245, B=380, C=120 -> (A+B+C)/10 = 74.5 ~ jour 74 (14 mars 2025).
    On accepte "14/03/2025", "14 mars 2025", "14-03-2025", "74".
    """
    def __init__(self):
        self.codes = {"A":245, "B":380, "C":120}
        self.accept_days = {"74"}  # numéro du jour accepté
        self.accept_dates = {
            "14/03/2025", "14-03-2025", "14.03.2025", "14 03 2025",
            "14 MARS 2025", "14 MARS", "14 MARCH 2025"
        }
        self.hints = [
            "Additionnez les trois codes puis divisez par 10.",
            "Convertissez le numéro de jour 2025 en date.",
        ]
        self.debrief = (
            "Jour de dépassement : lorsque l’empreinte dépasse la biocapacité annuelle. "
            "Réduire les émissions et préserver la biodiversité repousse cette date."
        )

    def get_prompt(self):
        return {
            "type": "gaia_final",
            "title": "Salle 4 — Réactiver Gaïa",
            "instruction": (
                "Codes trouvés : A=245, B=380, C=120.<br>"
                "Calculez (A+B+C)/10 → numéro du jour 2025 → convertissez en date."
            ),
        }

    def validate(self, submission):
        ans = (submission.get("answer") or "").strip().upper()
        if not ans:
            return False
        # tolérer espaces
        ans_norm = " ".join(ans.replace("-", " ").replace(".", " ").split())
        # accepter le jour "74"
        if ans_norm.isdigit() and ans_norm in self.accept_days:
            return True
        # accepter formats de date
        if ans_norm in self.accept_dates:
            return True
        # formats types "14 03 2025"
        if ans_norm == "14 03 2025":
            return True
        return False

