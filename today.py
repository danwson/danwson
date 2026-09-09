#!/usr/bin/env python3
"""
Gera dark_mode.svg e light_mode.svg pro README de perfil do GitHub
(https://github.com/danwson/danwson), buscando stats reais via API.

Usa só o GITHUB_TOKEN automático do Actions (nada de PAT manual armazenado):
token de vida curta, escopo mínimo, gerado e destruído a cada execução.
Como consequência só lê dados PÚBLICOS (repos/commits/stars públicos) —
não conta contribuições em repositórios privados, o que é adequado pra um
card de perfil público de qualquer forma.
"""

import os
import sys
import time
from datetime import datetime, timezone

import requests

USERNAME = "danwson"
REST_URL = "https://api.github.com"

TOKEN = os.environ.get("GITHUB_TOKEN")
if not TOKEN:
    sys.exit("GITHUB_TOKEN não definido — normal só se rodar fora do Actions.")

HEADERS_REST = {
    "Authorization": f"Bearer {TOKEN}",
    "Accept": "application/vnd.github+json",
    "X-GitHub-Api-Version": "2022-11-28",
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
# Coleta de dados via API (só endpoints REST públicos)                        #
# --------------------------------------------------------------------------- #
def get_user_overview() -> dict:
    """Segue paginação — GITHUB_TOKEN consegue ler qualquer repo público,
    não só o do próprio workflow."""
    resp = requests.get(f"{REST_URL}/users/{USERNAME}", headers=HEADERS_REST, timeout=30)
    resp.raise_for_status()
    user = resp.json()

    repos, page = [], 1
    while True:
        resp = requests.get(
            f"{REST_URL}/users/{USERNAME}/repos",
            params={"type": "owner", "per_page": 100, "page": page},
            headers=HEADERS_REST,
            timeout=30,
        )
        resp.raise_for_status()
        batch = resp.json()
        if not batch:
            break
        repos.extend(r for r in batch if not r["fork"])
        page += 1

    stars = sum(r["stargazers_count"] for r in repos)
    return {
        "followers": user["followers"],
        "repos": user["public_repos"],
        "stars": stars,
        "repo_names": [r["name"] for r in repos],
    }


def get_total_commits() -> int:
    """Commits públicos autorados pelo usuário, via API de busca de commits."""
    resp = requests.get(
        f"{REST_URL}/search/commits",
        params={"q": f"author:{USERNAME}"},
        headers=HEADERS_REST,
        timeout=30,
    )
    resp.raise_for_status()
    return resp.json().get("total_count", 0)


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
    commits = get_total_commits()
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
