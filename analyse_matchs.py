import json
from collections import defaultdict
from pathlib import Path

JOUEURS_CLUB_JSON = Path("joueurs_matchs_fc27.json")
JOUEURS_ADV_JSON = Path("adversaires_joueurs_fc27.json")


def load_json_list(path: Path) -> list[dict]:
    if not path.exists():
        return []
    with path.open("r", encoding="utf-8") as f:
        data = json.load(f)
    return data if isinstance(data, list) else []

def resume_controle_match(players_rows: list[dict]) -> dict:
    goals = sum(p.get("goals", 0) or 0 for p in players_rows)
    shots = sum(p.get("shots", 0) or 0 for p in players_rows)
    passes_made = sum(p.get("passesMade", 0) or 0 for p in players_rows)
    pass_attempts = sum(p.get("passAttempts", 0) or 0 for p in players_rows)
    tackles_made = sum(p.get("tacklesMade", 0) or 0 for p in players_rows)
    tackle_attempts = sum(p.get("tackleAttempts", 0) or 0 for p in players_rows)

    return {
        "goals": goals,
        "shots": shots,
        "conversion_pct": round((goals / shots) * 100, 1) if shots > 0 else 0.0,
        "passes_made": passes_made,
        "pass_attempts": pass_attempts,
        "pass_accuracy_pct": round((passes_made / pass_attempts) * 100, 1) if pass_attempts > 0 else 0.0,
        "tackles_made": tackles_made,
        "tackle_success_pct": round((tackles_made / tackle_attempts) * 100, 1) if tackle_attempts > 0 else 0.0,
    }
def evaluer_match_equipe(stats: dict) -> dict:
    conv = stats["conversion_pct"]
    passes = stats["pass_accuracy_pct"]
    tacles = stats["tackles_made"]

    note_tir = min(4.0, round((conv / 35.0) * 4.0, 1)) if stats["shots"] > 0 else 0.0

    if stats["pass_attempts"] > 0:
        note_passes = max(0.0, min(3.0, round(((passes - 60.0) / 32.0) * 3.0, 1)))
    else:
        note_passes = 0.0

    note_tacles = min(3.0, round((tacles / 12.0) * 3.0, 1))
    note_totale = round(note_tir + note_passes + note_tacles, 1)

    if passes >= 82 and conv >= 15:
        tendance = "Contrôle et efficacité"
    elif passes >= 82 and conv < 15:
        tendance = "Contrôle stérile"
    elif passes < 75 and conv >= 20:
        tendance = "Réalisme en contre"
    elif tacles >= 9 and passes < 75:
        tendance = "Match subi / gros pressing"
    else:
        tendance = "Match équilibré / irrégulier"

    return {
        "note_10": note_totale,
        "detail_notes": {
            "tir_4": note_tir,
            "passes_3": note_passes,
            "tacles_3": note_tacles,
        },
        "tendance": tendance,
    }
def grouper_par_match(rows: list[dict]) -> dict[str, list[dict]]:
    grouped = defaultdict(list)
    for r in rows:
        mid = r.get("matchId")
        if mid is not None:
            grouped[str(mid)].append(r)
    return dict(grouped)

def _entier_fc27(val) -> int:
    try:
        if val is None or val == "":
            return 0
        return int(float(val))
    except (ValueError, TypeError):
        return 0


def evaluer_match_20_et_8_tendances(rows: list[dict]) -> dict:
    buts = 0
    tirs = 0
    passes_tent = 0
    passes_reuss = 0
    tacles_tent = 0
    tacles_reuss = 0
    nb_joueurs = 0

    for r in rows:
        if not isinstance(r, dict):
            continue
        role = str(r.get("position") or "").strip().lower()
        if role == "any":
            continue
        nb_joueurs += 1
        buts += _entier_fc27(r.get("goals"))
        tirs += _entier_fc27(r.get("shots"))
        passes_tent += _entier_fc27(r.get("passAttempts"))
        passes_reuss += _entier_fc27(r.get("passesMade"))
        tacles_tent += _entier_fc27(r.get("tackleAttempts"))
        tacles_reuss += _entier_fc27(r.get("tacklesMade"))

    taux_passes = (passes_reuss / passes_tent) if passes_tent > 0 else 0.0
    taux_tacles = (tacles_reuss / tacles_tent) if tacles_tent > 0 else 0.0
    ratio_buts_tirs = (buts / tirs) if tirs > 0 else 0.0

    note = 12.0
    note += ((tirs - 15.1) / 15.1) * 4.5
    note += (taux_passes - 0.805) * 25.0
    note += (taux_tacles - 0.347) * 15.0
    note += ((passes_tent - 196.1) / 196.1) * 1.2
    note += ((tacles_tent - 46.5) / 46.5) * 1.0
    note_20 = round(max(0.0, min(20.0, note)), 1)

    tendances = []
    if buts > 6.44 and tirs > 15.1 and passes_tent > 196.1 and tacles_tent > 46.5 and nb_joueurs >= 5:
        tendances.append("Très gros match collectif")
    if tirs > 15.1 and ratio_buts_tirs < 0.25:
        tendances.append("Domination sans finition")
    if taux_passes >= 0.82 and buts > 6.44:
        tendances.append("Construction propre et efficace")
    if tirs < 12.0 and buts < 4.0 and taux_tacles < 0.34:
        tendances.append("Match subi")
    if tirs < 12.0 and buts <= 3.0:
        tendances.append("Stérilité offensive")
    if passes_tent >= 180.0 and taux_passes < 0.78:
        tendances.append("Circulation brouillonne")
    if ratio_buts_tirs >= 0.45 and passes_tent <= 196.1 and tirs >= 8.0:
        tendances.append("Jeu direct tranchant")
    if passes_tent >= 196.1 and tacles_tent >= 46.5 and 0.32 <= taux_tacles <= 0.37:
        tendances.append("Match disputé")

    if not tendances:
        tendances.append("Profil équilibré / standard")

    return {"note_20": note_20, "tendances": tendances}


def construire_evaluations_matchs(
    tous_les_matchs: list[str],
    club_par_match: dict[str, list[dict]],
    adv_par_match: dict[str, list[dict]],
) -> dict[str, dict]:
    evaluations = {}
    for mid in tous_les_matchs:
        c_rows = club_par_match.get(mid, [])
        a_rows = adv_par_match.get(mid, [])
        entry = {
            "matchId": int(mid) if mid.isdigit() else mid,
            "club": evaluer_match_20_et_8_tendances(c_rows),
        }
        if a_rows:
            entry["adversaire"] = evaluer_match_20_et_8_tendances(a_rows)
        evaluations[mid] = entry
    return evaluations

def main():
    club_rows = load_json_list(JOUEURS_CLUB_JSON)
    adv_rows = load_json_list(JOUEURS_ADV_JSON)

    club_par_match = grouper_par_match(club_rows)
    adv_par_match = grouper_par_match(adv_rows)

    tous_les_matchs = sorted(set(club_par_match.keys()) | set(adv_par_match.keys()))

    for mid in tous_les_matchs[-3:]:
        c_rows = club_par_match.get(mid, [])
        a_rows = adv_par_match.get(mid, [])

        c_stats = resume_controle_match(c_rows)
        c_eval = evaluer_match_equipe(c_stats)

        print(f"=== Match {mid} ===")
        print(
            f"  Club : {c_stats['goals']} buts / {c_stats['shots']} tirs "
            f"(conv {c_stats['conversion_pct']}%) | "
            f"Passes {c_stats['passes_made']}/{c_stats['pass_attempts']} ({c_stats['pass_accuracy_pct']}%) | "
            f"Tacles réussis : {c_stats['tackles_made']}"
        )
        print(
            f"  Éval : {c_eval['note_10']}/10 "
            f"[Tir {c_eval['detail_notes']['tir_4']}/4, "
            f"Passes {c_eval['detail_notes']['passes_3']}/3, "
            f"Tacles {c_eval['detail_notes']['tacles_3']}/3] "
            f"-> {c_eval['tendance']}"
        )

        if a_rows:
            a_stats = resume_controle_match(a_rows)
            a_eval = evaluer_match_equipe(a_stats)
            print(
                f"  Adv  : {a_stats['goals']} buts / {a_stats['shots']} tirs "
                f"(conv {a_stats['conversion_pct']}%) | "
                f"Passes {a_stats['passes_made']}/{a_stats['pass_attempts']} ({a_stats['pass_accuracy_pct']}%) | "
                f"Tacles réussis : {a_stats['tackles_made']} "
                f"| Note : {a_eval['note_10']}/10 ({a_eval['tendance']})"
            )


    evaluations = construire_evaluations_matchs(tous_les_matchs, club_par_match, adv_par_match)
    Path("evaluation_matchs_fc27.json").write_text(
        json.dumps(evaluations, ensure_ascii=False, indent=2),
        encoding="utf-8",
    )


if __name__ == "__main__":
    main()
