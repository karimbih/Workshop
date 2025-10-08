# services/game_state.py
# 4 énigmes finales : Tri, Devinette "Abeille", Énergie 180 MW, Réactivation Gaïa

import re
from typing import Dict, Any

# ---------- Salle 1 : Tri des déchets ----------
WASTE_OBJECTS = [
    {"id": "pot-verre", "label": "Pot en verre", "icon": "🍾"},
    {"id": "dechet-alim", "label": "Déchet alimentaire", "icon": "🍎"},
    {"id": "bouteille-plastique", "label": "Bouteille en plastique", "icon": "🥤"},
]
WASTE_BINS = [
    {"id": "verre", "label": "Verre", "icon": "🍾"},
    {"id": "compost", "label": "Compost", "icon": "🌱"},
    {"id": "plastique", "label": "Plastique (jaune)", "icon": "♻️"},
]
WASTE_CORRECT = {
    "pot-verre": "verre",
    "dechet-alim": "compost",
    "bouteille-plastique": "plastique",
}


def _waste_prompt() -> Dict[str, Any]:
    return {
        "type": "waste_v2",
        "title": "Salle 1 — Tri des déchets",
        "instruction": "Associe chaque objet au bon bac, puis clique « Valider ».",
        "objects": WASTE_OBJECTS,
        "bins": WASTE_BINS,
    }


def _waste_validate(payload: Dict[str, Any]) -> bool:
    # payload: { assign: {obj_id: bin_id, ...} }
    assign = payload.get("assign") or {}
    if set(assign.keys()) != set(WASTE_CORRECT.keys()):
        return False
    for obj_id, bin_id in assign.items():
        if WASTE_CORRECT.get(obj_id) != bin_id:
            return False
    return True


# ---------- Salle 2 : Devinette Abeille ----------
def _riddle_prompt() -> Dict[str, Any]:
    return {
        "type": "riddle_v2",
        "title": "Salle 2 — Devinette biodiversité",
        "instruction": (
            "Mon premier est la première lettre de l’alphabet.\n"
            "Mon deuxième est le cri du veau.\n"
            "Mon troisième se prononce comme une petite île en vieux français.\n"
            "Mon tout est un insecte pollinisateur essentiel à la vie sur Terre."
        ),
    }


def _riddle_validate(payload: Dict[str, Any]) -> bool:
    ans = (payload.get("answer") or "").strip().lower()
    ans = ans.replace("é", "e").replace("è", "e").replace("ê", "e")
    return ans in ("abeille",)


# ---------- Salle 3 : Énergie 180 MW ----------
ENERGY_CONSTANTS = {"eolien": 50, "solaire": 40, "hydro": 60}
ENERGY_TARGET = 180
ENERGY_MIN_FOSSIL = 30  # solution optimale : 30 MW fossile


def _energy_prompt() -> Dict[str, Any]:
    return {
        "type": "energy_180",
        "title": "Salle 3 — Énergie 180 MW",
        "instruction": "Atteins exactement 180 MW avec le moins de fossile possible.",
        "eolien": ENERGY_CONSTANTS["eolien"],
        "solaire": ENERGY_CONSTANTS["solaire"],
        "hydro": ENERGY_CONSTANTS["hydro"],
        "min": 0,
        "max": 60,
        "step": 1,
    }


def _energy_validate(payload: Dict[str, Any]) -> bool:
    # payload: { fossil: number }
    fossil = int(payload.get("fossil") or 0)
    total = ENERGY_CONSTANTS["eolien"] + ENERGY_CONSTANTS["solaire"] + ENERGY_CONSTANTS["hydro"] + fossil
    # on exige vraiment le minimum (30) pour "minimiser le fossile"
    return total == ENERGY_TARGET and fossil == ENERGY_MIN_FOSSIL


# ---------- Salle 4 : Réactivation Gaïa ----------
def _gaia_prompt() -> Dict[str, Any]:
    return {
        "type": "gaia_v2",
        "title": "Salle 4 — Réactiver Gaïa",
        "instruction": (
            "Codes trouvés : A=245, B=380, C=120.\n"
            "Calculez (A+B+C)/10 → numéro du jour 2025 → convertissez en date."
        ),
    }


def _normalize_date(s: str) -> str:
    s = s.strip().lower()
    s = s.replace("é", "e").replace("è", "e").replace("ê", "e")
    s = re.sub(r"\s+", " ", s)
    return s


def _gaia_validate(payload: Dict[str, Any]) -> bool:
    # Résultat attendu: 14 mars 2025 (jour 74)
    val = _normalize_date(payload.get("date") or "")
    # on accepte quelques variantes usuelles
    return (
        "14" in val
        and ("mars" in val or "mar" in val)
        and "2025" in val
    )


# ---------- API attendue par app.py ----------
PUZZLES = [
    {"prompt": _waste_prompt, "validate": _waste_validate, "hints": [
        "Le verre va dans le bac verre.",
        "Les déchets de cuisine vont au compost.",
        "Les bouteilles en plastique vont dans le bac jaune."
    ], "debrief": "Un bon tri réduit la pollution et augmente le recyclage."},
    {"prompt": _riddle_prompt, "validate": _riddle_validate, "hints": [
        "C’est un insecte.",
        "Il produit du miel.",
        "Il pollinise beaucoup de plantes."
    ], "debrief": "Sans les abeilles, ~80% des plantes à fleurs dépendent de la pollinisation."},
    {"prompt": _energy_prompt, "validate": _energy_validate, "hints": [
        "Le renouvelable totalise 150 MW.",
        "Complète avec juste ce qu’il faut en fossile.",
        "Le minimum de fossile est la bonne réponse."
    ], "debrief": "Les réseaux doivent équilibrer production/consommation en continu ; la flexibilité est essentielle."},
    {"prompt": _gaia_prompt, "validate": _gaia_validate, "hints": [
        "Additionnez A+B+C, puis divisez par 10.",
        "Convertissez le n° de jour 2025 en date.",
        "Mars est un bon mois à considérer…"
    ], "debrief": "Le « jour de dépassement » illustre la pression humaine sur la biocapacité de la Terre."},
]


def total_stages() -> int:
    return len(PUZZLES)


def get_stage_prompt(i: int) -> Dict[str, Any]:
    return PUZZLES[i]["prompt"]()


def validate_stage(i: int, submission: Dict[str, Any]) -> bool:
    return PUZZLES[i]["validate"](submission)


def get_hint(index: int, used: int):
    hints = PUZZLES[index].get("hints", []) or []
    return hints[used] if used < len(hints) else None


def get_debrief(index: int):
    return PUZZLES[index].get("debrief")

