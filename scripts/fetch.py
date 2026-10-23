#!/usr/bin/env python3
"""Pull activities from the Garmin Connect Personal API into data/.

Needs env GARMIN_PERSONAL_API_KEY. Writes:
  data/activities.json   slim summary of every activity
  data/tracks/<id>.json  GPS polyline + elevation/HR profile (HRP stages + recent)
  data/meta.json         last refresh time
"""
import json, os, sys, time, urllib.request, urllib.error
from datetime import datetime, timezone
from pathlib import Path

BASE = "https://personal.connectapi.garmin.com"
ROOT = Path(__file__).resolve().parent.parent
DATA = ROOT / "data"
CONFIG = json.loads((ROOT / "config.json").read_text())

KEEP = ["activityId", "activityName", "startTimeLocal", "startTimeGMT", "distance",
        "duration", "elapsedDuration", "movingDuration", "elevationGain", "elevationLoss",
        "maxElevation", "minElevation", "averageSpeed", "maxSpeed", "averageHR", "maxHR",
        "calories", "steps", "locationName", "startLatitude", "startLongitude",
        "endLatitude", "endLongitude", "aerobicTrainingEffect", "anaerobicTrainingEffect",
        "trainingEffectLabel", "activityTrainingLoad", "hrTimeInZone_1", "hrTimeInZone_2",
        "hrTimeInZone_3", "hrTimeInZone_4", "hrTimeInZone_5", "minTemperature",
        "maxTemperature", "vigorousIntensityMinutes", "moderateIntensityMinutes"]


def req(path, method="GET", headers=None, retries=3):
    for attempt in range(retries):
        r = urllib.request.Request(BASE + path, method=method, headers=headers or {})
        try:
            with urllib.request.urlopen(r, timeout=60) as resp:
                return resp.read()
        except urllib.error.HTTPError as e:
            if e.code in (429, 500, 502, 503) and attempt < retries - 1:
                time.sleep(5 * (attempt + 1))
                continue
            raise


def token():
    key = os.environ.get("GARMIN_PERSONAL_API_KEY", "").strip()
    if not key:
        sys.exit("GARMIN_PERSONAL_API_KEY is not set")
    raw = req("/personalapitoken-service/personal-api/personal-api-key/token", "POST",
              {"Authorization": f"ApiKey {key}"}).decode().strip()
    try:
        d = json.loads(raw)
        if isinstance(d, dict):
            return d.get("access_token") or d.get("accessToken") or d.get("token")
        return str(d)
    except json.JSONDecodeError:
        return raw


def main():
    auth = {"Authorization": f"Bearer {token()}"}
    acts, start = [], 0
    while True:
        page = json.loads(req(f"/activitylist-service/activities/search/activities?start={start}&limit=100", headers=auth))
        acts += page
        if len(page) < 100:
            break
        start += 100

    slim = []
    for a in acts:
        s = {k: a.get(k) for k in KEEP}
        s["type"] = a["activityType"]["typeKey"]
        slim.append(s)
    slim.sort(key=lambda x: x["startTimeLocal"], reverse=True)

    DATA.mkdir(exist_ok=True)
    (DATA / "tracks").mkdir(exist_ok=True)
    (DATA / "activities.json").write_text(json.dumps(slim, ensure_ascii=False, separators=(",", ":")))

    # Tracks: every HRP stage, plus the N most recent activities with GPS.
    h0, h1 = CONFIG["hrp"]["start"], CONFIG["hrp"]["end"]
    want = [a for a in slim if h0 <= a["startTimeLocal"][:10] <= h1 and a["type"] in CONFIG["hrp"]["types"]]
    gps = [a for a in slim if a.get("startLatitude")]
    want += gps if CONFIG.get("allTracks") else gps[: CONFIG.get("recentTracks", 10)]
    seen = set()
    for a in want:
        aid = a["activityId"]
        if aid in seen:
            continue
        seen.add(aid)
        out = DATA / "tracks" / f"{aid}.json"
        if out.exists():
            continue  # activities don't change once recorded
        try:
            d = json.loads(req(f"/activity-service/activity/{aid}/details?maxChartSize=300&maxPolylineSize=500", headers=auth)) or {}
        except Exception as e:  # one bad activity shouldn't stop the refresh
            print(f"skip track {aid}: {e}")
            continue
        idx = {m["key"]: m["metricsIndex"] for m in (d.get("metricDescriptors") or [])}

        def series(key):
            i = idx.get(key)
            rows = d.get("activityDetailMetrics") or []
            return [] if i is None else [(m["metrics"][i] if m.get("metrics") and i < len(m["metrics"]) else None) for m in rows]

        poly = (d.get("geoPolylineDTO") or {}).get("polyline") or []
        out.write_text(json.dumps({
            "id": aid,
            "line": [[round(p["lat"], 5), round(p["lon"], 5)] for p in poly if p.get("lat") is not None],
            "dist": [round(v / 1000, 3) if v is not None else None for v in series("sumDistance")],
            "elev": [round(v) if v is not None else None for v in series("directElevation")],
            "hr": [round(v) if v is not None else None for v in series("directHeartRate")],
        }, separators=(",", ":")))
        time.sleep(0.7)

    (DATA / "meta.json").write_text(json.dumps({
        "refreshed": datetime.now(timezone.utc).isoformat(timespec="minutes"),
        "count": len(slim)}))
    print(f"{len(slim)} activities, {len(seen)} tracks")


if __name__ == "__main__":
    main()
