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

import io
import os
import sys
import time
from datetime import datetime, timezone

import requests
from PIL import Image, ImageOps

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
        "avatar_url": user["avatar_url"],
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
# Avatar convertido pra ASCII art                                             #
# --------------------------------------------------------------------------- #
ASCII_RAMP = " .:-=+*#%@"  # do mais claro (espaço) ao mais escuro (@)


def avatar_to_ascii(avatar_url: str, cols: int = 30) -> list[str]:
    resp = requests.get(avatar_url, timeout=30)
    resp.raise_for_status()
    img = Image.open(io.BytesIO(resp.content)).convert("L")  # tons de cinza
    img = ImageOps.autocontrast(img, cutoff=1)  # espalha os tons, evita saturar tudo em "@"

    # caracteres monoespaçados são ~2x mais altos que largos —
    # compensa a proporção pra imagem não ficar esticada
    rows = max(1, round(cols * img.height / img.width * 0.5))
    img = img.resize((cols, rows))

    pixels = list(img.getdata())
    art = []
    for r in range(rows):
        row_pixels = pixels[r * cols : (r + 1) * cols]
        row = "".join(
            ASCII_RAMP[min(len(ASCII_RAMP) - 1, (255 - p) * len(ASCII_RAMP) // 256)]
            for p in row_pixels
        )
        art.append(row)
    return art


# --------------------------------------------------------------------------- #
# Renderização do SVG (card estilo terminal, duas colunas)                    #
# --------------------------------------------------------------------------- #
def build_info_lines(stats: dict) -> list[str]:
    def row(label, value):
        dots = "." * max(2, 22 - len(label))
        return f"{label} {dots} {value}"

    return [
        f"{USERNAME}@github",
        "─" * 40,
        row("OS", STATIC_FIELDS["OS"]),
        row("IDE", STATIC_FIELDS["IDE"]),
        row("Role", STATIC_FIELDS["Role"]),
        row("Languages", STATIC_FIELDS["Languages"]),
        row("Hobby", STATIC_FIELDS["Hobby"]),
        "─" * 40,
        row("LinkedIn", STATIC_FIELDS["LinkedIn"]),
        "─" * 40,
        row("Repos", stats["repos"]),
        row("Stars", stats["stars"]),
        row("Followers", stats["followers"]),
        row("Commits", stats["commits"]),
        row("Lines of Code", f"+{stats['additions']} / -{stats['deletions']}"),
        "─" * 40,
        f"Last updated: {datetime.now(timezone.utc):%Y-%m-%d %H:%M UTC}",
    ]


def _escape(text: str) -> str:
    return text.replace("&", "&amp;").replace("<", "&lt;").replace(">", "&gt;")


def render_svg(art_lines: list[str], info_lines: list[str], bg: str, fg: str, accent: str) -> str:
    font_size = 12
    char_w = font_size * 0.6
    line_height = 16
    padding_top = 26
    padding_x = 22
    gutter = 24

    art_w = max((len(l) for l in art_lines), default=0)
    art_col_px = round(art_w * char_w)
    info_x = padding_x + art_col_px + gutter

    rows = max(len(art_lines), len(info_lines))
    art_lines = art_lines + [""] * (rows - len(art_lines))
    info_lines = info_lines + [""] * (rows - len(info_lines))

    width = info_x + max((len(l) for l in info_lines), default=0) * char_w + padding_x
    height = padding_top * 2 + line_height * rows

    text_rows = []
    for i in range(rows):
        y = padding_top + i * line_height

        if art_lines[i]:
            text_rows.append(
                f'<text x="{padding_x}" y="{y}" fill="{fg}" '
                f'font-family="Consolas, Menlo, monospace" font-size="{font_size}" '
                f'xml:space="preserve">{_escape(art_lines[i])}</text>'
            )

        info_line = info_lines[i]
        if info_line:
            color = (
                accent
                if info_line.startswith("─") or "@github" in info_line or info_line.startswith("Last")
                else fg
            )
            text_rows.append(
                f'<text x="{info_x}" y="{y}" fill="{color}" '
                f'font-family="Consolas, Menlo, monospace" font-size="{font_size}">{_escape(info_line)}</text>'
            )

    return f'''<svg xmlns="http://www.w3.org/2000/svg" width="{round(width)}" height="{round(height)}">
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
    art_lines = avatar_to_ascii(overview["avatar_url"])
    info_lines = build_info_lines(stats)

    dark = render_svg(art_lines, info_lines, bg="#0d1117", fg="#c9d1d9", accent="#58a6ff")
    light = render_svg(art_lines, info_lines, bg="#ffffff", fg="#24292f", accent="#0969da")

    with open("dark_mode.svg", "w", encoding="utf-8") as f:
        f.write(dark)
    with open("light_mode.svg", "w", encoding="utf-8") as f:
        f.write(light)

    print("SVGs gerados com sucesso.")


if __name__ == "__main__":
    main()
