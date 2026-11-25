#!/usr/bin/env python3
"""
Gera o README.md (documentação, com a prévia do perfil de EXAMPLE) e os SVGs da
prévia em assets/example/.

Uso:
    pip install fonttools
    python tools/build.py

O texto vira contorno (path) dentro dos SVGs, então as fontes aparecem iguais
em qualquer navegador, sem depender de nada instalado. Por isso, para mudar
qualquer texto, edite o dicionário EXAMPLE e rode o script de novo.

Marcação dentro dos textos:
    [i:texto]  item / palavra-chave   (verde)
    [l:texto]  local                  (vermelho)
    [y:texto]  destaque               (amarelo)
"""
import re
from pathlib import Path
from xml.sax.saxutils import escape

from fontTools.ttLib import TTFont
from fontTools.pens.svgPathPen import SVGPathPen
from fontTools.pens.transformPen import TransformPen

# ═══════════════════════════════ CONTEÚDO ═══════════════════════════════

# Perfil de exemplo (fictício): é o que aparece no README.md e em assets/example/.
# Para fazer o seu, troque os dados aqui pelos seus e rode o script.
EXAMPLE = {
    "name": "Wren Halloway",
    "greeting": "Well met! I'm Wren, an ML engineer at the [l:Lantern Observatory], "
                "teaching [i:neural nets] to read the night sky.",
    "hearts": {"full": 3, "empty": 1, "bonus": 1},
    "stamina": 0.4,  # deadline week

    "inventory": [
        {"label": "Weapons", "tab_image": "tab-weapons.png", "items": [
            {"glyph": "Py", "icon": "py", "name": "Python", "selected": True, "kind": "Main weapon",
             "description": "A trusty serpent staff. Casts [i:NumPy] and [i:PyTorch] "
                            "spells, and summons a [y:Jupyter] familiar on request."},
            {"glyph": "Pt", "icon": "pytorch", "name": "PyTorch"},
            {"glyph": "Rs", "icon": "rust", "name": "Rust"},
            {"glyph": "Pg", "icon": "postgres", "name": "PostgreSQL"},
            {"glyph": "Nx", "icon": "nix", "name": "NixOS"},
            {"glyph": "Dk", "icon": "docker", "name": "Docker"},
            {"glyph": "Vi", "icon": "neovim", "name": "Neovim"},
        ]},
    ],

    "quests": [
        {"kind": "Main quest", "where": "Current role", "title": "ML Engineer", "link": "https://example.com/lantern-observatory",
         "text": "Teaching [i:neural nets] to read the night sky at the [l:Lantern Observatory].",
         "status": "In progress", "selected": True},
        {"kind": "Main quest", "title": "B.S. in Astrophysics", "link": "https://example.com/duskwater-university",
         "text": "Graduated from [l:Duskwater University] with a thesis on mapping faint stars.",
         "status": "Complete"},
        {"kind": "Main quest", "where": "Former role",
         "title": "Star Cartographer at Northwind Survey Guild", "link": "https://example.com/northwind-guild",
         "link_label": "Former Star Cartographer",
         "text": "Charted the northern skies for the [l:Northwind Survey Guild], one constellation at a time.",
         "status": "Complete"},
    ],

}

# ═══════════════════════════════ ESTILO ═══════════════════════════════

C = {
    "page": "#66645D",
    "card": "#292825",            # rgba(0,0,0,.6) sobre #66645D, opaco para funcionar no tema claro
    "sheikah_bg": "#101827",      # rgba(10,20,40,.8) sobre o card
    "modal": "#141412",
    "text": "#FFFEFF",
    "tan": "#E2DED3",
    "yellow": "#E2D146",
    "red": "#F15050",
    "green": "#6BDECC",
    "muted": "#E9E1D1@0.6",
    "blue": "#3CD3FC",
    "gold": "#FCC413",
    "sheikah_yellow": "#FFE460",
    "heart": "#F1362F",
    "heart_empty": "#363930",
    "heart_bonus": "#FFE465",
    "stamina": "#6CF07A",
    "stamina_used": "#1F4A2A",
}
MARK = {"i": C["green"], "l": C["red"], "y": C["yellow"]}
STATUS = {"Complete": C["sheikah_yellow"], "In progress": C["blue"], "Ongoing": C["blue"]}

ROOT = Path(__file__).resolve().parent
OUT = ROOT.parent / "assets"
FONTS = ROOT / "fonts"

# ═══════════════════════════════ TEXTO → PATH ═══════════════════════════════


class Font:
    def __init__(self, file):
        tt = TTFont(FONTS / file)
        self.gs = tt.getGlyphSet()
        self.cmap = tt.getBestCmap()
        self.upm = tt["head"].unitsPerEm
        self.adv = tt["hmtx"].metrics

    def _g(self, ch):
        return self.cmap.get(ord(ch)) or self.cmap[ord("?")]

    def width(self, text, size, spacing=0.0):
        w = sum(self.adv[self._g(c)][0] for c in text) * size / self.upm
        return w + spacing * max(len(text) - 1, 0)

    def d(self, text, size, x, y, spacing=0.0):
        s = size / self.upm
        pen = SVGPathPen(self.gs, ntos=lambda v: ("%.1f" % v).rstrip("0").rstrip("."))
        for c in text:
            g = self._g(c)
            self.gs[g].draw(TransformPen(pen, (s, 0, 0, -s, x, y)))
            x += self.adv[g][0] * s + spacing
        return pen.getCommands()


TITLE = Font("cinzel-latin-400-normal.woff")     # Hylia Serif não tem licença clara; Cinzel é o fallback da spec
BODY = Font("roboto-latin-500-italic.woff")
BOLD = Font("roboto-latin-700-italic.woff")


def paint(color):
    if "@" in color:
        c, a = color.split("@")
        return f'fill="{c}" fill-opacity="{a}"'
    return f'fill="{color}"'


def text(font, s, size, x, y, color, anchor="start", spacing=0.0):
    w = font.width(s, size, spacing)
    x -= {"start": 0, "middle": w / 2, "end": w}[anchor]
    return f'<path {paint(color)} d="{font.d(s, size, x, y, spacing)}"/>'


def runs(s, default):
    out, pos = [], 0
    for m in re.finditer(r"\[([ily]):([^\]]+)\]", s):
        if m.start() > pos:
            out.append((s[pos:m.start()], default))
        out.append((m.group(2), MARK[m.group(1)]))
        pos = m.end()
    if pos < len(s):
        out.append((s[pos:], default))
    return out


def plain(s):
    return re.sub(r"\[[ily]:([^\]]+)\]", r"\1", s)


def wrap(font, s, size, maxw, default):
    """Quebra texto com marcação em linhas; cada palavra guarda os pedaços coloridos."""
    words, cur = [], []
    for chunk, color in runs(s, default):
        for i, part in enumerate(chunk.split(" ")):
            if i > 0 and cur:
                words.append(cur)
                cur = []
            if part:
                cur.append((part, color))
    if cur:
        words.append(cur)
    space = font.width(" ", size)
    lines, line, lw = [], [], 0.0
    for w in words:
        ww = sum(font.width(p, size) for p, _ in w)
        if line and lw + space + ww > maxw:
            lines.append(line)
            line, lw = [w], ww
        else:
            lw += (space if line else 0) + ww
            line.append(w)
    if line:
        lines.append(line)
    return lines


def draw_lines(font, lines, size, x, y, lh, anchor="start"):
    space = font.width(" ", size)
    out = []
    for n, line in enumerate(lines):
        total = sum(sum(font.width(p, size) for p, _ in w) for w in line) + space * (len(line) - 1)
        cx = x - {"start": 0, "middle": total / 2, "end": total}[anchor]
        for w in line:
            for part, color in w:
                out.append(f'<path {paint(color)} d="{font.d(part, size, cx, y + n * lh)}"/>')
                cx += font.width(part, size)
            cx += space
    return "".join(out)


def fit(font, s, size, maxw, minimum=12):
    while size > minimum and font.width(s, size) > maxw:
        size -= 0.5
    return size

# ═══════════════════════════════ PEÇAS ═══════════════════════════════

DEFS = f"""
<linearGradient id="goldLine" x1="0" x2="1"><stop offset="0" stop-color="{C['gold']}" stop-opacity="0"/><stop offset=".5" stop-color="{C['gold']}"/><stop offset="1" stop-color="{C['gold']}" stop-opacity="0"/></linearGradient>
<linearGradient id="blueLine" x1="0" x2="1"><stop offset="0" stop-color="{C['blue']}" stop-opacity="0"/><stop offset=".5" stop-color="{C['blue']}"/><stop offset="1" stop-color="{C['blue']}" stop-opacity="0"/></linearGradient>
<radialGradient id="vignette" cx=".5" cy=".42" r=".75"><stop offset=".5" stop-color="#000" stop-opacity="0"/><stop offset="1" stop-color="#000" stop-opacity=".42"/></radialGradient>
<filter id="glowGold" x="-30%" y="-30%" width="160%" height="160%"><feDropShadow dx="0" dy="0" stdDeviation="3" flood-color="#FFB800"/><feDropShadow dx="0" dy="0" stdDeviation="4" flood-color="#FFDB7E" flood-opacity=".8"/><feDropShadow dx="0" dy="0" stdDeviation="5" flood-color="#FFB904" flood-opacity=".6"/></filter>
<filter id="glowSelect" x="-30%" y="-30%" width="160%" height="160%"><feDropShadow dx="0" dy="0" stdDeviation="6" flood-color="#E3E3C8" flood-opacity=".8"/></filter>
<filter id="glowSheikah" x="-10%" y="-30%" width="120%" height="160%"><feDropShadow dx="0" dy="0" stdDeviation="5" flood-color="#4FC0FF" flood-opacity=".9"/><feDropShadow dx="0" dy="1" stdDeviation="5.5" flood-color="#0A8DD7" flood-opacity=".8"/></filter>
<filter id="glowTan" x="-10%" y="-40%" width="120%" height="180%"><feDropShadow dx="0" dy="0" stdDeviation="10" flood-color="#000"/><feDropShadow dx="0" dy="0" stdDeviation="7" flood-color="#E2DED3" flood-opacity=".7"/></filter>
<filter id="glowGreen" x="-50%" y="-50%" width="200%" height="200%"><feDropShadow dx="0" dy="0" stdDeviation="2.5" flood-color="#13FF59" flood-opacity=".6"/></filter>
<linearGradient id="menuBg" x1="0" y1="0" x2="0" y2="1"><stop offset="0" stop-opacity=".78"/><stop offset=".15" stop-opacity=".58"/><stop offset=".5" stop-opacity=".46"/><stop offset=".85" stop-opacity=".58"/><stop offset="1" stop-opacity=".78"/></linearGradient>
<radialGradient id="menuEdge" cx=".5" cy=".5" r=".72"><stop offset=".6" stop-opacity="0"/><stop offset="1" stop-opacity=".3"/></radialGradient>
<radialGradient id="showcase" cx=".5" cy=".5" r=".5"><stop offset="0" stop-color="#FFFBE6" stop-opacity=".22"/><stop offset="1" stop-color="#FFFBE6" stop-opacity="0"/></radialGradient>
<filter id="glowPing" x="-200%" y="-200%" width="500%" height="500%"><feDropShadow dx="0" dy="0" stdDeviation="2.5" flood-color="#FFD84A" flood-opacity=".9"/><feDropShadow dx="0" dy="0" stdDeviation="5" flood-color="#FFB904" flood-opacity=".5"/></filter>
<filter id="glowBorder" x="-10%" y="-60%" width="120%" height="220%"><feDropShadow dx="0" dy="0" stdDeviation="2.5" flood-color="#FFF6D0" flood-opacity=".85"/><feDropShadow dx="0" dy="0" stdDeviation="6" flood-color="#E3E3C8" flood-opacity=".55"/></filter>
<filter id="inkDark" color-interpolation-filters="sRGB"><feColorMatrix type="matrix" values="0 0 0 0 .114  0 0 0 0 .114  0 0 0 0 .102  0 0 0 1 0"/></filter>
<filter id="inkTan" color-interpolation-filters="sRGB"><feColorMatrix type="matrix" values="0 0 0 0 .886  0 0 0 0 .871  0 0 0 0 .827  0 0 0 .55 0"/></filter>
<filter id="soft" x="-20%" y="-20%" width="140%" height="140%"><feGaussianBlur stdDeviation="3.5"/></filter>
"""

_ids = [0]


def uid(prefix):
    _ids[0] += 1
    return f"{prefix}{_ids[0]}"


def svg(w, h, body, title):
    return (f'<svg xmlns="http://www.w3.org/2000/svg" width="{w}" height="{h}" '
            f'viewBox="0 0 {w} {h}" role="img"><title>{escape(title)}</title>'
            f'<defs>{DEFS}</defs>{body}</svg>\n')


def frame(x, y, w, h, fill, selected=False, inner="#E2DED3", inner_alpha=0.3, glow=None):
    """A estrutura de borda dupla: fundo com raio 4, borda interna a 3px com raio 2."""
    out = []
    if selected:
        out.append(f'<rect x="{x}" y="{y}" width="{w}" height="{h}" rx="4" {paint(fill)} filter="url(#glowSelect)"/>')
    elif glow:
        out.append(f'<rect x="{x}" y="{y}" width="{w}" height="{h}" rx="4" {paint(fill)} filter="url(#{glow})"/>')
    out.append(f'<rect x="{x}" y="{y}" width="{w}" height="{h}" rx="4" {paint(fill)}/>')
    if selected:
        cid = uid("clip")
        out.append(f'<clipPath id="{cid}"><rect x="{x}" y="{y}" width="{w}" height="{h}" rx="4"/></clipPath>'
                   f'<rect x="{x}" y="{y}" width="{w}" height="{h}" rx="4" fill="none" stroke="#F6E798" '
                   f'stroke-opacity=".55" stroke-width="12" filter="url(#soft)" clip-path="url(#{cid})"/>')
        inner_alpha = 0.6
    out.append(f'<rect x="{x + 3.5}" y="{y + 3.5}" width="{w - 7}" height="{h - 7}" rx="2" fill="none" '
               f'stroke="{inner}" stroke-opacity="{inner_alpha}"/>')
    return "".join(out)


def diamond(cx, cy, r, color):
    return f'<rect x="{cx - r}" y="{cy - r}" width="{2 * r}" height="{2 * r}" fill="{color}" transform="rotate(45 {cx} {cy})"/>'


# Forma e cor do coração vêm do SVG em assets/ (path único, 16.2 x 12.6).
_heart_svg = (OUT / "Herzcontainer_-_The_Legend_of_Zelda_BotW,_TotK.svg").read_text(encoding="utf-8")
HEART = re.search(r'<path d="([^"]+)"', _heart_svg).group(1)
C["heart"] = re.search(r'fill="(#[0-9a-fA-F]{3,6})"', _heart_svg).group(1)
HEART_SCALE = 0.95  # ~15 x 12 px, nos cantos do menu


def heart(x, y, color, scale=HEART_SCALE):
    return (f'<path transform="translate({x} {y}) scale({scale})" d="{HEART}" fill="{color}" '
            f'stroke="#1D1D1A" stroke-width="{1.5 / scale:.3f}" stroke-linejoin="round"/>')


def stamina(cx, cy, frac, outer=15, hole=4.5):
    """Roda grossa estilo BotW: anel verde claro com furo pequeno; a parte gasta fica
    verde-escuro, começando no topo e avançando no sentido horário."""
    r, sw = (outer + hole) / 2, outer - hole
    circ = 2 * 3.14159265 * r
    used = circ * (1 - frac)
    ring = f'cx="{cx}" cy="{cy}" r="{r}" fill="none" stroke-width="{sw}" transform="rotate(-90 {cx} {cy})"'
    # Arcos sem sobreposição: se um ficasse por baixo do outro, o antialiasing
    # vazaria a cor de baixo nas bordas.
    out = ''
    if used > 0:
        out += f'<circle {ring} stroke="{C["stamina_used"]}" stroke-dasharray="{used:.2f} {circ:.2f}"/>'
    if frac > 0:
        out += (f'<circle {ring} stroke="{C["stamina"]}" stroke-dasharray="{circ - used:.2f} {circ:.2f}" '
                f'stroke-dashoffset="{-used:.2f}"/>')
    return out


def blink_arrow(cx, top):
    return (f'<polygon points="{cx - 9},{top} {cx + 9},{top} {cx},{top + 10}" fill="{C["tan"]}">'
            f'<animate attributeName="opacity" values="1;0" dur="1.2s" calcMode="discrete" repeatCount="indefinite"/>'
            f'</polygon>')

# ═══════════════════════════════ IMAGENS ═══════════════════════════════


def build_hero(p):
    W = 800
    box_x, box_w, box_top = 40, 720, 16   # o nome sobe ~6px acima da caixa
    size, lh = 28, 35
    lines = wrap(BOLD, p["greeting"], size, box_w - 128, C["text"])
    first = box_top + 58
    last = first + (len(lines) - 1) * lh
    arrow_top = last + 18
    box_h = arrow_top + 10 + 20 - box_top
    H = box_top + box_h + 16

    body = (f'<rect x="{box_x}" y="{box_top}" width="{box_w}" height="{box_h}" rx="{min(90, box_h / 2)}" fill="#000" fill-opacity=".5"/>'
            + text(BODY, p["name"], 26, box_x + 60, box_top + 12, C["tan"])
            + draw_lines(BOLD, lines, size, box_x + 64, first, lh)
            + blink_arrow(W / 2, arrow_top))
    return svg(W, H, body, f'{p["name"]}: {plain(p["greeting"])}')


def badge(cx, cy, letter, r=8):
    """Botão redondo de controle (L, R, A, B...)."""
    return (f'<circle cx="{cx}" cy="{cy}" r="{r}" fill="{C["tan"]}"/>'
            + text(BOLD, letter, r * 1.25, cx, cy + r * 0.45, "#1D1D1A", "middle"))


# ─────────────── menu (inventário, diário de missões, perfil) ───────────────

MENU_W = 800
QUEST_WHERE = "#C9DD5B"   # verde-amarelado das legendas no diário de missões


def hint_bar(y, hints):
    """Linha + dicas de botões alinhadas à direita: [(rótulo, letra), ...] da direita p/ esquerda."""
    out = [f'<rect x="20" y="{y}" width="{MENU_W - 40}" height="1" fill="{C["tan"]}" fill-opacity=".18"/>']
    hx = MENU_W - 30
    for label, letter in hints:
        out.append(badge(hx, y + 22, letter) + text(BODY, label, 13, hx - 14, y + 27, C["text"], "end"))
        hx -= 30 + BODY.width(label, 13) + 14
    return "".join(out)


def menu_title(title):
    return text(BOLD, title, 24, MENU_W / 2, 38, C["text"], "middle")


def menu_sides(left, right, page, pages):
    """Vizinhos com L/R e os pontinhos de página (ficam parados nas trocas)."""
    W = MENU_W
    out = []
    for k in range(pages):
        dx = (k - (pages - 1) / 2) * 8
        out.append(f'<circle cx="{W / 2 + dx}" cy="50" r="1.6" fill="{C["tan"]}" '
                   f'fill-opacity="{1 if k == page else .4}"/>')
    for side, letter, label in ((-1, "L", left), (1, "R", right)):
        if label:
            tx = W / 2 + side * 160
            out.append(badge(tx, 18, letter, 7) + text(BODY, label, 13, tx, 42, C["tan"], "middle"))
    return "".join(out)


def menu_chrome(p, H):
    """Fundo, corações e roda de stamina: o que não muda entre as telas."""
    W = MENU_W
    # Fundo translúcido em preto neutro (como o menu do jogo escurecendo o mundo por trás):
    # o que aparece atrás é a própria página do GitHub, clara ou escura.
    out = [f'<rect width="{W}" height="{H}" rx="6" fill="url(#menuBg)"/>'
           f'<rect width="{W}" height="{H}" rx="6" fill="url(#menuEdge)"/>'
           f'<rect x="20" y="62" width="{W - 40}" height="1" fill="#fff" fill-opacity=".14"/>']
    x = 22
    for kind, n in (("heart", p["hearts"]["full"]), ("heart_empty", p["hearts"]["empty"]),
                    ("heart_bonus", p["hearts"]["bonus"])):
        for _ in range(n):
            out.append(heart(x, 20, C[kind]))
            x += 18
    # roda no canto direito, centrada na altura dos corações (topo 20 + 12/2)
    out.append(stamina(W - 24 - 15, 20 + 12.6 * HEART_SCALE / 2, p["stamina"]))
    return "".join(out)


TABS_Y = 112      # centro dos ícones de categoria
CONTENT_Y = 158   # onde começam a grade do inventário e a lista de missões


def tab_image(file, cx, cy, size, ink):
    """Ícone de aba a partir de uma imagem em tools/icons/ (embutida em base64), recolorida
    com o filtro `ink` (inkDark na aba selecionada, inkTan nas outras)."""
    import base64
    data = base64.b64encode((ICONS / file).read_bytes()).decode()
    mime = "image/svg+xml" if file.endswith(".svg") else "image/png"
    return (f'<image x="{cx - size / 2}" y="{cy - size / 2}" width="{size}" height="{size}" '
            f'href="data:{mime};base64,{data}" filter="url(#{ink})"/>')


def category_tabs(labels, sel, cx0, ty=TABS_Y, icons=None, images=None):
    """Fileira de ícones de categoria: nome da selecionada em cima, linha fina embaixo com ◀ R ▶."""
    out, tab_gap = [], 46
    t0 = cx0 - (len(labels) - 1) * tab_gap / 2
    ly = ty + 25
    half = max((len(labels) - 1) * tab_gap / 2 + 34, 70)
    out.append(f'<rect x="{cx0 - half}" y="{ly - .5}" width="{2 * half}" height="1" fill="#fff" fill-opacity=".3"/>')
    for i, label in enumerate(labels):
        cx = t0 + i * tab_gap
        icon = (icons or {}).get(label) or label[:1]
        img = (images or {}).get(label)
        if i == sel:
            out.append(text(BODY, label, 13, cx, ty - 28, C["text"], "middle")
                       + f'<circle cx="{cx}" cy="{ty}" r="15" fill="{C["tan"]}"/>'
                       + (tab_image(img, cx, ty, 18, "inkDark") if img else
                          text(BOLD, icon, 14, cx, ty + 5, "#1D1D1A", "middle"))
                       + f'<rect x="{cx - 24}" y="{ly - 1}" width="48" height="2" fill="{C["tan"]}"/>'
                       + f'<polygon points="{cx - 22},{ly} {cx - 15},{ly - 4} {cx - 15},{ly + 4}" fill="{C["tan"]}"/>'
                       + f'<polygon points="{cx + 22},{ly} {cx + 15},{ly - 4} {cx + 15},{ly + 4}" fill="{C["tan"]}"/>'
                       + badge(cx, ly, "R", 6))
        else:
            out.append(tab_image(img, cx, ty, 18, "inkTan") if img else
                       text(BOLD, icon, 14, cx, ty + 5, C["tan"] + "@0.55", "middle"))
    return "".join(out)


ICONS = ROOT / "icons"   # ícones de https://skillicons.dev (MIT, ver tools/icons/LICENSE.txt)


def has_icon(name):
    """True se existe tools/icons/<name>.svg; sem arquivo, o item mostra o glyph."""
    if name and not (ICONS / f"{name}.svg").exists():
        print(f"aviso: tools/icons/{name}.svg não existe; usando o glyph")
        return False
    return bool(name)


def item_icon(name, x, y, size):
    """Desenha o ícone tools/icons/<name>.svg num quadrado (x, y, size). Os ids internos
    (gradientes, clipPaths) ganham um prefixo único para não colidir quando o mesmo
    ícone aparece mais de uma vez na imagem."""
    svg_text = (ICONS / f"{name}.svg").read_text(encoding="utf-8").strip()
    pre = uid("ic")
    svg_text = re.sub(r'id="([^"]+)"', lambda m: f'id="{pre}-{m.group(1)}"', svg_text)
    svg_text = re.sub(r'url\(#([^)]+)\)', lambda m: f'url(#{pre}-{m.group(1)})', svg_text)
    return re.sub(r'^<svg[^>]*>', f'<svg x="{x}" y="{y}" width="{size}" height="{size}" viewBox="0 0 256 256" fill="none">',
                  svg_text, count=1)


def showcase(cx, cy, rad, label, icon=None):
    return (f'<circle cx="{cx}" cy="{cy}" r="{rad * 1.6}" fill="url(#showcase)"/>'
            f'<circle cx="{cx}" cy="{cy}" r="{rad}" fill="#000" fill-opacity=".35" '
            f'stroke="{C["tan"]}" stroke-opacity=".45"/>'
            + (item_icon(icon, cx - rad * .6, cy - rad * .6, rad * 1.2) if icon else
               text(BOLD, label, fit(BOLD, label, rad * .8, rad * 1.5), cx, cy + rad * .28, C["tan"], "middle")))


def inventory_screen(p):
    """Conteúdo da tela de inventário. Devolve (svg, y do fim do conteúdo)."""
    rows = p["inventory"]
    cols, slot, gap, gx = 5, 62, 8, 48
    gw = cols * slot + (cols - 1) * gap
    out = []

    grid, sel_row, selected = [], 0, None
    for ri, row in enumerate(rows):
        items = row["items"]
        for k in range(0, max(len(items), 1), cols):
            grid.append(items[k:k + cols])
        for it in items:
            if it.get("selected"):
                selected, sel_row = it, ri
    while len(grid) < 3:
        grid.append([])

    out.append(category_tabs([r["label"] for r in rows], sel_row, gx + gw / 2,
                             icons={r["label"]: r.get("icon") for r in rows},
                             images={r["label"]: r.get("tab_image") for r in rows}))

    gy = CONTENT_Y
    for r, items in enumerate(grid):
        for c in range(cols):
            sx, sy = gx + c * (slot + gap), gy + r * (slot + gap)
            it = items[c] if c < len(items) else None
            sel = it is not None and it is selected
            if sel:
                out.append(f'<rect x="{sx}" y="{sy}" width="{slot}" height="{slot}" rx="3" fill="#000" '
                           f'fill-opacity=".6" filter="url(#glowSelect)"/>')
            out.append(f'<rect x="{sx + .5}" y="{sy + .5}" width="{slot - 1}" height="{slot - 1}" rx="3" '
                       f'fill="#000" fill-opacity="{.45 if it else .2}" '
                       + (f'stroke="#FFFBE6" stroke-width="2"/>' if sel else
                          f'stroke="#fff" stroke-opacity="{.3 if it else .1}"/>'))
            if it:
                if has_icon(it.get("icon")):
                    out.append(item_icon(it["icon"], sx + slot / 2 - 17, sy + 6, 34))
                else:
                    out.append(text(BOLD, it["glyph"], fit(BOLD, it["glyph"], 20, slot - 14), sx + slot / 2, sy + 33,
                                    C["tan"], "middle"))
                out.append(text(BODY, it["name"], fit(BODY, it["name"], 10, slot - 8, 7), sx + slot / 2, sy + 51,
                                  C["muted"], "middle"))
    gb = gy + len(grid) * (slot + gap) - gap
    my = (gy + gb) / 2
    for ax, d in ((gx - 26, -1), (gx + gw + 26, 1)):
        out.append(f'<polygon points="{ax + d * 8},{my} {ax - d * 4},{my - 12} {ax - d * 4},{my + 12}" fill="#fff" fill-opacity=".9"/>')

    px, pw = 448, 330
    if selected:
        desc = wrap(BODY, selected.get("description", ""), 14, pw - 32, C["text"])
        ph = 92 + max(len(desc), 1) * 19
        py = gb - ph
        kind = selected.get("kind", "")
        kw = BODY.width(kind, 11) + 16
        out.append(f'<rect x="{px}" y="{py}" width="{pw}" height="{ph}" rx="3" fill="#000" fill-opacity=".5" '
                   f'stroke="#fff" stroke-opacity=".16"/>'
                   + text(BOLD, selected["name"], 20, px + 16, py + 32, C["text"])
                   + (f'<rect x="{px + 16}" y="{py + 42}" width="{kw}" height="18" rx="2" fill="{C["red"]}" '
                      f'fill-opacity=".18" stroke="{C["red"]}" stroke-opacity=".8"/>'
                      + text(BODY, kind, 11, px + 24, py + 55, C["text"]) if kind else "")
                   + draw_lines(BODY, desc, 14, px + 16, py + 86, 19))
        top, bottom = 70, py - 10
        rad = min(52, (bottom - top) / 2 - 4)
        if rad > 20:
            icon = selected.get("icon") if has_icon(selected.get("icon")) else None
            out.append(showcase(px + pw / 2, (top + bottom) / 2, rad, selected["glyph"], icon))
    return "".join(out), gb


def quest_bubble(x, y, color="#FFFEFF"):
    """Ícone de balão de fala com três pontinhos."""
    return (f'<rect x="{x}" y="{y}" width="20" height="14" rx="5" fill="{color}"/>'
            f'<polygon points="{x + 4},{y + 12} {x + 4},{y + 19} {x + 10},{y + 13}" fill="{color}"/>'
            + "".join(f'<circle cx="{x + 5 + k * 5}" cy="{y + 7}" r="1.4" fill="#1D1D1A"/>' for k in range(3)))


def quest_tab(x, y, w, h, dot=True, tw=24):
    """Aba cinza na ponta direita da linha da missão (com pontinho escuro, se dot)."""
    tx = x + w - tw - 3
    return (f'<rect x="{tx}" y="{y + 3}" width="{tw}" height="{h - 6}" fill="#fff" fill-opacity=".16"/>'
            + (f'<circle cx="{tx + tw / 2}" cy="{y + h / 2}" r="1.5" fill="#000" fill-opacity=".75"/>' if dot else ""))


def corner_ticks(x, y, w, h, size=8, out=2.5):
    """Triângulos claros nos quatro cantos da seleção, com o ângulo reto no canto e a ponta para dentro."""
    tris = []
    for cx, cy, dx, dy in ((x, y, 1, 1), (x + w, y, -1, 1), (x, y + h, 1, -1), (x + w, y + h, -1, -1)):
        ox, oy = cx - dx * out, cy - dy * out
        tris.append(f'{ox},{oy} {ox + dx * size},{oy} {ox},{oy + dy * size}')
    return (f'<g fill="#FFFBE6" filter="url(#glowSelect)">'
            + "".join(f'<polygon points="{t}"/>' for t in tris) + '</g>')


def quest_ping(cx, cy):
    """Marcador da missão acompanhada: anel amarelo vazado (o brilho aparece por dentro), ponto central."""
    return (f'<circle cx="{cx}" cy="{cy}" r="5.5" fill="none" stroke="{C["sheikah_yellow"]}" '
            f'stroke-width="2" filter="url(#glowPing)"/>'
            f'<circle cx="{cx}" cy="{cy}" r="2" fill="{C["sheikah_yellow"]}"/>')


def short_link(url, size, maxw):
    """Link sem https://, cortado com … se não couber."""
    s = re.sub(r"^https?://", "", url).rstrip("/")
    if BODY.width(s, size) <= maxw:
        return s
    while s and BODY.width(s + "…", size) > maxw:
        s = s[:-1]
    return s + "…"


def quest_legend(q):
    return q["kind"] + (f' - {q["where"]}' if q.get("where") else "")


def quests_screen(p):
    """Diário de missões: lista de missões à esquerda e detalhes da selecionada à direita."""
    quests = p["quests"]
    selected = next((q for q in quests if q.get("selected")), None) \
        or next((q for q in quests if q.get("status") != "Complete"), quests[0])
    kinds = list(dict.fromkeys(q["kind"] for q in quests))
    out = []

    lx, lw, rh, rgap, ly0 = 48, 352, 44, 8, CONTENT_Y
    # título da aba sem o "Main" ("Main quest" → "Quests"); as legendas das linhas continuam com ele
    tab = {k: re.sub(r"^main\s+", "", k, flags=re.I).capitalize() + "s" for k in kinds}
    out.append(category_tabs([tab[k] for k in kinds], kinds.index(selected["kind"]), lx + lw / 2,
                             icons={tab[k]: ("!" if k.lower().startswith("main") else "?") for k in kinds}))
    bottom = CONTENT_Y + 3 * (rh + rgap) + 46   # mesma altura da grade do inventário
    visible = quests[:max(1, (bottom - ly0 + rgap) // (rh + rgap))]
    for i, q in enumerate(visible):
        y = ly0 + i * (rh + rgap)
        sel = q is selected
        row = []
        if sel:
            # Mesmo fundo preto das outras linhas e, por cima, a borda com brilho próprio: a luz
            # sai da linha para os dois lados (para fora e um pouco para dentro da caixa), como no jogo.
            row.append(f'<rect x="{lx + .5}" y="{y + .5}" width="{lw - 1}" height="{rh - 1}" rx="1" fill="#000" '
                       f'fill-opacity=".82"/>'
                       f'<rect x="{lx + .5}" y="{y + .5}" width="{lw - 1}" height="{rh - 1}" rx="1" fill="none" '
                       f'stroke="#FFFBE6" stroke-width="2" filter="url(#glowBorder)"/>')
            row.append(corner_ticks(lx, y, lw, rh))
            row.append(quest_tab(lx, y, lw, rh, dot=False))
            row.append(quest_ping(lx + lw - 15, y + rh / 2))   # anel por cima da aba
        else:
            # não selecionada (como no jogo): caixa quase preta com borda fina clara e, na ponta
            # direita, uma aba cinza com um pontinho no meio
            row.append(f'<rect x="{lx + .5}" y="{y + .5}" width="{lw - 1}" height="{rh - 1}" rx="1" fill="#000" '
                       f'fill-opacity=".82" stroke="#fff" stroke-opacity=".28"/>'
                       + quest_tab(lx, y, lw, rh))
        row.append(quest_bubble(lx + 12, y + 12))
        row.append(text(BOLD, q["title"], fit(BOLD, q["title"], 16, lw - 64), lx + 42, y + 21, C["text"]))
        row.append(text(BODY, quest_legend(q), 11, lx + 42, y + 36, QUEST_WHERE))
        out.append("".join(row))

    px, py, pw = 432, 70, 346
    ph = bottom - py
    status = selected.get("status", "")
    desc = wrap(BODY, selected["text"], 15, pw - 36, C["text"])
    scol = STATUS.get(status, C["muted"])
    link = selected.get("link", "")
    out.append(f'<rect x="{px}" y="{py}" width="{pw}" height="{ph}" rx="3" fill="#000" fill-opacity=".5" '
               f'stroke="#fff" stroke-opacity=".16"/>'
               + text(BOLD, selected["title"], fit(BOLD, selected["title"], 20, pw - 36), px + 18, py + 36, C["text"])
               + f'<circle cx="{px + 25}" cy="{py + 56}" r="7" fill="{C["red"]}"/>'
               + text(BOLD, "!", 11, px + 25, py + 60, C["text"], "middle")
               + text(BODY, status, 12, px + 38, py + 60, scol)
               + text(BODY, quest_legend(selected), 12, px + pw - 18, py + 60, QUEST_WHERE, "end")
               + f'<rect x="{px + 18}" y="{py + 72}" width="{pw - 36}" height="1" fill="{C["tan"]}" fill-opacity=".2"/>'
               + draw_lines(BODY, desc, 15, px + 18, py + 100, 21)
               + (text(BODY, short_link(link, 12, pw - 36), 12, px + 18, py + ph - 18, C["muted"]) if link else ""))
    return "".join(out), bottom


MENU_SCREENS = [
    ("Adventure Log", quests_screen, [("Select", "A"), ("Back", "B")]),
    ("Inventory", inventory_screen, [("Select", "A"), ("Back", "B"), ("Sort", "Y")]),
]


def saving_spinner(x, y):
    dots = "".join(f'<circle cx="{x + 7 * __import__("math").cos(k * 0.785)}" cy="{y + 7 * __import__("math").sin(k * 0.785)}" '
                   f'r="1.6" fill="{C["tan"]}" fill-opacity="{.25 + k * .1:.2f}"/>' for k in range(8))
    return (f'<g>{dots}<animateTransform attributeName="transform" type="rotate" from="0 {x} {y}" to="360 {x} {y}" '
            f'dur="1.6s" repeatCount="indefinite"/></g>' + text(BODY, "Saving", 13, x + 16, y + 5, C["tan"]))


def screen_parts(i, content, bottom):
    """(parte parada, parte que desliza) de uma tela: só o título e o conteúdo deslizam."""
    names = [s[0] for s in MENU_SCREENS]
    n = len(names)
    title, _, hints = MENU_SCREENS[i]
    # Sem dar a volta: a primeira aba só tem R, a última só tem L (como no jogo).
    left = names[i - 1] if i > 0 else None
    right = names[i + 1] if i < n - 1 else None
    still = menu_sides(left, right, i, n) + hint_bar(bottom + 22, hints)
    return still, menu_title(title) + content


def build_menu(p, hold=5.0, swap=0.5, slide=90):
    """Menu animado como apertar R/L no jogo: a cada `hold` segundos o título e o conteúdo
    da tela atual saem por um lado enquanto os da próxima entram pelo outro (com fade).
    Fundo, corações, stamina e rodapé ficam parados; L/R, pontinhos e dicas fazem só fade.
    SMIL funciona dentro de <img> no GitHub; sem animação, fica parado na primeira tela."""
    screens = [fn(p) for _, fn, _ in MENU_SCREENS]
    bottom = max(b for _, b in screens)
    H = bottom + 66
    n, total = len(screens), hold * len(screens)
    out = [menu_chrome(p, H), saving_spinner(34, H - 22)]
    for i, (content, _) in enumerate(screens):
        start, end = i * hold, (i + 1) * hold
        # Posição: desliza durante toda a janela de troca [fim - swap, fim].
        # Opacidade: a tela que sai some na 1ª metade e a que entra aparece na 2ª,
        # assim as duas quase não se sobrepõem.
        h = swap / 2
        # Avança com R (sai pela esquerda, a próxima entra pela direita); da última volta para a
        # primeira com L, no sentido contrário (sai pela direita, a primeira entra pela esquerda).
        if i == 0:
            move = [(0, 0), (end - swap, 0), (end, -slide), (total - swap, -slide), (total, 0)]
            fade = [(0, 1), (end - swap, 1), (end - h, 0), (total - h, 0), (total, 1)]
        elif i == n - 1:
            move = [(0, slide), (start - swap, slide), (start, 0), (total - swap, 0), (total, slide)]
            fade = [(0, 0), (start - h, 0), (start, 1), (total - swap, 1), (total - h, 0), (total, 0)]
        else:
            move = [(0, slide), (start - swap, slide), (start, 0), (end - swap, 0), (end, -slide), (total, -slide)]
            fade = [(0, 0), (start - h, 0), (start, 1), (end - swap, 1), (end - h, 0), (total, 0)]

        def anim(keys):
            kt = ";".join(f"{t / total:.4f}" for t, _ in keys)
            ease = ";".join(["0.25 0.1 0.25 1"] * (len(keys) - 1))
            return (f'dur="{total}s" repeatCount="indefinite" keyTimes="{kt}" '
                    f'calcMode="spline" keySplines="{ease}"')

        still, moving = screen_parts(i, content, bottom)
        out.append(f'<g opacity="{1 if i == 0 else 0}">'
                   f'<animate attributeName="opacity" {anim(fade)} values="{";".join(str(v) for _, v in fade)}"/>'
                   + still
                   + f'<g><animateTransform attributeName="transform" type="translate" {anim(move)} '
                     f'values="{";".join(f"{x} 0" for _, x in move)}"/>{moving}</g>'
                   + '</g>')
    titles = " / ".join(s[0] for s in MENU_SCREENS)
    return svg(MENU_W, H, "".join(out), f'{p["name"]}: game menu cycling through {titles}')


MENU_TABS = {"menu-quests": 0, "menu-inventory": 1}

# True: o perfil mostra o menu animado. False: mostra as três abas paradas, uma embaixo da outra.
MENU_ANIMATED = True


def build_menu_tab(p, i):
    """Uma aba do menu sozinha, parada (sem animação), na mesma altura do menu animado."""
    screens = [fn(p) for _, fn, _ in MENU_SCREENS]
    bottom = max(b for _, b in screens)
    H = bottom + 66
    content, _ = screens[i]
    return svg(MENU_W, H, menu_chrome(p, H) + saving_spinner(34, H - 22)
               + "".join(screen_parts(i, content, bottom)), f'{p["name"]}: {MENU_SCREENS[i][0]}')


def build_divider():
    W, H = 800, 40
    body = (f'<rect x="20" y="19.5" width="340" height="1" fill="url(#goldLine)"/>'
            f'<rect x="440" y="19.5" width="340" height="1" fill="url(#goldLine)"/>'
            f'<rect x="392" y="12" width="16" height="16" fill="none" stroke="{C["gold"]}" transform="rotate(45 400 20)"/>'
            + diamond(400, 20, 3.5, C["gold"]) + diamond(372, 20, 2.5, C["gold"]) + diamond(428, 20, 2.5, C["gold"]))
    return svg(W, H, body, "")

# ═══════════════════════════════ README ═══════════════════════════════


def img(file, alt, width="100%", base="assets"):
    return f'<img src="./{base}/{file}.svg" width="{width}" alt="{escape(alt, {chr(34): "&quot;"})}">'


def linked(file, alt, link, width="100%", base="assets"):
    tag = img(file, alt, width, base)
    return f'<a href="{link}">{tag}</a>' if link else tag


def build_profile(p, base="assets"):
    # O menu (animado ou em abas paradas) substitui as seções antigas. Como uma imagem
    # não tem links por região, os links dos cartões e missões vão numa linha de texto abaixo.
    # "link_label" (opcional) troca o texto do link na linha abaixo do menu
    links = [(q.get("link_label", q["title"]), q["link"]) for q in p["quests"] if q.get("link")]
    link_line = (f'<p align="center"><sub>{" · ".join(f"<a href=\"{u}\">{escape(t)}</a>" for t, u in links)}</sub></p>\n\n'
                 if links else "")
    alt = (f'{p["name"]}: {plain(p["greeting"])} '
           f'Inventory: {", ".join(it["name"] for r in p["inventory"] for it in r["items"])}. '
           f'Quests: {"; ".join(q["title"] + " (" + q.get("status", "") + ")" for q in p["quests"])}.')
    footer = f'\n<p align="center"><sub><i>{escape(p["footer"])}</i></sub></p>\n' if p.get("footer") else ""
    if MENU_ANIMATED:
        menu = f'<p align="center">{img("menu", alt, base=base)}</p>'
    else:
        menu = "\n\n".join(f'<p align="center">{img(name, MENU_SCREENS[i][0], base=base)}</p>'
                             for name, i in MENU_TABS.items())
    return f"""<p align="center">{img("hero", f'{p["name"]}: {plain(p["greeting"])}', base=base)}</p>

<p align="center">{img("divider", "", base=base)}</p>

{menu}

{link_line}<p align="center">{img("divider", "", base=base)}</p>
{footer}"""


GENERATED = "<!-- Gerado por tools/build.py. Não edite à mão: edite o script e rode de novo. -->\n\n"


def DESCRIPTIONS(p, files):
    """Uma linha por SVG gerado, na ordem em que main() os cria."""
    known = {"hero": "The greeting dialogue box",
             "menu": "Animated game menu that switches between Adventure Log and Inventory",
             "menu-inventory": "Menu tab Inventory, as a still image",
             "menu-quests": "Menu tab Adventure Log, as a still image",
             "divider": "Ornamental divider, used under the intro and at the bottom"}
    return [(n, known[n]) for n in files]


def build_docs(p, files, profile):
    """README.md do repositório: explica o projeto e mostra o perfil recém-gerado."""
    outputs = "\n".join(f"| `{name}.svg` | {desc} |" for name, desc in files)
    marks = "\n".join(f"| `[{k}:text]` | {label} | `{C[c]}` |" for k, label, c in
                      (("i", "item / keyword", "green"), ("l", "place", "red"), ("y", "highlight", "yellow")))
    h = p["hearts"]
    return GENERATED + f"""# GitHub profile builder

A Python script that renders a GitHub profile README as a set of SVG images styled after an
open-world adventure game: a dialogue box with your greeting, then a game menu with your
hearts and stamina wheel, an Adventure Log (your roles and degrees, as quests) and an
Inventory (your tools).

The **Result** section below is the real output of [`tools/build.py`](tools/build.py), rendered
from the placeholder `EXAMPLE` profile. This README is generated by the same script, so the
preview is always up to date.

## Result

{profile}
---

## How it works

GitHub strips CSS, fonts and scripts from READMEs, but it renders SVG images. `build.py`
draws every section as a standalone SVG and converts all text to vector outlines
(`<path>`) with [fontTools](https://github.com/fonttools/fonttools), using the fonts in
[`tools/fonts/`](tools/fonts). The images look the same in any browser, on light and dark
themes, with nothing installed on the viewer's side.

The menu's "tabs" are an SVG animation (SMIL): GitHub plays it inside the `<img>`, so each
screen slides into the next every few seconds without any JavaScript. Viewers that don't
run SVG animation see the first screen. Each tab is also written as a still image
(`menu-quests.svg`, `menu-inventory.svg`); set `MENU_ANIMATED = False` in
`build.py` to show those stacked instead of the animation.

Because the text is baked into the images, **never edit the SVGs by hand**: change the
`EXAMPLE` dictionary at the top of `build.py` and run the script again.

## Quick start

```sh
python3 -m venv venv
venv/bin/pip install fonttools
venv/bin/python tools/build.py
```

This writes this document (`README.md`) and the profile images in `assets/example/`,
both built from the `EXAMPLE` dictionary:

| File | Contents |
| --- | --- |
{outputs}

## Customizing

Replace the data in the `EXAMPLE` dictionary in [`tools/build.py`](tools/build.py) with your
own and run the script. These are the keys:

| Key | What it controls | Example value |
| --- | --- | --- |
| `name`, `greeting` | The intro dialogue box | `{escape(p["name"])}` |
| `hearts` | Hearts in the menu's top-left: `full`, `empty` and yellow `bonus` | {h["full"]} full, {h["empty"]} empty, {h["bonus"]} bonus |
| `stamina` | Fill of the stamina wheel in the menu's top-right, from 0 to 1 | `{p["stamina"]}` |
| `inventory` | Item categories (one tab each) and their items, 5 per row; the `selected` item fills the showcase and description panel. A category's tab shows `tab_image` (an image in `tools/icons/`) or a one-letter `icon` | {len(p["inventory"])} {"category" if len(p["inventory"]) == 1 else "categories"}, {sum(len(r["items"]) for r in p["inventory"])} items |
| `quests` | Adventure Log entries (your roles and degrees), in list order; `selected` picks the one shown in the panel, `where` extends the legend, `link` adds it to the link line under the menu (`link_label` changes its text), `status` is `Complete`, `In progress` or `Ongoing` | {len(p["quests"])} entries |
| `footer` | Optional line at the very bottom | |

Text fields accept inline color markup:

| Markup | Meaning | Color |
| --- | --- | --- |
{marks}

Colors live in the `C` dictionary. The heart shape and its color come from the heart SVG
in `assets/`, so replacing that file changes every heart on the next build.

## Icons

Icons live in [`tools/icons/`](tools/icons) and are drawn straight into the SVGs, so the build
never needs the internet. There are two kinds:

- **Item icons** (the colored tiles in the inventory slots). Set an item's `icon` to the file
  name without `.svg`, for example `{{"glyph": "Py", "icon": "py", "name": "Python"}}`.
  If the file doesn't exist or `icon` is missing, the slot shows the item's `glyph` text instead.
- **Tab images** (the symbol inside a category's round tab, like the sword on "Weapons"). Set the
  category's `tab_image` to a file in `tools/icons/`, for example `"tab_image": "tab-weapons.png"`.
  Use a **white** shape on a transparent background (PNG or SVG): the build recolors it dark on
  the selected tab and light gray on the others. Keep the file small (around 96×96 px is plenty).

### Adding a new item icon

Item icons come from [skillicons.dev](https://skillicons.dev) (see the list of IDs there).

1. Download the icon, using the dark theme:

   ```sh
   curl -s "https://skillicons.dev/icons?i=vscode&theme=dark" -o vscode-download.svg
   ```

2. Strip the wrapper. The downloaded file wraps the real icon in an extra `<svg>` and `<g>`:

   ```xml
   <svg width="48" height="48" viewBox="0 0 256 256" ...>        <- remove
       <g transform="translate(0, 0)">                          <- remove
         <svg xmlns="http://www.w3.org/2000/svg" width="256" ...>  <- keep from here
           ...
         </svg>                                                  <- ...to here
       </g>                                                      <- remove
   </svg>                                                        <- remove
   ```

   `build.py` expects only the inner `<svg>...</svg>` (256×256). You can delete the outer
   lines by hand in any editor, or run this to do it:

   ```sh
   python3 -c "import re, sys; t = open(sys.argv[1]).read(); open(sys.argv[2], 'w').write(re.search(r'<g transform=\\"translate\\(0, 0\\)\\">\\s*(<svg.*?</svg>)\\s*</g>', t, re.S).group(1) + '\\n')" vscode-download.svg tools/icons/vscode.svg
   ```

3. Use it in your profile: `{{"glyph": "VS", "icon": "vscode", "name": "VS Code"}}`, then run
   `venv/bin/python tools/build.py`.

## Using it as your GitHub profile

GitHub shows a profile README from a public repository named exactly like your username.
After building with your data, copy the `assets/example/` folder into that repository and
paste the HTML of the [Result](#result) section (the `<p align="center">` blocks) into its
`README.md`. The image paths are relative (`./assets/example/...`), so they keep working as long
as the folder keeps the same path.

## Project layout

```
assets/              the heart shape used as input
assets/example/      generated SVGs for the README preview
tools/build.py       the example profile, styles and the generator
tools/fonts/         Cinzel and Roboto, with their licenses
tools/icons/         item icons and tab images
README.md            generated documentation (this file)
```

## Credits

- Fonts: [Cinzel](https://github.com/NDISCOVER/Cinzel) and [Roboto](https://github.com/googlefonts/roboto-classic),
  both under the SIL Open Font License (see `tools/fonts/`).
- Item icons: [Skill Icons](https://github.com/tandpfun/skill-icons) by tandpfun, MIT License
  (see `tools/icons/` and the [Icons](#icons) section).
- The HUD style is a fan tribute to *The Legend of Zelda: Breath of the Wild / Tears of the Kingdom*.
  This project is not affiliated with or endorsed by Nintendo.
"""


def build_all(p, out):
    files = {
        "hero": build_hero(p),
        "menu": build_menu(p),
        **{name: build_menu_tab(p, i) for name, i in MENU_TABS.items()},
        "divider": build_divider(),
    }
    out.mkdir(parents=True, exist_ok=True)
    for name, content in files.items():
        (out / f"{name}.svg").write_text(content, encoding="utf-8")
    return files


def main():
    # Exemplo: README.md + assets/example/.
    files = build_all(EXAMPLE, OUT / "example")
    preview = build_profile(EXAMPLE, "assets/example")
    (ROOT.parent / "README.md").write_text(build_docs(EXAMPLE, DESCRIPTIONS(EXAMPLE, files), preview),
                                           encoding="utf-8")
    print("README.md e assets/example/ (exemplo) atualizados")


if __name__ == "__main__":
    main()
