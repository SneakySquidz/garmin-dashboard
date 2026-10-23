#!/usr/bin/env python3
"""Build an artifact-safe copy of the dashboard into build/artifact/.

The Claude artifact viewer wraps the page in its own <html>/<head>/<body>,
blocks external stylesheets and file downloads, so this script:
  - strips the document wrapper tags
  - inlines Leaflet's CSS from vendor/
  - removes the .ics "Add to calendar" button
  - swaps the footer to point at the live GitHub Pages site
and copies config.json + data/ alongside. Prints the published file list (JSON).
"""
import json, re, shutil
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
OUT = ROOT / "build" / "artifact"

s = (ROOT / "index.html").read_text()
s = re.sub(r"<!doctype html>\s*<html[^>]*>\s*<head>\s*", "", s, flags=re.I)
s = s.replace('<meta charset="utf-8">\n', "").replace('<meta name="viewport" content="width=device-width,initial-scale=1">\n', "")
s = s.replace("</head>\n<body>\n", "").replace("</body>\n</html>\n", "")
s = s.replace("position:sticky;top:0;", "position:sticky;top:env(safe-area-inset-top,0px);")
css = (ROOT / "vendor" / "leaflet-1.9.4.css").read_text()
s = s.replace('<link rel="stylesheet" href="https://cdnjs.cloudflare.com/ajax/libs/leaflet/1.9.4/leaflet.min.css">', "<style>" + css + "</style>")
i = s.find("${exact?`<a class=\"btn\" data-ics=")
if i >= 0:
    j = s.index(":''}</div></div></div>`;", i)
    s = s[:i] + s[j + 4:]
s = s.replace("<footer>Data: Garmin Connect Personal API, refreshed daily by GitHub Actions.",
              '<footer>Synced daily from <a href="https://sneakysquidz.github.io/garmin-dashboard/" target="_blank" rel="noopener">sneakysquidz.github.io/garmin-dashboard</a> (Garmin Connect Personal API).')
for bad in ("<!doctype", "leaflet.min.css", "download="):
    assert bad not in s.lower(), f"artifact build still contains {bad}"

if OUT.exists():
    shutil.rmtree(OUT)
(OUT / "data").mkdir(parents=True)
(OUT / "index.html").write_text(s)
shutil.copy(ROOT / "config.json", OUT / "config.json")
shutil.copytree(ROOT / "data", OUT / "data", dirs_exist_ok=True)
files = sorted(str(p.relative_to(OUT)) for p in OUT.rglob("*.json"))
print(json.dumps(files))
