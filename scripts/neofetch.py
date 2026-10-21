"""Draws a neofetch-style terminal card for the profile as an animated SVG.

The facts about you live in profile.json (edit that when something changes, for example the year of study). The
numbers (languages, repositories, stars, contributions, account age) come from the GitHub GraphQL API, or from a
saved response with --from-json for offline previews.

    python scripts/neofetch.py --user SpicyFalcon619 --out dist/neofetch.svg
    python scripts/neofetch.py --from-json profile_data.json --out neofetch.svg
"""

import argparse
import datetime
import html
import json
import os
import urllib.request
from collections import Counter

QUERY = """query($login:String!){user(login:$login){createdAt followers{totalCount}
repositories(ownerAffiliations:OWNER,isFork:false,privacy:PUBLIC,first:100){totalCount nodes{stargazerCount
languages(first:6,orderBy:{field:SIZE,direction:DESC}){edges{size node{name}}}}}
contributionsCollection{contributionCalendar{totalContributions}}}}"""

BG, LINE, MUTED, TEXT = "#0A0D12", "#1B2540", "#5B6B8C", "#DCE6F7"
SKY, BLUE, AMBER = "#38BDF8", "#4D8DFF", "#FFB454"
SWATCH = ["#131822", "#21365E", "#2F5394", "#3E72CB", BLUE, SKY, AMBER, "#E6EDF7"]

LOGO = [
    r"        /\        ",
    r"       /  \       ",
    r"      /    \      ",
    r"     /      \     ",
    r"    /   ,,   \    ",
    r"   /   |  |   -\  ",
    r"  /_-''    ''-_\  ",
]

W = 860
CH = 8.45  # width of one character of the 14px monospace font, used for the typing animation steps


def fetch(user: str) -> dict:
    req = urllib.request.Request(
        "https://api.github.com/graphql",
        data=json.dumps({"query": QUERY, "variables": {"login": user}}).encode(),
        headers={"Authorization": f"bearer {os.environ['GITHUB_TOKEN']}", "Content-Type": "application/json", "User-Agent": "neofetch"},
    )
    with urllib.request.urlopen(req, timeout=30) as r:
        data = json.load(r)
    if "errors" in data:
        raise SystemExit(f"GitHub API error: {data['errors']}")
    return data


def age(created: str, now: datetime.datetime) -> str:
    c = datetime.datetime.fromisoformat(created.replace("Z", "+00:00"))
    months = (now.year - c.year) * 12 + now.month - c.month - (1 if now.day < c.day else 0)
    y, m = divmod(max(months, 0), 12)
    return f"{y} yr {m} mo" if y else f"{m} mo"


def languages(repos: list) -> str:
    size = Counter()
    for r in repos:
        for e in r["languages"]["edges"]:
            size[e["node"]["name"]] += e["size"]
    total = sum(size.values()) or 1
    return ", ".join(f"{n} {round(v * 100 / total)}%" for n, v in size.most_common(4))


def render(data: dict, info: dict, now: datetime.datetime) -> str:
    u = data["data"]["user"]
    repos = u["repositories"]["nodes"]
    stars = sum(r["stargazerCount"] for r in repos)
    rows = [
        ("OS", info["os"]),
        ("WM", info["wm"]),
        ("Uni", info["university"]),
        ("Year", info["year"]),
        ("Focus", info["focus"]),
        ("Learning", info["learning"]),
        ("Langs", languages(repos)),
        ("Repos", f"{u['repositories']['totalCount']} public, {stars} stars"),
        ("Commits", f"{u['contributionsCollection']['contributionCalendar']['totalContributions']} in the last year"),
        ("Uptime", f"{age(u['createdAt'], now)} on GitHub"),
        ("Off duty", info["offduty"]),
    ]

    x_logo, x_info = 52, 318
    y0, step = 104, 23
    height = y0 + step * (len(rows) + 3) + 40
    t = 0.0  # animation clock, seconds

    css = """
    text{font:14px ui-monospace,SFMono-Regular,Menlo,Consolas,'DejaVu Sans Mono',monospace;white-space:pre}
    .ty{clip-path:inset(0 100% 0 0);animation:type var(--d) steps(var(--n),end) var(--t) forwards}
    .fd{opacity:0;animation:fade .45s ease-out var(--t) forwards}
    .cur{animation:blink 1.1s steps(1) infinite}
    @keyframes type{to{clip-path:inset(0 0 0 0)}}
    @keyframes fade{to{opacity:1}}
    @keyframes blink{50%{opacity:0}}
    @media (prefers-reduced-motion:reduce){.ty{clip-path:none;animation:none}.fd{opacity:1;animation:none}.cur{animation:none}}
    """
    o = [f'<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 {W} {height}" width="{W}" height="{height}" role="img" '
         f'aria-label="Terminal card: {html.escape(info["os"])} with {html.escape(info["wm"])}, {html.escape(info["year"])} at {html.escape(info["university"])}">']
    o.append(f"<style>{css}</style>")
    o.append(f'<rect x=".5" y=".5" width="{W - 1}" height="{height - 1}" rx="8" fill="{BG}" stroke="{LINE}"/>')
    o.append(f'<line x1="0" y1="36" x2="{W}" y2="36" stroke="{LINE}"/>')
    o.append(f'<text x="18" y="24" fill="{MUTED}" font-size="12">{html.escape(os.environ.get("CARD_TITLE", "spicyfalcon@" + info["host"] + ": ~"))}</text>')

    def typed(x, y, n, dur, body, delay):
        return f'<text class="ty" style="--n:{n};--d:{dur:.2f}s;--t:{delay:.2f}s" x="{x}" y="{y}" xml:space="preserve">{body}</text>'

    # The command being typed.
    cmd = "neofetch"
    o.append(typed(18, 70, len(cmd) + 2, 0.9, f'<tspan fill="{SKY}">$</tspan> <tspan fill="{TEXT}">{cmd}</tspan>', t))
    t = 1.3

    # Logo, line by line.
    for i, line in enumerate(LOGO):
        o.append(f'<text class="fd" style="--t:{t + i * 0.09:.2f}s" x="{x_logo}" y="{y0 + 70 + i * step}" fill="{BLUE}" font-size="17" xml:space="preserve">{html.escape(line)}</text>')

    # Header line and the facts.
    handle = f"spicyfalcon@{info['host']}"
    o.append(typed(x_info, y0, len(handle), 0.7, f'<tspan fill="{SKY}" font-weight="700">{html.escape(handle)}</tspan>', t))
    o.append(f'<line class="fd" style="--t:{t + 0.2:.2f}s" x1="{x_info}" y1="{y0 + 8}" x2="{x_info + 210}" y2="{y0 + 8}" stroke="{LINE}"/>')
    for i, (k, v) in enumerate(rows):
        y = y0 + step * (i + 1) + 6
        delay = t + 0.35 + i * 0.22
        n = 10 + len(v) + 2
        body = f'<tspan fill="{SKY}">{html.escape(k.ljust(10))}</tspan><tspan fill="{TEXT}">{html.escape(v)}</tspan>'
        o.append(typed(x_info, y, n, min(0.2 + n * 0.025, 1.0), body, delay))
    t_end = t + 0.35 + len(rows) * 0.22 + 0.4

    # Colour swatches, then a waiting prompt with a blinking cursor.
    ys = y0 + step * (len(rows) + 1) + 18
    for i, c in enumerate(SWATCH):
        o.append(f'<rect class="fd" style="--t:{t_end + i * 0.06:.2f}s" x="{x_info + i * 26}" y="{ys}" width="22" height="14" fill="{c}"/>')
    yp = ys + 48
    o.append(f'<text class="fd" style="--t:{t_end + 0.6:.2f}s" x="18" y="{yp}" xml:space="preserve"><tspan fill="{SKY}">$</tspan> <tspan class="cur" fill="{TEXT}">_</tspan></text>')
    o.append("</svg>")
    return "".join(o)


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--user", default=os.environ.get("GITHUB_REPOSITORY_OWNER", ""))
    ap.add_argument("--from-json")
    ap.add_argument("--info", default=os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "profile.json"))
    ap.add_argument("--out", default="dist/neofetch.svg")
    a = ap.parse_args()
    if a.from_json:
        with open(a.from_json, encoding="utf-8") as f:
            data = json.load(f)
    else:
        if not a.user:
            raise SystemExit("--user is required")
        data = fetch(a.user)
    with open(a.info, encoding="utf-8") as f:
        info = json.load(f)
    os.makedirs(os.path.dirname(os.path.abspath(a.out)), exist_ok=True)
    with open(a.out, "w", encoding="utf-8") as f:
        f.write(render(data, info, datetime.datetime.now(datetime.timezone.utc)))
    print(f"wrote {a.out}")


if __name__ == "__main__":
    main()
