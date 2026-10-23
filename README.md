# Activity dashboard

Static dashboard of my Garmin activities, served by GitHub Pages and refreshed every morning by GitHub Actions through the Garmin Connect Personal API.

Tabs: Overview · Activities · HRP · Improve · Barcelona.

## Setup
1. Repo → Settings → Secrets and variables → Actions → New secret `GARMIN_PERSONAL_API_KEY` = your Garmin personal API key.
2. Repo → Settings → Pages → Source: **GitHub Actions**.
3. Actions → *Refresh Garmin data and deploy* → Run workflow.

## Changing things
- HRP dates: `config.json` → `hrp.start` / `hrp.end`.
- Barcelona events: `data/events.json` (hand-curated; past events hide themselves).
- Run locally: `GARMIN_PERSONAL_API_KEY=... python3 scripts/fetch.py` then `python3 -m http.server`.

The API key is never stored in the repo; it lives only in the Actions secret.
