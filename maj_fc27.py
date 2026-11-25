import csv
import hashlib
import json
from datetime import date, datetime
from pathlib import Path
from fc_clubs_api import FC27API

CLUB_NAME = "AZERTYTEAM"
PLATFORM = "common-gen5"
TIMEZONE = "Europe/Paris"
MATCH_TYPE = "leagueMatch"

MATCHS_JSON = Path("matchs_fc27.json")
JOUEURS_JSON = Path("joueurs_matchs_fc27.json")
MATCHS_CSV = Path("matchs_fc27.csv")
JOUEURS_CSV = Path("joueurs_matchs_fc27.csv")
BRUT_MATCHS_JSON = Path("brut_matchs.json")
BRUT_JOUEURS_JSON = Path("brut_joueurs.json")


def serialize_value(val):
    if isinstance(val, (datetime, date)):
        return val.isoformat()
    if isinstance(val, (dict, list)):
        return json.dumps(val, ensure_ascii=False, default=serialize_value)
    return str(val)


def load_json_list(path: Path) -> list:
    if not path.exists():
        return []
    with open(path, "r", encoding="utf-8") as f:
        data = json.load(f)
    return data if isinstance(data, list) else []


def match_key(match: dict) -> str:
    for k in ("matchId", "match_id", "id", "matchid"):
        if k in match and match[k] not in (None, ""):
            return str(match[k])
    raw = json.dumps(match, sort_keys=True, ensure_ascii=False, default=serialize_value)
    return hashlib.sha256(raw.encode("utf-8")).hexdigest()


def player_row_key(row: dict) -> str:
    raw = json.dumps(row, sort_keys=True, ensure_ascii=False, default=serialize_value)
    return hashlib.sha256(raw.encode("utf-8")).hexdigest()


def save_csv(rows: list, filename: Path):
    if not rows or not isinstance(rows[0], dict):
        return
    fieldnames = sorted({k for row in rows for k in row.keys()})
    cleaned_rows = [
        {k: serialize_value(v) if v is not None else "" for k, v in row.items()}
        for row in rows
    ]
    with open(filename, "w", newline="", encoding="utf-8-sig") as f:
        writer = csv.DictWriter(f, fieldnames=fieldnames, extrasaction="ignore")
        writer.writeheader()
        writer.writerows(cleaned_rows)


def main():
    api = FC27API(platform=PLATFORM, timezone=TIMEZONE)
    club_id = api.find_club_id(CLUB_NAME)

import csv
import hashlib
import json
from datetime import date, datetime
from pathlib import Path
from fc_clubs_api import FC27API

CLUB_NAME = "Azertyteam"
PLATFORM = "common-gen5"
TIMEZONE = "Europe/Paris"
MATCH_TYPE = "leagueMatch"

MATCHS_JSON = Path("matchs_fc27.json")
JOUEURS_JSON = Path("joueurs_matchs_fc27.json")
MATCHS_CSV = Path("matchs_fc27.csv")
JOUEURS_CSV = Path("joueurs_matchs_fc27.csv")


def serialize_value(val):
    if isinstance(val, (datetime, date)):
        return val.isoformat()
    if isinstance(val, (dict, list)):
        return json.dumps(val, ensure_ascii=False, default=serialize_value)
    return str(val)


def load_json_list(path: Path) -> list:
    if not path.exists():
        return []
    with open(path, "r", encoding="utf-8") as f:
        data = json.load(f)
    return data if isinstance(data, list) else []


def match_key(match: dict) -> str:
    for k in ("matchId", "match_id", "id", "matchid"):
        if k in match and match[k] not in (None, ""):
            return str(match[k])
    raw = json.dumps(match, sort_keys=True, ensure_ascii=False, default=serialize_value)
    return hashlib.sha256(raw.encode("utf-8")).hexdigest()


def player_row_key(row: dict) -> str:
    raw = json.dumps(row, sort_keys=True, ensure_ascii=False, default=serialize_value)
    return hashlib.sha256(raw.encode("utf-8")).hexdigest()


def save_csv(rows: list, filename: Path):
    if not rows or not isinstance(rows[0], dict):
        return
    fieldnames = sorted({k for row in rows for k in row.keys()})
    cleaned_rows = [
        {k: serialize_value(v) if v is not None else "" for k, v in row.items()}
        for row in rows
    ]
    with open(filename, "w", newline="", encoding="utf-8-sig") as f:
        writer = csv.DictWriter(f, fieldnames=fieldnames, extrasaction="ignore")
        writer.writeheader()
        writer.writerows(cleaned_rows)


def main():
    api = FC27API(platform=PLATFORM, timezone=TIMEZONE)
    club_id = api.find_club_id(CLUB_NAME)

    new_matches = api.get_club_matches(club_id, match_type=MATCH_TYPE, count=10) or []
    print("Matchs reçus de l'API :", len(new_matches))
    new_players = api.get_match_players(club_id, match_type=MATCH_TYPE, count=10, both_teams=True) or []
    print("Total lignes joueurs reçues (both_teams=True) :", len(new_players))
    clubs_vus = {str(p.get("clubId")) for p in new_players}
    print("ClubIds présents dans new_players :", clubs_vus)

    existing_matches = load_json_list(MATCHS_JSON)
    seen_matches = {match_key(m) for m in existing_matches}
    added_matches = 0

    for m in new_matches:
        mk = match_key(m)
        if mk not in seen_matches:
            existing_matches.append(m)
            seen_matches.add(mk)
            added_matches += 1

    existing_players = load_json_list(JOUEURS_JSON)
    seen_players = {player_row_key(p) for p in existing_players}
    added_players = 0

    for p in new_players:
        pk = player_row_key(p)
        if pk not in seen_players:
            existing_players.append(p)
            seen_players.add(pk)
            added_players += 1

    with open(MATCHS_JSON, "w", encoding="utf-8") as f:
        json.dump(existing_matches, f, indent=2, ensure_ascii=False, default=serialize_value)

    with open(JOUEURS_JSON, "w", encoding="utf-8") as f:
        json.dump(existing_players, f, indent=2, ensure_ascii=False, default=serialize_value)

    save_csv(existing_matches, MATCHS_CSV)
    save_csv(existing_players, JOUEURS_CSV)

    print(f"Nouveaux matchs ajoutés : {added_matches} (total : {len(existing_matches)})")
    print(f"Nouvelles lignes joueurs ajoutées : {added_players} (total : {len(existing_players)})")


if __name__ == "__main__":
    main()
