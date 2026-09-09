#!/usr/bin/env python3
"""
Gera dark_mode.svg e light_mode.svg pro README de perfil do GitHub
(https://github.com/danwson/danwson), buscando stats reais via API.

Requer a env var ACCESS_TOKEN (Personal Access Token do GitHub) com escopo
'repo' + 'read:user' pra conseguir ler contribuições e stats de commits.
"""

import os
import sys
import time
from datetime import datetime, timezone

import requests

USERNAME = "danwson"
API_URL = "https://api.github.com/graphql"
REST_URL = "https://api.github.com"

TOKEN = os.environ.get("ACCESS_TOKEN")
if not TOKEN:
    sys.exit("ACCESS_TOKEN não definido — configure o secret no repositório.")

HEADERS_GQL = {"Authorization": f"bearer {TOKEN}"}
HEADERS_REST = {
    "Authorization": f"token {TOKEN}",
    "Accept": "application/vnd.github+json",
}

# --------------------------------------------------------------------------- #
# Campos fixos / editáveis à mão                                              #
# --------------------------------------------------------------------------- #
STATIC_FIELDS = {
    "OS": "Linux, Windows 10/11",
    "IDE": "VSCode 1.136.2",
    "Role": "Desenvolvedor PHP Full Stack",
    "Languages": "PHP, Laravel, JavaScript, MySQL/MariaDB",
    "Hobby": "Desenvolvimento de jogos indie",
    "LinkedIn": "dani-alves-dev",
}


# --------------------------------------------------------------------------- #
# Coleta de dados via API                                                     #
# --------------------------------------------------------------------------- #
def gql(query: str, variables: dict) -> dict:
    resp = requests.post(
        API_URL, json={"query": query, "variables": variables}, headers=HEADERS_GQL, timeout=30
    )
    resp.raise_for_status()
    data = resp.json()
    if "errors" in data:
        raise RuntimeError(data["errors"])
    return data["data"]


def get_user_overview() -> dict:
    query = """
    query($login: String!) {
      user(login: $login) {
        createdAt
        followers { totalCount }
        repositories(first: 100, ownerAffiliations: OWNER, isFork: false,
                      privacy: PUBLIC) {
          totalCount
          nodes { name stargazerCount }
        }
      }
    }
    """
    data = gql(query, {"login": USERNAME})["user"]
    stars = sum(r["stargazerCount"] for r in data["repositories"]["nodes"])
    return {
        "created_at": data["createdAt"],
        "followers": data["followers"]["totalCount"],
        "repos": data["repositories"]["totalCount"],
        "stars": stars,
        "repo_names": [r["name"] for r in data["repositories"]["nodes"]],
    }


def get_total_commits(created_at: str) -> int:
    """Soma contribuições de commit ano a ano (a API só cobre 1 ano por vez)."""
    start_year = datetime.fromisoformat(created_at.replace("Z", "+00:00")).year
    end_year = datetime.now(timezone.utc).year

    query = """
    query($login: String!, $from: DateTime!, $to: DateTime!) {
      user(login: $login) {
        contributionsCollection(from: $from, to: $to) {
          totalCommitContributions
          restrictedContributionsCount
        }
      }
    }
    """
    total = 0
    for year in range(start_year, end_year + 1):
        frm = f"{year}-01-01T00:00:00Z"
        to = f"{year}-12-31T23:59:59Z"
        data = gql(query, {"login": USERNAME, "from": frm, "to": to})["user"]
        cc = data["contributionsCollection"]
        total += cc["totalCommitContributions"] + cc["restrictedContributionsCount"]
    return total


def get_lines_of_code(repo_names: list[str]) -> tuple[int, int]:
    """Soma additions/deletions do usuário via /stats/contributors por repo.
    Esse endpoint é assíncrono no GitHub: se voltar 202, precisa tentar de novo."""
    additions, deletions = 0, 0
    for name in repo_names:
        url = f"{REST_URL}/repos/{USERNAME}/{name}/stats/contributors"
        for attempt in range(6):
            resp = requests.get(url, headers=HEADERS_REST, timeout=30)
            if resp.status_code == 202:
                time.sleep(3)
                continue
            if resp.status_code != 200:
                break
            for contributor in resp.json() or []:
                if contributor.get("author", {}).get("login") == USERNAME:
                    for week in contributor.get("weeks", []):
                        additions += week.get("a", 0)
                        deletions += week.get("d", 0)
            break
    return additions, deletions


# --------------------------------------------------------------------------- #
# Renderização do SVG (card estilo terminal)                                  #
# --------------------------------------------------------------------------- #
def build_lines(stats: dict) -> list[str]:
    def row(label, value):
        dots = "." * max(2, 26 - len(label))
        return f"{label} {dots} {value}"

    lines = [
        f"{USERNAME}@github",
        "─" * 46,
        row("OS", STATIC_FIELDS["OS"]),
        row("IDE", STATIC_FIELDS["IDE"]),
        row("Role", STATIC_FIELDS["Role"]),
        row("Languages", STATIC_FIELDS["Languages"]),
        row("Hobby", STATIC_FIELDS["Hobby"]),
        "─" * 46,
        row("LinkedIn", STATIC_FIELDS["LinkedIn"]),
        "─" * 46,
        row("Repos", stats["repos"]),
        row("Stars", stats["stars"]),
        row("Followers", stats["followers"]),
        row("Commits", stats["commits"]),
        row("Lines of Code", f"+{stats['additions']} / -{stats['deletions']}"),
        "─" * 46,
        f"Last updated: {datetime.now(timezone.utc):%Y-%m-%d %H:%M UTC}",
    ]
    return lines


def render_svg(lines: list[str], bg: str, fg: str, accent: str) -> str:
    line_height = 20
    padding_top = 30
    padding_x = 24
    width = 560
    height = padding_top * 2 + line_height * len(lines)

    text_rows = []
    for i, line in enumerate(lines):
        y = padding_top + i * line_height
        color = accent if line.startswith("─") or "@github" in line or line.startswith("Last") else fg
        escaped = (
            line.replace("&", "&amp;").replace("<", "&lt;").replace(">", "&gt;")
        )
        text_rows.append(
            f'<text x="{padding_x}" y="{y}" fill="{color}" '
            f'font-family="Consolas, Menlo, monospace" font-size="13">{escaped}</text>'
        )

    return f'''<svg xmlns="http://www.w3.org/2000/svg" width="{width}" height="{height}">
  <rect width="100%" height="100%" rx="10" fill="{bg}" />
  {"".join(text_rows)}
</svg>'''


def main():
    overview = get_user_overview()
    commits = get_total_commits(overview["created_at"])
    additions, deletions = get_lines_of_code(overview["repo_names"])

    stats = {
        "repos": overview["repos"],
        "stars": overview["stars"],
        "followers": overview["followers"],
        "commits": commits,
        "additions": additions,
        "deletions": deletions,
    }
    lines = build_lines(stats)

    dark = render_svg(lines, bg="#0d1117", fg="#c9d1d9", accent="#58a6ff")
    light = render_svg(lines, bg="#ffffff", fg="#24292f", accent="#0969da")

    with open("dark_mode.svg", "w", encoding="utf-8") as f:
        f.write(dark)
    with open("light_mode.svg", "w", encoding="utf-8") as f:
        f.write(light)

    print("SVGs gerados com sucesso.")


if __name__ == "__main__":
    main()
