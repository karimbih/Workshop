from typing import Dict, Any, List

# ---- Salle 1 : Tri des déchets ----
ITEMS = [
    {"id":"bouteille-plastique","name":"Bouteille en plastique","icon":"🥤","correct_bin":"plastique"},
    {"id":"pot-verre","name":"Pot en verre","icon":"🍾","correct_bin":"verre"},
    {"id":"dechet-alimentaire","name":"Déchet alimentaire","icon":"🍎","correct_bin":"compost"},
]
BINS = [
    {"id":"verre","name":"Verre","color":"#10b981","icon":"🍾"},
    {"id":"compost","name":"Compost","color":"#92400e","icon":"🌱"},
    {"id":"plastique","name":"Plastique (jaune)","color":"#fbbf24","icon":"♻️"},
]

def s1_prompt() -> Dict[str, Any]:
    return {
        "type":"tri",
        "title":"Salle 1 — Tri des déchets",
        "instruction":"Associe chaque objet au bon bac, puis clique « Valider ».",
        "items": ITEMS,
        "bins": BINS
    }

def s1_validate(payload: Dict[str, Any]) -> bool:
    assign = payload.get("assign") or {}
    # assign attendu: {bin_id: item_id}
    expected = {
        "verre": "pot-verre",
        "compost": "dechet-alimentaire",
        "plastique": "bouteille-plastique",
    }
    return assign == expected

# ---- Salle 2 : Devinette Abeille ----
def s2_prompt() -> Dict[str, Any]:
    return {
        "type":"riddle",
        "title":"Salle 2 — Biodiversité (Devinette)",
        "instruction":(
            "Mon premier est la première lettre de l’alphabet.<br>"
            "Mon deuxième est le cri du veau.<br>"
            "Mon troisième se prononce comme une petite île en vieux français.<br>"
            "Mon tout est un insecte pollinisateur essentiel à la vie sur Terre."
        )
    }

def s2_validate(payload: Dict[str, Any]) -> bool:
    ans = (payload.get("answer") or "").strip().lower()
    return ans in {"abeille"}

# ---- Salle 3 : Énergie 180 MW ----
def s3_prompt() -> Dict[str, Any]:
    return {
        "type":"energy",
        "title":"Salle 3 — Énergie renouvelable",
        "instruction":(
            "Objectif : Atteindre exactement 180 MW avec le moins de gaz fossile possible.<br>"
            "Éolien, Solaire, Hydraulique, Gaz fossile."
        ),
        "min": 0, "max": 180
    }

def s3_validate(payload: Dict[str, Any]) -> bool:
    mix = payload.get("mix") or {}
    e = int(mix.get("eolien", 0))
    s = int(mix.get("solaire", 0))
    h = int(mix.get("hydro", 0))
    g = int(mix.get("gaz", 0))
    total = e + s + h + g
    # Solution pédagogique : total 180, gaz <= 30
    return total == 180 and g <= 30

# ---- Salle 4 : Réactiver Gaïa (calcul de date) ----
def s4_prompt() -> Dict[str, Any]:
    return {
        "type":"gaia",
        "title":"Salle 4 — Réactiver Gaïa",
        "instruction":(
            "Codes trouvés : A=245, B=380, C=120.<br>"
            "Calculez (A+B+C)/10 → numéro du jour 2025 → convertissez en date."
        )
    }

def s4_validate(payload: Dict[str, Any]) -> bool:
    # Jour 74 de 2025 => 14 mars 2025
    ans = (payload.get("date") or "").strip().lower()
    valid_texts = {
        "14 mars 2025", "14/03/2025", "14-03-2025", "2025-03-14", "14 march 2025", "march 14 2025"
    }
    return ans in valid_texts

# ---- Registre des salles ----
PUZZLES = [
    {"prompt": s1_prompt, "validate": s1_validate, "score": 2390},
    {"prompt": s2_prompt, "validate": s2_validate, "score": 2400},
    {"prompt": s3_prompt, "validate": s3_validate, "score": 2431},
    {"prompt": s4_prompt, "validate": s4_validate, "score": 2500},
]

def total_stages() -> int: return len(PUZZLES)
def get_stage_prompt(i: int) -> Dict[str, Any]: return PUZZLES[i]["prompt"]()
def validate_stage(i: int, payload: Dict[str, Any]) -> bool: return PUZZLES[i]["validate"](payload)
def stage_score(i: int) -> int: return PUZZLES[i]["score"]
