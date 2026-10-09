#!/usr/bin/env python3
import json, os, sys, urllib.parse, urllib.request
from datetime import datetime, timezone

API = "https://api.pandascore.co"
TOKEN = os.environ.get("PANDASCORE_TOKEN", "").strip()
SERIES_ID = os.environ.get("PANDASCORE_SERIES_ID", "11014").strip() or "11014"

if not TOKEN:
    print("PANDASCORE_TOKEN is missing.", file=sys.stderr)
    sys.exit(2)

def api_get(path, params=None):
    params = dict(params or {})
    params["token"] = TOKEN
    url = API + path + "?" + urllib.parse.urlencode(params, doseq=True)
    req = urllib.request.Request(url, headers={"Accept":"application/json","User-Agent":"kamra-worlds-tracker/1.2"})
    with urllib.request.urlopen(req, timeout=30) as response:
        return json.load(response)

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
        tid = r.get("team_id")
        if tid is not None:
            try:
                results[str(tid)] = int(r.get("score", 0))
            except Exception:
                results[str(tid)] = 0

    opponents = []
    for raw in m.get("opponents") or []:
        opp = normalize_opponent(raw)
        if opp:
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
    # One PandaScore request per run.
    matches = api_get(f"/series/{SERIES_ID}/matches", {"per_page":100, "sort":"begin_at"})
    normalized = [normalize_match(m) for m in matches or []]
    ready = sum(1 for m in normalized if len(m["opponents"]) == 2)
    pending = len(normalized) - ready

    print(f"Series {SERIES_ID}: fetched {len(normalized)} matches ({ready} ready, {pending} pending).")

    serie = normalized[0].get("serie") if normalized else {}
    payload = {
        "updated_at": datetime.now(timezone.utc).isoformat().replace("+00:00","Z"),
        "source": "PandaScore",
        "series": {
            "id": (serie or {}).get("id") or (int(SERIES_ID) if SERIES_ID.isdigit() else SERIES_ID),
            "name": (serie or {}).get("name"),
            "full_name": (serie or {}).get("full_name"),
            "year": (serie or {}).get("year"),
        },
        "matches": normalized,
    }

    with open("data.json", "w", encoding="utf-8") as f:
        json.dump(payload, f, ensure_ascii=False, indent=2)
        f.write("\n")

    print(f"Wrote {len(normalized)} matches to data.json using 1 PandaScore API request.")

if __name__ == "__main__":
    main()
