"""Draws the last year of GitHub contributions as a small pixel city skyline (an animated SVG).

Each week is one building. Its height follows that week's total, and each window is a day you contributed.
The data comes from the GitHub GraphQL API (GITHUB_TOKEN is enough for public contributions), or from a saved
API response with --from-json, which is how the design is previewed offline.

    python scripts/skyline.py --user SpicyFalcon619 --out dist/skyline.svg
    python scripts/skyline.py --from-json contrib.json --out skyline.svg
"""

import argparse
import json
import math
import os
import urllib.request

QUERY = """query($login:String!){user(login:$login){contributionsCollection{contributionCalendar{
totalContributions weeks{contributionDays{date contributionCount}}}}}}"""

# Palette taken from the header gif: night navy, two blues and one warm window light.
BG, GROUND = "#0A0D12", "#1B2540"
BODY, EDGE = "#121A2E", "#2A3F6E"
LIT = ["#38BDF8", "#4D8DFF", "#38BDF8", "#4D8DFF", "#FFB454"]
DARK_WINDOW = "#1A2542"
MUTED = "#5B6B8C"

W, H = 900, 220
BUILD_W, GAP = 13, 3
BASE = 172  # y of the ground line
MARGIN_X = 6


def fetch(user: str) -> dict:
    token = os.environ["GITHUB_TOKEN"]
    req = urllib.request.Request(
        "https://api.github.com/graphql",
        data=json.dumps({"query": QUERY, "variables": {"login": user}}).encode(),
        headers={"Authorization": f"bearer {token}", "Content-Type": "application/json", "User-Agent": "skyline"},
    )
    with urllib.request.urlopen(req, timeout=30) as r:
        data = json.load(r)
    if "errors" in data:
        raise SystemExit(f"GitHub API error: {data['errors']}")
    return data


def render(data: dict) -> str:
    cal = data["data"]["user"]["contributionsCollection"]["contributionCalendar"]
    weeks = [w["contributionDays"] for w in cal["weeks"]]
    total = cal["totalContributions"]
    sums = [sum(d["contributionCount"] for d in w) for w in weeks]
    peak = max(sums + [1])

    out = []
    css = f"""
    .b{{transform-box:fill-box;transform-origin:50% 100%;animation:rise .9s cubic-bezier(.2,.8,.2,1) both}}
    .w{{animation:tw 5s ease-in-out infinite}}
    @keyframes rise{{from{{transform:scaleY(0);opacity:0}}to{{transform:scaleY(1);opacity:1}}}}
    @keyframes tw{{0%,100%{{opacity:1}}50%{{opacity:.35}}}}
    @media (prefers-reduced-motion:reduce){{.b,.w{{animation:none}}}}
    text{{font:11px ui-monospace,SFMono-Regular,Menlo,Consolas,monospace}}
    """
    out.append(f'<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 {W} {H}" width="{W}" height="{H}" role="img" '
               f'aria-label="Contribution skyline: {total} contributions in the last year" shape-rendering="crispEdges">')
    out.append(f"<style>{css}</style>")
    out.append(f'<rect width="{W}" height="{H}" rx="6" fill="{BG}"/>')

    # A few fixed stars, so the sky is not empty. Positions are derived, not random, so the file is stable.
    for i in range(14):
        x = (i * 67 + 31) % (W - 20) + 10
        y = (i * 29 + 11) % 60 + 12
        out.append(f'<rect x="{x}" y="{y}" width="2" height="2" fill="{MUTED}" opacity=".55"/>')

    left = MARGIN_X + (W - 2 * MARGIN_X - len(weeks) * (BUILD_W + GAP) + GAP) / 2
    for i, (week, s) in enumerate(zip(weeks, sums)):
        active = [d for d in week if d["contributionCount"] > 0]
        # Square-root scale: one busy week must not flatten the rest of the year.
        h = 12 + round(math.sqrt(s / peak) * 112) if s else 8
        h -= h % 4
        x = round(left + i * (BUILD_W + GAP))
        y = BASE - h
        delay = round(i * 0.025, 3)
        g = [f'<g class="b" style="animation-delay:{delay}s">']
        g.append(f'<rect x="{x}" y="{y}" width="{BUILD_W}" height="{h}" fill="{BODY}"/>')
        g.append(f'<rect x="{x}" y="{y}" width="{BUILD_W}" height="2" fill="{EDGE}"/>')
        # Windows: 2 columns, rows from the bottom up. Lit = a day with contributions, up to what fits.
        rows = max(0, (h - 8) // 8)
        slots = min(rows * 2, 14)
        lit = min(len(active), slots)
        for k in range(slots):
            col, row = k % 2, k // 2
            wx = x + 2 + col * 5
            wy = BASE - 8 - row * 8
            is_lit = k < lit
            colour = LIT[(i + k) % len(LIT)] if is_lit else DARK_WINDOW
            cls = ' class="w"' if is_lit and (i * 7 + k * 3) % 5 == 0 else ""
            style = f' style="animation-delay:{round(((i * 13 + k * 17) % 50) / 10, 1)}s"' if cls else ""
            g.append(f'<rect{cls}{style} x="{wx}" y="{wy}" width="4" height="4" fill="{colour}"/>')
        g.append("</g>")
        out.append("".join(g))

    out.append(f'<rect x="0" y="{BASE}" width="{W}" height="2" fill="{GROUND}"/>')
    out.append(f'<text x="14" y="{H - 22}" fill="{MUTED}">{total} contributions in the last year</text>')
    out.append(f'<text x="{W - 14}" y="{H - 22}" fill="{MUTED}" text-anchor="end">one building a week, one lit window a day</text>')
    out.append("</svg>")
    return "".join(out)


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--user", default=os.environ.get("GITHUB_REPOSITORY_OWNER", ""))
    ap.add_argument("--from-json", help="a saved GraphQL response instead of calling the API")
    ap.add_argument("--out", default="dist/skyline.svg")
    a = ap.parse_args()
    if a.from_json:
        with open(a.from_json, encoding="utf-8") as f:
            data = json.load(f)
    else:
        if not a.user:
            raise SystemExit("--user is required")
        data = fetch(a.user)
    os.makedirs(os.path.dirname(os.path.abspath(a.out)), exist_ok=True)
    with open(a.out, "w", encoding="utf-8") as f:
        f.write(render(data))
    print(f"wrote {a.out}")


if __name__ == "__main__":
    main()
