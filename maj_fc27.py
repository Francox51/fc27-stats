import csv
import hashlib
import json
from datetime import date, datetime, timezone
from zoneinfo import ZoneInfo
from pathlib import Path
from fc_clubs_api import FC27API

CLUB_NAME = "Azertyteam"
PLATFORM = "common-gen5"
TIMEZONE = "Europe/Paris"

CURRENT_SEASON = 2
MATCH_TYPES = ["leagueMatch", "playoffMatch"]

# Bornes de dates (YYYY-MM-DD) renseignées manuellement si besoin.
# Si une saison a des dates définies, elles permettent d'affecter la saison correspondante ;
# sinon on applique CURRENT_SEASON par défaut.
SEASONS_DATES = {
    1: {"start": None, "end": None},
    2: {"start": "2026-10-22", "end": "2026-12-03"},
}

MATCHS_JSON = Path("matchs_fc27.json")
JOUEURS_JSON = Path("joueurs_matchs_fc27.json")
ADVERSAIRES_JOUEURS_JSON = Path("adversaires_joueurs_fc27.json")

MATCHS_CSV = Path("matchs_fc27.csv")
JOUEURS_CSV = Path("joueurs_matchs_fc27.csv")
ADVERSAIRES_JOUEURS_CSV = Path("adversaires_joueurs_fc27.csv")


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


def parse_match_date(match: dict) -> date | None:
    ts = match.get("timestamp")
    if ts in (None, ""):
        return None
    tz = ZoneInfo(TIMEZONE)
    if isinstance(ts, (int, float)):
        # Gère les timestamps en secondes ou millisecondes
        sec = ts / 1000 if ts > 1e11 else ts
        return datetime.fromtimestamp(sec, tz=timezone.utc).astimezone(tz).date()
    if isinstance(ts, str):
        try:
            dt = datetime.fromisoformat(ts.replace("Z", "+00:00"))
            if dt.tzinfo is None:
                dt = dt.replace(tzinfo=timezone.utc)
            return dt.astimezone(tz).date()
        except ValueError:
            try:
                return date.fromisoformat(ts[:10])
            except ValueError:
                return None
    return None


def resolve_season(match: dict) -> int:
    match_date = parse_match_date(match)
    if match_date is not None:
        for season_num, bounds in SEASONS_DATES.items():
            start_str = bounds.get("start")
            end_str = bounds.get("end")
            if start_str and end_str:
                start_d = date.fromisoformat(start_str)
                end_d = date.fromisoformat(end_str)
                if start_d <= match_date <= end_d:
                    return int(season_num)
    return CURRENT_SEASON


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

    existing_matches = load_json_list(MATCHS_JSON)
    seen_matches = {match_key(m) for m in existing_matches}
    added_matches = 0

    existing_players = load_json_list(JOUEURS_JSON)
    seen_players = {player_row_key(p) for p in existing_players}
    added_players = 0

    existing_opp_players = load_json_list(ADVERSAIRES_JOUEURS_JSON)
    seen_opp_players = {player_row_key(p) for p in existing_opp_players}
    added_opp_players = 0

    club_id_str = str(club_id)
    match_season_map = {}

    for match_type in MATCH_TYPES:
        raw_matches = api.get_club_matches(club_id, match_type=match_type, count=10) or []
        print(f"[{match_type}] Matchs reçus de l'API : {len(raw_matches)}")

        for m in raw_matches:
            resolved_type = m.get("matchType") or match_type
            resolved_season = resolve_season(m)
            m["matchType"] = resolved_type
            m["season"] = resolved_season
            match_season_map[match_key(m)] = (resolved_type, resolved_season)

            mk = match_key(m)
            if mk not in seen_matches:
                existing_matches.append(m)
                seen_matches.add(mk)
                added_matches += 1

        raw_players = api.get_match_players(club_id, match_type=match_type, count=10, both_teams=True) or []
        print(f"[{match_type}] Lignes joueurs reçues (both_teams=True) : {len(raw_players)}")
        clubs_vus = {str(p.get("clubId")) for p in raw_players}
        print(f"[{match_type}] ClubIds présents : {clubs_vus}")

        for p in raw_players:
            p_key_match = match_key(p)
            m_type, m_season = match_season_map.get(p_key_match, (match_type, CURRENT_SEASON))
            p["matchType"] = p.get("matchType") or m_type
            p["season"] = m_season

            pk = player_row_key(p)
            if str(p.get("clubId")) == club_id_str:
                if pk not in seen_players:
                    existing_players.append(p)
                    seen_players.add(pk)
                    added_players += 1
            else:
                if pk not in seen_opp_players:
                    existing_opp_players.append(p)
                    seen_opp_players.add(pk)
                    added_opp_players += 1

    with open(MATCHS_JSON, "w", encoding="utf-8") as f:
        json.dump(existing_matches, f, indent=2, ensure_ascii=False, default=serialize_value)

    with open(JOUEURS_JSON, "w", encoding="utf-8") as f:
        json.dump(existing_players, f, indent=2, ensure_ascii=False, default=serialize_value)

    with open(ADVERSAIRES_JOUEURS_JSON, "w", encoding="utf-8") as f:
        json.dump(existing_opp_players, f, indent=2, ensure_ascii=False, default=serialize_value)

    save_csv(existing_matches, MATCHS_CSV)
    save_csv(existing_players, JOUEURS_CSV)
    save_csv(existing_opp_players, ADVERSAIRES_JOUEURS_CSV)

    print(f"Nouveaux matchs ajoutés : {added_matches} (total : {len(existing_matches)})")
    print(f"Nouvelles lignes joueurs club ajoutées : {added_players} (total : {len(existing_players)})")
    print(f"Nouvelles lignes joueurs adverses ajoutées : {added_opp_players} (total : {len(existing_opp_players)})")


if __name__ == "__main__":
    main()