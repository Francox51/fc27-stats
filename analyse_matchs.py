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

def main():
    club_rows = load_json_list(JOUEURS_CLUB_JSON)
    adv_rows = load_json_list(JOUEURS_ADV_JSON)

    club_par_match = grouper_par_match(club_rows)
    adv_par_match = grouper_par_match(adv_rows)

    tous_les_matchs = sorted(set(club_par_match.keys()) | set(adv_par_match.keys()))

    for mid in tous_les_matchs:
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


if __name__ == "__main__":
    main()
