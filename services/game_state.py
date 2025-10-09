# services/game_state.py
from __future__ import annotations
from typing import Any, Dict, List

# ---- Codes des 3 premières salles (annoncés au chat quand la salle est validée)
CODES: List[int] = [2390, 2400, 2431]

# ---- Durée par salle (secondes)
STAGE_DURATIONS = {0: 180, 1: 120, 2: 180, 3: 180}

# =========================
# Salle 1 — Tri des déchets
# =========================
S1_ITEMS = [
    {"id": "bouteille-plastique", "name": "Bouteille en plastique", "icon": "🥤", "correct_bin": "plastique"},
    {"id": "pot-verre", "name": "Pot en verre", "icon": "🍾", "correct_bin": "verre"},
    {"id": "epluchure", "name": "Déchet alimentaire", "icon": "🍎", "correct_bin": "compost"},
]
S1_BINS = [
    {"id": "verre", "name": "Verre", "icon": "🍾", "color": "#10b981"},
    {"id": "compost", "name": "Compost", "icon": "🌱", "color": "#92400e"},
    {"id": "plastique", "name": "Plastique (jaune)", "icon": "♻️", "color": "#fbbf24"},
]

def s1_prompt() -> Dict[str, Any]:
    return {
        "type": "waste_v2",
        "title": "Salle 1 — Tri des déchets",
        "instruction": "Associe chaque objet au bon bac, puis clique « Valider ».",
        "objects": S1_ITEMS,
        "bins": S1_BINS,
    }

def s1_validate(payload: Dict[str, Any]) -> bool:
    mapping = payload.get("assign", {})
    if not isinstance(mapping, dict):
        return False
    # mapping attend {bin_id: item_id}
    expect = {
        "verre": "pot-verre",
        "compost": "epluchure",
        "plastique": "bouteille-plastique",
    }
    return all(mapping.get(k) == v for k, v in expect.items())

# ==========================================
# Salle 2 — Devinette biodiversité: ABEILLE
# ==========================================
S2_RIDDLE = (
    "Mon premier est la première lettre de l’alphabet.<br>"
    "Mon deuxième est le cri du veau.<br>"
    "Mon troisième se prononce comme une petite île en vieux français.<br>"
    "Mon tout est un insecte pollinisateur essentiel à la vie sur Terre."
)

def s2_prompt() -> Dict[str, Any]:
    return {
        "type": "riddle",
        "title": "Salle 2 — Devinette biodiversité",
        "instruction": S2_RIDDLE + "<br><br>🕒 2 minutes. Entrez votre réponse.",
    }

def s2_validate(payload: Dict[str, Any]) -> bool:
    ans = (payload.get("answer") or "").strip().lower()
    return ans in {"abeille", "l'abeille", "une abeille"}

# ==========================================
# Salle 3 — Énergie 180 MW (minimiser fossile)
# ==========================================
# Solution cible : Eolien=50, Solaire=40, Hydro=60, Fossile=30  → Total 180
def s3_prompt() -> Dict[str, Any]:
    return {
        "type": "energy_v2",
        "title": "Salle 3 — L’énergie renouvelable",
        "instruction": (
            "Alimentez la ville à <strong>180 MW</strong> en minimisant le fossile.<br>"
            "Sources disponibles : Éolien (max 50), Solaire (max 40), Hydraulique (max 60) + Fossile.<br>"
            "Validez lorsque le total vaut 180."
        ),
        "min": 0,
        "maxE": 50,
        "maxS": 40,
        "maxH": 60,
        "maxF": 60,
        "start": {"eolien": 0, "solaire": 0, "hydro": 0, "fossile": 0},
    }

def s3_validate(payload: Dict[str, Any]) -> bool:
    mix = payload.get("mix", {})
    try:
        e = int(mix.get("eolien", 0))
        s = int(mix.get("solaire", 0))
        h = int(mix.get("hydro", 0))
        f = int(mix.get("fossile", 0))
    except Exception:
        return False

    if any(v < 0 for v in (e, s, h, f)):
        return False
    if e > 50 or s > 40 or h > 60 or f > 60:
        return False
    if (e + s + h + f) != 180:
        return False
    # On accepte la solution optimale (fossile=30) ou toute solution à 180 avec fossile ≤ 30
    return f <= 30

# =======================================================
# Salle 4 — Réactiver Gaïa (nouvelle règle JJMM à calculer)
# =======================================================
def s4_prompt() -> Dict[str, Any]:
    return {
        "type": "gaia",
        "title": "Salle 4 — Réactiver Gaïa",
        "instruction": (
            "Vous avez obtenu 3 codes aux salles précédentes (Code 1, Code 2, Code 3).<br>"
            "Calculez <strong>(Code1 + Code2 + Code3) / 3</strong> = un nombre à 4 chiffres.<br>"
            "Interprétez ce nombre comme <strong>JJMM</strong> de l’année 2025 → saisissez la date."
        ),
    }

def s4_validate(payload: Dict[str, Any]) -> bool:
    # (2390+2400+2431)/3 = 2407 → 24/07/2025
    ans = (payload.get("date") or "").strip().lower()
    valid_texts = {
        "24 juillet 2025",
        "24/07/2025", "24-07-2025", "2025-07-24",
        "24 july 2025", "july 24 2025", "24 jul 2025", "jul 24 2025",
    }
    return ans in valid_texts

# ========================
# Routage des 4 salles
# ========================
PUZZLES = [
    {"prompt": s1_prompt, "validate": s1_validate, "hints": [
        "Le verre va dans le bac verre.",
        "Le déchet alimentaire va au compost.",
        "La bouteille en plastique va dans la poubelle jaune."
    ], "debrief": "Bien trier permet de réduire les déchets et d’augmenter le recyclage."},
    {"prompt": s2_prompt, "validate": s2_validate, "hints": [
        "Premier = lettre A.",
        "Cri du veau → beu (sonorité « be »).",
        "Petite île en ancien français → « île » / « île » se prononce comme « ille ».",
    ], "debrief": "Les abeilles sont essentielles : elles pollinisent une grande partie des plantes cultivées."},
    {"prompt": s3_prompt, "validate": s3_validate, "hints": [
        "L’hydraulique est indispensable à la stabilité.",
        "Éolien + solaire doivent bien contribuer.",
        "Le fossile doit rester minimal tout en atteignant 180 MW."
    ], "debrief": "Un mix équilibré limite les émissions et maintient l’équilibre production/consommation."},
    {"prompt": s4_prompt, "validate": s4_validate, "hints": [
        "Additionnez les 3 codes puis divisez par 3.",
        "Interprétez le résultat comme JJMM (jour/mois).",
    ], "debrief": "Le « jour de dépassement » illustre l’empreinte écologique globale."},
]

def total_stages() -> int:
    return len(PUZZLES)

def get_stage_prompt(i: int) -> Dict[str, Any]:
    return PUZZLES[i]["prompt"]()

def validate_stage(i: int, submission: Dict[str, Any]) -> bool:
    return PUZZLES[i]["validate"](submission)

def get_hint(index: int, used: int):
    hints = PUZZLES[index].get("hints") or []
    return hints[used] if used < len(hints) else None

def get_debrief(index: int) -> str | None:
    return PUZZLES[index].get("debrief")

def stage_duration_for(i: int) -> int:
    return STAGE_DURATIONS.get(i, 180)

