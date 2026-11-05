#!/usr/bin/env python3
"""Generate a self-hosted SVG line chart from GitHub's real contribution calendar."""

from datetime import datetime, timedelta, timezone
from pathlib import Path
import json
import math
import subprocess
import xml.sax.saxutils as xml

USERNAME = "CharudattaLende"
TODAY = datetime.now(timezone.utc).date()
START = TODAY - timedelta(days=30)
FROM = datetime.combine(START, datetime.min.time(), timezone.utc).isoformat().replace("+00:00", "Z")
TO = datetime.combine(TODAY + timedelta(days=1), datetime.min.time(), timezone.utc).isoformat().replace("+00:00", "Z")

QUERY = """
query($login: String!, $from: DateTime!, $to: DateTime!) {
  user(login: $login) {
    contributionsCollection(from: $from, to: $to) {
      contributionCalendar {
        totalContributions
        weeks {
          contributionDays {
            date
            contributionCount
          }
        }
      }
    }
  }
}
"""

result = subprocess.run(
    [
        "gh", "api", "graphql",
        "-f", "query=" + QUERY,
        "-F", "login=" + USERNAME,
        "-F", "from=" + FROM,
        "-F", "to=" + TO,
    ],
    check=True,
    capture_output=True,
    text=True,
)
payload = json.loads(result.stdout)
try:
    calendar = payload["data"]["user"]["contributionsCollection"]["contributionCalendar"]
except (KeyError, TypeError) as exc:
    raise SystemExit("GitHub did not return a contribution calendar: " + json.dumps(payload)) from exc

counts = {}
for week in calendar["weeks"]:
    for day in week["contributionDays"]:
        counts[day["date"]] = int(day["contributionCount"])

dates = [START + timedelta(days=i) for i in range(31)]
values = [counts.get(d.isoformat(), 0) for d in dates]
total = sum(values)
peak = max(values, default=0)
ymax = max(4, int(math.ceil(peak / 2.0) * 2))

W, H = 1100, 390
L, R, T, B = 78, 34, 84, 76
PW, PH = W - L - R, H - T - B
base_y = T + PH

def x_at(i):
    return L + (PW * i / (len(values) - 1))

def y_at(v):
    return T + PH * (1 - v / ymax)

coords = [(x_at(i), y_at(v)) for i, v in enumerate(values)]
line = " ".join(f"{x:.1f},{y:.1f}" for x, y in coords)
area = f"{L},{base_y} " + line + f" {L + PW},{base_y}"

parts = [
    f'<svg xmlns="http://www.w3.org/2000/svg" width="{W}" height="{H}" viewBox="0 0 {W} {H}" role="img" aria-labelledby="title desc">',
    '<title id="title">Charudatta Lende GitHub contribution graph</title>',
    f'<desc id="desc">Daily public GitHub contributions for {xml.escape(USERNAME)} over the last 31 days. {total} contributions in this period.</desc>',
    '<defs><linearGradient id="fill" x1="0" y1="0" x2="0" y2="1"><stop offset="0%" stop-color="#ffffff" stop-opacity=".30"/><stop offset="100%" stop-color="#ffffff" stop-opacity=".015"/></linearGradient></defs>',
    '<rect width="100%" height="100%" rx="18" fill="#0d1117"/>',
    f'<text x="{W/2}" y="42" fill="#f0f3f6" font-family="Arial, sans-serif" font-size="25" font-weight="700" text-anchor="middle">Charudatta\'s Contribution Graph</text>',
    f'<text x="{W/2}" y="66" fill="#9da7b3" font-family="Arial, sans-serif" font-size="13" text-anchor="middle">Daily GitHub contributions · Last 31 days · {total} total</text>',
]

for tick in range(0, ymax + 1, max(1, ymax // 4)):
    y = y_at(tick)
    parts.append(f'<line x1="{L}" y1="{y:.1f}" x2="{L+PW}" y2="{y:.1f}" stroke="#30363d" stroke-width="1"/>')
    parts.append(f'<text x="{L-18}" y="{y+5:.1f}" fill="#9da7b3" font-family="Arial, sans-serif" font-size="13" text-anchor="end">{tick}</text>')

parts.append(f'<polygon points="{area}" fill="url(#fill)"/>')
parts.append(f'<polyline points="{line}" fill="none" stroke="#f0f3f6" stroke-width="4" stroke-linecap="round" stroke-linejoin="round"/>')

for i, (x, y) in enumerate(coords):
    parts.append(f'<circle cx="{x:.1f}" cy="{y:.1f}" r="3.2" fill="#ffffff"><title>{dates[i].isoformat()}: {values[i]} contributions</title></circle>')

for i in range(0, 31, 5):
    x = x_at(i)
    label = dates[i].strftime("%b %d")
    parts.append(f'<text x="{x:.1f}" y="{base_y+30}" fill="#9da7b3" font-family="Arial, sans-serif" font-size="13" text-anchor="middle">{label}</text>')

parts.append(f'<text x="{L+PW/2}" y="{H-14}" fill="#9da7b3" font-family="Arial, sans-serif" font-size="13" text-anchor="middle">Date (UTC)</text>')
parts.append('</svg>')

out = Path("assets/contribution-graph.svg")
out.parent.mkdir(parents=True, exist_ok=True)
out.write_text("\n".join(parts), encoding="utf-8")
print(f"Generated {out} with {total} real public contributions over 31 days.")
