from .base import Puzzle

class Energy180MWPuzzle(Puzzle):
    """
    Éolien=50, Solaire=40, Hydro=60 -> total 150.
    Il faut atteindre 180 MW avec gaz (curseur) MINIMUM.
    Réponse attendue : gaz = 30.
    """
    def __init__(self):
        self.fixed = {"eolien":50,"solaire":40,"hydro":60}
        self.target = 180
        self.debrief = (
            "Les réseaux électriques doivent équilibrer production et consommation. "
            "Plus de renouvelables => besoin de flexibilité (hydro, stockage, coopération)."
        )

    def get_prompt(self):
        return {"type":"energy180","title":"Salle 3 — Énergie 180 MW",
                "instruction":"Atteins exactement 180 MW avec le moins de fossile possible.",
                "fixed":self.fixed,"target":self.target}

    def validate(self, submission):
        gas = int(submission.get("gas", 0))
        total = self.fixed["eolien"] + self.fixed["solaire"] + self.fixed["hydro"] + gas
        return total == self.target and gas == 30

