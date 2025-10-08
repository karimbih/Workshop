from .base import Puzzle

class WasteInteractivePuzzle(Puzzle):
    """
    Associer objets -> bacs :
      - verre: pot-verre
      - compost: dechet-alimentaire
      - plastique: bouteille-plastique
    """
    def __init__(self):
        self.items = [
            {"id":"pot-verre", "label":"Pot en verre", "emoji":"🍾"},
            {"id":"dechet-alimentaire", "label":"Déchet alimentaire", "emoji":"🍎"},
            {"id":"bouteille-plastique", "label":"Bouteille plastique", "emoji":"🥤"},
        ]
        self.bins = [
            {"id":"verre","label":"Verre","emoji":"🍾"},
            {"id":"compost","label":"Compost","emoji":"🌱"},
            {"id":"plastique","label":"Plastique (jaune)","emoji":"♻️"},
        ]
        self.correct = {
            "verre":"pot-verre",
            "compost":"dechet-alimentaire",
            "plastique":"bouteille-plastique",
        }
        self.debrief = (
            "Un bon tri réduit la pollution. Le verre est recyclable à l’infini, "
            "le compost réduit nos déchets."
        )

    def get_prompt(self):
        return {"type":"waste_v2","title":"Salle 1 — Tri des déchets",
                "instruction":"Associe chaque objet au bon bac, puis clique « Valider ».",
                "items":self.items,"bins":self.bins}

    def validate(self, submission):
        assign = submission.get("assign", {})
        return (
            assign.get("verre") == self.correct["verre"] and
            assign.get("compost") == self.correct["compost"] and
            assign.get("plastique") == self.correct["plastique"]
        )

