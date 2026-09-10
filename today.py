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
from PIL import Image

AVATAR_PATH = "assets/avatar.jpg"  # imagem fixa no repo, não o avatar do GitHub

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
    "Editor": "VSCode 1.136.2",
    "Role": "Full Stack PHP Developer",
    "Languages": "PHP, Laravel, JavaScript, MySQL/MariaDB",
    "Hobby": "Indie game development",
    "LinkedIn": "dani-alves-dev",
}

# paleta: (cor no modo escuro, cor no modo claro)
PALETTE = {
    "label": ("#ffa657", "#bc4c00"),    # títulos/labels de cada linha, laranja
    "dim": ("#5b6270", "#8c929b"),      # pontinhos e traços de separador
    "value": ("#c9d1d9", "#24292f"),    # valores, cor de texto padrão (sem cor própria)
    "add": ("#3fb950", "#1a7f37"),      # linhas adicionadas (verde)
    "del": ("#f85149", "#cf222e"),      # linhas removidas (vermelho)
    "footer": ("#5b6270", "#8c929b"),   # rodapé, discreto
    "art": ("#c9d1d9", "#24292f"),      # arte ASCII, monocromática (cor de texto padrão)
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
        "owned_repos": [(USERNAME, r["name"]) for r in repos],
    }


def get_contributed_repos(owned: list[tuple[str, str]]) -> list[tuple[str, str]]:
    """Repos públicos de OUTROS donos onde o usuário aparece nos commits,
    via busca de commits (até 1000 resultados, limite da Search API do
    GitHub — cobre bem o uso normal de um perfil pessoal)."""
    owned_set = {f"{o}/{n}".lower() for o, n in owned}
    found = {}
    for page in range(1, 11):
        resp = requests.get(
            f"{REST_URL}/search/commits",
            params={"q": f"author:{USERNAME}", "per_page": 100, "page": page},
            headers=HEADERS_REST,
            timeout=30,
        )
        resp.raise_for_status()
        items = resp.json().get("items", [])
        if not items:
            break
        for item in items:
            full_name = item["repository"]["full_name"]
            if full_name.lower() not in owned_set:
                owner, name = full_name.split("/", 1)
                found[full_name.lower()] = (owner, name)
        if len(items) < 100:
            break
    return list(found.values())


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


def get_lines_of_code(repos: list[tuple[str, str]]) -> tuple[int, int]:
    """Soma additions/deletions do usuário via /stats/contributors por repo
    (funciona pra qualquer repo público, não só os que ele é dono).
    Esse endpoint é assíncrono no GitHub: se voltar 202, precisa tentar de novo."""
    additions, deletions = 0, 0
    for owner, name in repos:
        url = f"{REST_URL}/repos/{owner}/{name}/stats/contributors"
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
# Avatar (imagem fixa em assets/avatar.jpg) -> arte em caracteres, monocromática #
# --------------------------------------------------------------------------- #
# Rampa curta (poucos níveis) pra não ficar "cheia de detalhe" como uma rampa
# de tons de cinza tradicional (~70 símbolos) deixaria — só 9 níveis de
# densidade. Sem cor por pixel: só um tom (PALETTE["art"]), igual ao card
# de referência.
ASCII_RAMP = ".:-=+*#%@"


def _detect_bg_color(img: Image.Image) -> tuple[int, int, int]:
    """Amostra os dois cantos de CIMA (o rosto/roupa geralmente ocupam a parte
    de baixo do enquadramento) pra estimar a cor do fundo liso."""
    w, h = img.size
    samples = [img.getpixel((2, 2)), img.getpixel((w - 3, 2)), img.getpixel((w // 2, 2))]
    r = sum(p[0] for p in samples) / len(samples)
    g = sum(p[1] for p in samples) / len(samples)
    b = sum(p[2] for p in samples) / len(samples)
    return (r, g, b)


def image_to_art(path: str, cols: int = 30) -> list[list[str | None]]:
    """Retorna uma grade [linha][coluna] de caractere (ou None = célula vazia,
    deixa o fundo do card aparecer).

    Não depende de transparência real no arquivo: detecta a cor do fundo
    (liso, tipo foto de estúdio) e recorta por distância de cor — assim
    funciona tanto com PNG já recortado quanto com foto comum de fundo liso."""
    img = Image.open(path).convert("RGB")
    bg_color = _detect_bg_color(img)

    rows = max(1, round(cols * img.height / img.width * 0.5))
    small = img.resize((cols, rows), Image.LANCZOS)

    threshold = 35  # abaixo disso = fundo (célula vazia)
    grid = []
    for r in range(rows):
        row = []
        for c in range(cols):
            red, green, blue = small.getpixel((c, r))
            dist = ((red - bg_color[0]) ** 2 + (green - bg_color[1]) ** 2 + (blue - bg_color[2]) ** 2) ** 0.5
            if dist < threshold:
                row.append(None)
            else:
                luminance = 0.299 * red + 0.587 * green + 0.114 * blue
                level = min(len(ASCII_RAMP) - 1, int((255 - luminance) / 256 * len(ASCII_RAMP)))
                row.append(ASCII_RAMP[level])
        grid.append(row)
    return grid


# --------------------------------------------------------------------------- #
# Painel de info, no formato "neofetch": título, campos com "." e "- Seção -" #
# --------------------------------------------------------------------------- #
LABEL_COL = 20  # coluna onde os valores começam a alinhar
RULE_WIDTH = 40


def _title_row(text: str) -> dict:
    dashes = "-" * max(2, RULE_WIDTH - len(text) - 1)
    return {"kind": "title", "label": text, "dashes": dashes}


def _section_row(name: str) -> dict:
    prefix = f"- {name} "
    dashes = "-" * max(2, RULE_WIDTH - len(prefix))
    return {"kind": "section", "label": prefix, "dashes": dashes}


def _field_row(label: str, value) -> dict:
    prefix = f". {label}:"
    dots = "." * max(2, LABEL_COL - len(prefix))
    return {"kind": "field", "label": prefix, "dots": dots, "value": f" {value}"}


def _spacer_row() -> dict:
    return {"kind": "spacer"}


def build_info_rows(stats: dict) -> list[dict]:
    loc_value = [
        (f"+{stats['additions']:,}", "add"),
        (", ", "dim"),
        (f"-{stats['deletions']:,}", "del"),
    ]
    return [
        _title_row(f"{USERNAME} @ github"),
        _field_row("OS", STATIC_FIELDS["OS"]),
        _field_row("Editor", STATIC_FIELDS["Editor"]),
        _field_row("Role", STATIC_FIELDS["Role"]),
        _spacer_row(),
        _field_row("Languages", STATIC_FIELDS["Languages"]),
        _spacer_row(),
        _field_row("Hobby", STATIC_FIELDS["Hobby"]),
        _section_row("Contact"),
        _field_row("LinkedIn", STATIC_FIELDS["LinkedIn"]),
        _section_row("GitHub Stats"),
        _field_row("Repos", f"{stats['repos']:,} {{Contributed: {stats['contributed']:,}}}"),
        _field_row("Stars", f"{stats['stars']:,}"),
        _field_row("Followers", f"{stats['followers']:,}"),
        _field_row("Commits", f"{stats['commits']:,}"),
        {"kind": "loc", "label": ". Lines of Code:", "parts": loc_value},
        _spacer_row(),
        {"kind": "footer", "text": f"Updated {datetime.now(timezone.utc):%Y-%m-%d %H:%M UTC}"},
    ]


def _escape(text: str) -> str:
    return text.replace("&", "&amp;").replace("<", "&lt;").replace(">", "&gt;")


def _info_row_text_len(row: dict) -> int:
    if row["kind"] in ("title", "section"):
        return len(row["label"]) + len(row["dashes"])
    if row["kind"] == "field":
        return len(row["label"]) + len(row["dots"]) + len(row["value"])
    if row["kind"] == "loc":
        return len(row["label"]) + sum(len(t) for t, _ in row["parts"])
    if row["kind"] == "footer":
        return len(row["text"])
    return 1


# --------------------------------------------------------------------------- #
# Renderização do SVG (card estilo terminal, duas colunas)                    #
# --------------------------------------------------------------------------- #
def render_svg(art_grid: list[list[tuple]], info_rows: list[dict], bg: str, theme: str) -> str:
    idx = 0 if theme == "dark" else 1
    col = {name: pair[idx] for name, pair in PALETTE.items()}

    font_size = 13
    char_w = font_size * 0.62
    line_height = 18
    padding_top = 26
    padding_x = 22
    gutter = 26

    art_cols = max((len(row) for row in art_grid), default=0)
    art_col_px = round(art_cols * char_w)
    info_x = padding_x + art_col_px + gutter

    rows = max(len(art_grid), len(info_rows))
    max_info_chars = max((_info_row_text_len(r) for r in info_rows), default=0)
    width = info_x + max_info_chars * char_w + padding_x
    height = padding_top * 2 + line_height * rows

    elements = []
    for i in range(rows):
        y = padding_top + i * line_height

        if i < len(art_grid):
            row_glyphs = art_grid[i]
            spans = "".join(
                f'<tspan fill="{col["art"]}">{glyph}</tspan>' if glyph else '<tspan> </tspan>'
                for glyph in row_glyphs
            )
            elements.append(
                f'<text x="{padding_x}" y="{y}" '
                f'font-family="Consolas, Menlo, monospace" font-size="{font_size}" '
                f'xml:space="preserve">{spans}</text>'
            )

        if i >= len(info_rows):
            continue
        row = info_rows[i]
        spans = ""
        if row["kind"] in ("title", "section"):
            spans = (
                f'<tspan fill="{col["label"]}">{_escape(row["label"])}</tspan>'
                f'<tspan fill="{col["dim"]}">{row["dashes"]}</tspan>'
            )
        elif row["kind"] == "field":
            spans = (
                f'<tspan fill="{col["label"]}">{_escape(row["label"])}</tspan>'
                f'<tspan fill="{col["dim"]}">{row["dots"]}</tspan>'
                f'<tspan fill="{col["value"]}">{_escape(row["value"])}</tspan>'
            )
        elif row["kind"] == "loc":
            spans = f'<tspan fill="{col["label"]}">{_escape(row["label"])}</tspan> '
            spans += "".join(f'<tspan fill="{col[c]}">{_escape(t)}</tspan>' for t, c in row["parts"])
        elif row["kind"] == "footer":
            spans = f'<tspan fill="{col["footer"]}">{_escape(row["text"])}</tspan>'
        elif row["kind"] == "spacer":
            spans = f'<tspan fill="{col["dim"]}">.</tspan>'

        if spans:
            elements.append(
                f'<text x="{info_x}" y="{y}" '
                f'font-family="Consolas, Menlo, monospace" font-size="{font_size}">{spans}</text>'
            )

    return f'''<svg xmlns="http://www.w3.org/2000/svg" width="{round(width)}" height="{round(height)}">
  <rect width="100%" height="100%" rx="12" fill="{bg}" />
  {"".join(elements)}
</svg>'''


def main():
    overview = get_user_overview()
    commits = get_total_commits()
    contributed = get_contributed_repos(overview["owned_repos"])
    additions, deletions = get_lines_of_code(overview["owned_repos"] + contributed)

    stats = {
        "repos": overview["repos"],
        "contributed": len(contributed),
        "stars": overview["stars"],
        "followers": overview["followers"],
        "commits": commits,
        "additions": additions,
        "deletions": deletions,
    }
    art_grid = image_to_art(AVATAR_PATH)
    info_rows = build_info_rows(stats)

    dark = render_svg(art_grid, info_rows, bg="#0d1117", theme="dark")
    light = render_svg(art_grid, info_rows, bg="#ffffff", theme="light")

    with open("dark_mode.svg", "w", encoding="utf-8") as f:
        f.write(dark)
    with open("light_mode.svg", "w", encoding="utf-8") as f:
        f.write(light)

    print("SVGs gerados com sucesso.")


if __name__ == "__main__":
    main()
