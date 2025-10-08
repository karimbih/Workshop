from .base import Puzzle

class WasteInteractivePuzzle(Puzzle):
    """
    Salle 1 – Tri interactif : Verre / Compost / Plastique (jaune).
    Le client envoie: {"assign": {bac_id: objet_id}}  <-- IMPORTANT
    """
    def __init__(self):
        self.bins = [
            {"id": "verre",     "label": "Verre",             "img": "🍾"},
            {"id": "compost",   "label": "Compost",           "img": "🌱"},
            {"id": "plastique", "label": "Plastique (jaune)", "img": "♻️"},
        ]
        self.objects = [
            {"id": "pot-verre",           "label": "Pot en verre",            "img": "🍾"},
            {"id": "trognon-pomme",       "label": "Déchet alimentaire",      "img": "🍎"},
            {"id": "bouteille-plastique", "label": "Bouteille en plastique",  "img": "🥤"},
        ]
        # bac -> objet correct
        self.correct = {
            "verre":     "pot-verre",
            "compost":   "trognon-pomme",
            "plastique": "bouteille-plastique",
        }
        self.hints = [
            "Le verre se recycle à l’infini… dans le bac verre.",
            "Les déchets alimentaires vont au compost.",
            "Le plastique va dans la poubelle jaune.",
        ]
        self.debrief = (
            "Bravo ! Un bon tri réduit la pollution et augmente le recyclage. "
            "Le verre se recycle à l’infini, le compost réduit nos déchets."
        )

    def get_prompt(self):
        return {
            "type": "waste_v2",
            "title": "Salle 1 — Tri des déchets",
            "instruction": "Associe chaque objet au bon bac, puis clique « Valider ».",
            "bins": self.bins,
            "objects": self.objects,
        }

    def validate(self, submission):
        assign = submission.get("assign", {})
        if not isinstance(assign, dict):
            return False
        for b_id, obj_id in self.correct.items():
            if assign.get(b_id) != obj_id:
                return False
        return True

