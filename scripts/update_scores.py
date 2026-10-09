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
    req = urllib.request.Request(url, headers={"Accept":"application/json","User-Agent":"kamra-worlds-tracker/1.1"})
    with urllib.request.urlopen(req, timeout=30) as response:
        return json.load(response)

def series_blob(s):
    return " ".join([
        str(s.get("name") or ""),
        str(s.get("full_name") or ""),
        str(s.get("slug") or ""),
        str((s.get("league") or {}).get("name") or ""),
        str((s.get("league") or {}).get("slug") or ""),
        str(s.get("year") or ""),
        str(s.get("begin_at") or ""),
        str(s.get("end_at") or ""),
    ]).lower()

def is_worlds_2026(s):
    b = series_blob(s)
    return "world" in b and "2026" in b

def discover_series():
    endpoints = [
        "/lol/series/running",
        "/lol/series/upcoming",
        "/lol/series/past",
        "/lol/series",
    ]
    seen = {}
    for endpoint in endpoints:
        try:
            rows = api_get(endpoint, {"per_page":100, "sort":"-begin_at"})
        except Exception as exc:
            print(f"Warning: {endpoint} failed: {exc}")
            continue
        for s in rows or []:
            if s.get("id") is not None:
                seen[str(s["id"])] = s

    candidates = [s for s in seen.values() if is_worlds_2026(s)]

    print("Worlds 2026 series candidates:")
    for s in sorted(candidates, key=lambda x: str(x.get("begin_at") or ""), reverse=True):
        print(
            f"  id={s.get('id')} | name={s.get('name')!r} | "
            f"full_name={s.get('full_name')!r} | "
            f"league={(s.get('league') or {}).get('name')!r} | "
            f"begin_at={s.get('begin_at')}"
        )

    if not candidates:
        raise RuntimeError("No Worlds 2026 series candidates found.")

    # Prefer a candidate that actually has matches.
    for s in sorted(candidates, key=lambda x: str(x.get("begin_at") or ""), reverse=True):
        matches = api_get(f"/series/{s['id']}/matches", {"per_page":100, "sort":"begin_at"})
        print(f"Candidate series {s['id']} returned {len(matches or [])} matches.")
        if matches:
            return s, matches

    return candidates[0], []

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
        "opponents": opponents,
    }

def main():
    if SERIES_ID:
        series = api_get(f"/series/{SERIES_ID}")
        matches = api_get(f"/series/{SERIES_ID}/matches", {"per_page":100, "sort":"begin_at"})
        print(f"Using configured series {series.get('id')} | {series.get('name')!r} | {series.get('full_name')!r}")
    else:
        series, matches = discover_series()

    if not matches:
        raise RuntimeError(
            f"Series {series.get('id')} returned 0 matches. "
            "Set PANDASCORE_SERIES_ID to one of the printed candidates that has matches."
        )

    normalized = [normalize_match(m) for m in matches]
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

    print(f"Wrote {len(normalized)} matches for series {series.get('id')}.")

if __name__ == "__main__":
    main()
