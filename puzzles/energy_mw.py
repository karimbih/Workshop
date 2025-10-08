from .base import Puzzle

class EnergyMWPuzzle(Puzzle):
    """
    Salle 3 — Énergie 180 MW
    Fixes: Éolien 50, Solaire 40, Hydro 60. Slider: Gaz fossile (0..60).
    Objectif: total EXACT 180 et fossile minimal — on accepte 30 MW.
    """
    def __init__(self):
        self.fixed = {"eolien": 50, "solaire": 40, "hydro": 60}
        self.target = 180
        self.fossile = {"min": 0, "max": 60, "default": 30}
        self.hints = [
            "L’hydraulique est indispensable pour la stabilité du réseau.",
            "Éolien + solaire doivent couvrir au moins la moitié de la demande.",
            "Chaque MW de gaz fossile émet bien plus de CO₂ que les renouvelables."
        ]
        self.debrief = (
            "Les réseaux doivent équilibrer production et consommation en continu. "
            "Plus la part de renouvelable augmente, plus la flexibilité (barrages, stockage, coopération) est essentielle."
        )

    def get_prompt(self):
        return {
            "type": "energy_mw",
            "title": "Salle 3 — Énergie 180 MW",
            "instruction": "Atteins exactement 180 MW avec le moins de fossile possible.",
            "fixed": self.fixed,
            "target": self.target,
            "fossile": self.fossile,
        }

    def validate(self, submission):
        g = int(submission.get("fossile", -1))
        if g < self.fossile["min"] or g > self.fossile["max"]:
            return False
        total = self.fixed["eolien"] + self.fixed["solaire"] + self.fixed["hydro"] + g
        # solution attendue: 50 + 40 + 60 + 30 = 180
        return total == self.target and g == 30

