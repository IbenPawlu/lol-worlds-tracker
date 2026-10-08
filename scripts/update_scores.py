#!/usr/bin/env python3
import json
import os
import sys
import urllib.parse
import urllib.request
from datetime import datetime, timezone

API = "https://api.pandascore.co"
TOKEN = os.environ.get("PANDASCORE_TOKEN", "").strip()
SERIES_ID = os.environ.get("PANDASCORE_SERIES_ID", "").strip()

if not TOKEN:
    print("PANDASCORE_TOKEN is missing.", file=sys.stderr)
    sys.exit(2)

def api_get(path, params=None):
    params = dict(params or {})
    params["token"] = TOKEN
    url = API + path + "?" + urllib.parse.urlencode(params, doseq=True)
    req = urllib.request.Request(url, headers={"Accept": "application/json", "User-Agent": "kamra-worlds-tracker/1.0"})
    with urllib.request.urlopen(req, timeout=30) as response:
        return json.load(response)

def text(v):
    return str(v or "").lower()

def looks_like_worlds_2026(s):
    blob = " ".join([
        text(s.get("name")),
        text(s.get("full_name")),
        text(s.get("slug")),
        text((s.get("league") or {}).get("name")),
        text((s.get("league") or {}).get("slug")),
    ])
    year = s.get("year")
    year_ok = str(year) == "2026" or "2026" in blob or text(s.get("begin_at")).startswith("2026")
    worlds_ok = "world" in blob
    return year_ok and worlds_ok

def discover_series():
    # Latest series first; usually enough to find the current Worlds series.
    series = api_get("/lol/series", {"per_page": 100, "sort": "-begin_at"})
    candidates = [s for s in series if looks_like_worlds_2026(s)]

    if not candidates:
        # Fallback search.
        searched = api_get("/lol/series", {"per_page": 100, "search[name]": "World"})
        candidates = [s for s in searched if looks_like_worlds_2026(s)]

    if not candidates:
        raise RuntimeError(
            "Could not auto-detect the 2026 Worlds series. "
            "Set the GitHub repository variable PANDASCORE_SERIES_ID to the PandaScore series ID."
        )

    # Prefer an active series; otherwise newest begin_at.
    now = datetime.now(timezone.utc)
    def score(s):
        begin = s.get("begin_at") or ""
        end = s.get("end_at") or ""
        active = bool(begin and end and begin <= now.isoformat() <= end)
        return (1 if active else 0, begin)

    candidates.sort(key=score, reverse=True)
    return candidates[0]

def normalize_opponent(raw):
    opp = raw.get("opponent") if isinstance(raw, dict) and isinstance(raw.get("opponent"), dict) else raw
    if not isinstance(opp, dict):
        return None
    return {
        "id": opp.get("id"),
        "name": opp.get("name"),
        "acronym": opp.get("acronym"),
        "slug": opp.get("slug"),
    }

def normalize_match(m):
    results = {}
    for r in m.get("results") or []:
        team_id = r.get("team_id")
        if team_id is not None:
            try:
                results[str(team_id)] = int(r.get("score", 0))
            except Exception:
                results[str(team_id)] = 0

    opponents = []
    for raw in m.get("opponents") or []:
        opp = normalize_opponent(raw)
        if not opp:
            continue
        opp["score"] = results.get(str(opp.get("id")))
        opponents.append(opp)

    return {
        "id": m.get("id"),
        "slug": m.get("slug"),
        "name": m.get("name"),
        "status": m.get("status"),
        "begin_at": m.get("begin_at"),
        "end_at": m.get("end_at"),
        "winner_id": m.get("winner_id"),
        "number_of_games": m.get("number_of_games"),
        "league": {
            "id": (m.get("league") or {}).get("id"),
            "name": (m.get("league") or {}).get("name"),
            "slug": (m.get("league") or {}).get("slug"),
        },
        "serie": {
            "id": (m.get("serie") or {}).get("id"),
            "name": (m.get("serie") or {}).get("name"),
            "full_name": (m.get("serie") or {}).get("full_name"),
            "year": (m.get("serie") or {}).get("year"),
        },
        "tournament": {
            "id": (m.get("tournament") or {}).get("id"),
            "name": (m.get("tournament") or {}).get("name"),
            "slug": (m.get("tournament") or {}).get("slug"),
        },
        "opponents": opponents,
    }

def main():
    if SERIES_ID:
        series = {"id": int(SERIES_ID) if SERIES_ID.isdigit() else SERIES_ID, "name": "Configured series"}
    else:
        series = discover_series()

    sid = series["id"]
    matches = api_get("/lol/matches", {
        "filter[serie_id]": sid,
        "per_page": 100,
        "sort": "begin_at"
    })

    normalized = [normalize_match(m) for m in matches]
    # Keep actual team-vs-team fixtures only.
    normalized = [m for m in normalized if len(m["opponents"]) == 2]

    payload = {
        "updated_at": datetime.now(timezone.utc).isoformat().replace("+00:00", "Z"),
        "source": "PandaScore",
        "series": {
            "id": series.get("id"),
            "name": series.get("name"),
            "full_name": series.get("full_name"),
            "year": series.get("year"),
        },
        "matches": normalized,
    }

    with open("data.json", "w", encoding="utf-8") as f:
        json.dump(payload, f, ensure_ascii=False, indent=2)
        f.write("\n")

    print(f"Wrote {len(normalized)} matches for series {sid}.")

if __name__ == "__main__":
    main()
