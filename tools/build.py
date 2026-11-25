#!/usr/bin/env python3
"""
Gera os SVGs do perfil, o PROFILE.md (a página do perfil) e o README.md (a
documentação do projeto, que já mostra o perfil gerado) a partir do bloco PROFILE.

Uso:
    pip install fonttools
    python tools/build.py

O texto vira contorno (path) dentro dos SVGs, então as fontes aparecem iguais
em qualquer navegador, sem depender de nada instalado. Por isso, para mudar
qualquer texto, edite PROFILE e rode o script de novo em vez de editar os SVGs.

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

PROFILE = {
    "name": "Eduardo E. Traunig",
    "greeting": "Hi! I'm an MSc student at [l:MALTA Lab] ([l:PUCRS]), "
                "working with [i:AI] and [i:ML].",
    "hearts": {"full": 3, "empty": 0, "bonus": 1},
    "stamina": 0.66,  # 0 a 1

    "cards": [
        {"file": "card-degree", "label": "Degree", "title": "B.S. in Computer Science",
         "sub": "[l:PUCRS]", "link": "https://portal.pucrs.br/"},
        {"file": "card-msc", "label": "Current quest", "title": "MSc Student",
         "sub": "[l:MALTA Lab], [l:PUCRS]", "selected": True,
         "link": "https://portal.pucrs.br/pesquisa/estruturas-de-pesquisa/#labs-nucleos-grupos"},
        {"file": "card-pet", "label": "Former role", "title": "Scientific Researcher",
         "sub": "[l:PET-Inf]", "link": "https://pet-inf.github.io/pet-site/"},
    ],

    "inventory": [
        {"label": "Main weapons", "items": [
            {"glyph": "Py", "name": "Python", "selected": True, "kind": "Main weapon",
             "description": "My main weapon for research. Most of my [i:ML] experiments "
                            "are forged here, side by side with [i:PyTorch]."},
            {"glyph": "Pt", "name": "PyTorch"},
            {"glyph": "Jv", "name": "Java"},
            {"glyph": "C++", "name": "C++"},
        ]},
        {"label": "Tools", "items": [
            {"glyph": "Ar", "name": "Arch Linux"},
            {"glyph": "Gh", "name": "GitHub"},
            {"glyph": ">_", "name": "Bash"},
        ]},
    ],

    # Troque pelos seus repositórios. status: "Complete", "In progress" ou "Not started"
    "quests": [
        {"file": "quest-1", "kind": "Main quest", "title": "repo-name",
         "text": "One line about what the project does and what it is built with.",
         "status": "Complete", "link": "https://github.com/SEU-USUARIO/repo-name"},
        {"file": "quest-2", "kind": "Main quest", "title": "another-repo",
         "text": "One line about what the project does and what it is built with.",
         "status": "In progress", "link": "https://github.com/SEU-USUARIO/another-repo"},
        {"file": "quest-side", "kind": "Side quest", "title": "The endless Linux setup",
         "text": "When I'm not doing research, I'm tinkering with my [i:Arch] setup or gaming.",
         "status": "Ongoing"},
    ],

    "contact": {
        "email": "e.enes@edu.pucrs.br",
        "title": "Send Eduardo a message?",
        "confirm": "Send message",
        "cancel": "Maybe later",
    },

    "footer": "Thanks for visiting, traveler.",
}

# Perfil fictício usado só na prévia do README.md (assets/example/), para que a
# documentação não exponha os dados reais de PROFILE.
EXAMPLE = {
    "name": "Wren Halloway",
    "greeting": "Well met! I'm Wren, an ML engineer at the [l:Lantern Observatory], "
                "teaching [i:neural nets] to read the night sky.",
    "hearts": {"full": 3, "empty": 1, "bonus": 1},
    "stamina": 0.4,  # deadline week
    "gems": 4096,     # contador no canto do inventário (opcional)

    "cards": [
        {"file": "card-degree", "label": "Degree", "title": "B.S. in Astrophysics",
         "sub": "[l:Duskwater University]"},
        {"file": "card-current", "label": "Current quest", "title": "ML Engineer",
         "sub": "[l:Lantern Observatory]", "selected": True},
        {"file": "card-former", "label": "Former role", "title": "Star Cartographer",
         "sub": "[l:Northwind Survey Guild]"},
    ],

    "inventory": [
        {"label": "Main weapons", "icon": "W", "items": [
            {"glyph": "Py", "name": "Python", "selected": True, "kind": "Main weapon",
             "description": "A trusty serpent staff. Casts [i:NumPy] and [i:PyTorch] "
                            "spells, and summons a [y:Jupyter] familiar on request."},
            {"glyph": "Jx", "name": "JAX"},
            {"glyph": "Rs", "name": "Rust"},
            {"glyph": "SQL", "name": "SQL"},
        ]},
        {"label": "Tools", "items": [
            {"glyph": "Nx", "name": "NixOS"},
            {"glyph": "Dk", "name": "Docker"},
            {"glyph": "Vi", "name": "Neovim"},
        ]},
    ],

    "quests": [
        {"file": "quest-1", "kind": "Main quest", "title": "constellation-net",
         "text": "A [i:CNN] that spots constellations in blurry backyard telescope photos.",
         "status": "Complete"},
        {"file": "quest-2", "kind": "Main quest", "title": "comet-tail",
         "text": "Streaming anomaly detection for sky surveys, written in [i:Rust].",
         "status": "In progress"},
        {"file": "quest-side", "kind": "Side quest", "title": "The sourdough alchemist",
         "text": "Keeping a 4-year-old starter named [y:Kepler] alive between experiments.",
         "status": "Ongoing"},
    ],

    "contact": {
        "email": "wren@example.com",
        "title": "Send Wren a raven?",
        "confirm": "Send raven",
        "cancel": "Maybe later",
    },

    "footer": "May your gradients never vanish, traveler.",
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
<radialGradient id="menuBg" cx=".62" cy=".45" r=".8"><stop offset="0" stop-color="#3B4A3A"/><stop offset=".6" stop-color="#1F2A21"/><stop offset="1" stop-color="#0E130F"/></radialGradient>
<radialGradient id="showcase" cx=".5" cy=".5" r=".5"><stop offset="0" stop-color="#FFFBE6" stop-opacity=".22"/><stop offset="1" stop-color="#FFFBE6" stop-opacity="0"/></radialGradient>
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


def scene(w, h):
    return (f'<rect width="{w}" height="{h}" rx="6" fill="{C["page"]}"/>'
            f'<rect width="{w}" height="{h}" rx="6" fill="url(#vignette)"/>')


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
HEART_SCALE = 1.8  # ~29 x 23 px


def heart(x, y, color, scale=HEART_SCALE):
    return (f'<path transform="translate({x} {y}) scale({scale})" d="{HEART}" fill="{color}" '
            f'stroke="#1D1D1A" stroke-width="{1.5 / scale:.3f}" stroke-linejoin="round"/>')


def stamina(cx, cy, frac):
    """Roda grossa estilo BotW: anel verde claro com furo pequeno; a parte gasta fica
    verde-escuro, começando no topo e avançando no sentido horário."""
    outer, hole = 27, 8
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
    box_x, box_w, box_top = 40, 720, 132
    size, lh = 28, 35
    lines = wrap(BOLD, p["greeting"], size, box_w - 128, C["text"])
    first = box_top + 58
    last = first + (len(lines) - 1) * lh
    arrow_top = last + 18
    box_h = arrow_top + 10 + 20 - box_top
    H = box_top + box_h + 26

    hearts = []
    x = 28
    for kind, n in (("heart", p["hearts"]["full"]), ("heart_empty", p["hearts"]["empty"]),
                    ("heart_bonus", p["hearts"]["bonus"])):
        for _ in range(n):
            hearts.append(heart(x, 26, C[kind]))
            x += 34

    body = ("".join(hearts) + stamina(W - 54, 50, p["stamina"])
            + f'<rect x="{box_x}" y="{box_top}" width="{box_w}" height="{box_h}" rx="{min(90, box_h / 2)}" fill="#000" fill-opacity=".5"/>'
            + text(BODY, p["name"], 26, box_x + 60, box_top + 12, C["tan"])
            + draw_lines(BOLD, lines, size, box_x + 64, first, lh)
            + blink_arrow(W / 2, arrow_top))
    return svg(W, H, body, f'{p["name"]}: {plain(p["greeting"])}')


def build_title(label):
    W, H = 800, 60
    size, spacing = 26, 2
    tw = TITLE.width(label, size, spacing)
    l, r = W / 2 - tw / 2 - 22, W / 2 + tw / 2 + 22
    body = (frame(0, 0, W, H, C["card"])
            + f'<rect x="40" y="29.5" width="{l - 48}" height="1" fill="url(#goldLine)"/>'
            + f'<rect x="{r + 8}" y="29.5" width="{W - 48 - r}" height="1" fill="url(#goldLine)"/>'
            + diamond(l, 30, 3.5, C["gold"]) + diamond(r, 30, 3.5, C["gold"])
            + text(TITLE, label, size, W / 2, 39, C["tan"], "middle", spacing))
    return svg(W, H, body, label)


def build_cards(cards):
    W, H, m = 284, 164, 12
    size = min(fit(TITLE, c["title"], 21, 220, 14) for c in cards)
    out = {}
    for c in cards:
        sub = wrap(BODY, c["sub"], 15, 220, C["muted"])
        body = (frame(m, m, W - 2 * m, H - 2 * m, C["card"], c.get("selected", False))
                + text(BODY, c["label"], 14, m + 22, m + 38, C["yellow"])
                + text(TITLE, c["title"], size, m + 22, m + 78, C["tan"])
                + draw_lines(BODY, sub, 15, m + 22, m + 108, 20))
        out[c["file"]] = svg(W, H, body, f'{c["label"]}: {c["title"]}, {plain(c["sub"])}')
    return out


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
    """Fundo, corações e contador de gemas: o que não muda entre as telas."""
    W = MENU_W
    out = [f'<rect width="{W}" height="{H}" rx="6" fill="url(#menuBg)"/>'
           f'<rect width="{W}" height="{H}" rx="6" fill="url(#vignette)"/>']
    x = 22
    for kind, n in (("heart", p["hearts"]["full"]), ("heart_empty", p["hearts"]["empty"]),
                    ("heart_bonus", p["hearts"]["bonus"])):
        for _ in range(n):
            out.append(heart(x, 20, C[kind], 0.95))
            x += 18
    if p.get("gems") is not None:
        val = f'{p["gems"]:,}'
        vx = W - 24 - BOLD.width(val, 18)
        out.append(f'<polygon points="{vx - 18},{24} {vx - 12},{17} {vx - 6},{24} {vx - 12},{39}" fill="#3DDC6E" '
                   f'stroke="#B8FFC9" stroke-width=".8"/>' + text(BOLD, val, 18, W - 24, 38, C["text"], "end"))
    return "".join(out)


def category_tabs(labels, sel, cx0, ty=102, icons=None):
    """Fileira de ícones de categoria; a selecionada ganha círculo, nome em cima e ◀ R ▶."""
    out, tab_gap = [], 46
    t0 = cx0 - (len(labels) - 1) * tab_gap / 2
    for i, label in enumerate(labels):
        cx = t0 + i * tab_gap
        icon = (icons or {}).get(label) or label[:1]
        if i == sel:
            out.append(text(BODY, label, 13, cx, 74, C["text"], "middle")
                       + f'<circle cx="{cx}" cy="{ty}" r="15" fill="{C["tan"]}"/>'
                       + text(BOLD, icon, 14, cx, ty + 5, "#1D1D1A", "middle")
                       + f'<polygon points="{cx - 22},{ty + 25} {cx - 16},{ty + 21} {cx - 16},{ty + 29}" fill="{C["tan"]}"/>'
                       + f'<polygon points="{cx + 22},{ty + 25} {cx + 16},{ty + 21} {cx + 16},{ty + 29}" fill="{C["tan"]}"/>'
                       + badge(cx, ty + 25, "R", 6))
        else:
            out.append(text(BOLD, icon, 14, cx, ty + 5, C["tan"] + "@0.55", "middle"))
    return "".join(out)


def showcase(cx, cy, rad, label):
    return (f'<circle cx="{cx}" cy="{cy}" r="{rad * 1.6}" fill="url(#showcase)"/>'
            f'<circle cx="{cx}" cy="{cy}" r="{rad}" fill="#000" fill-opacity=".35" '
            f'stroke="{C["tan"]}" stroke-opacity=".45"/>'
            + text(BOLD, label, fit(BOLD, label, rad * .8, rad * 1.5), cx, cy + rad * .28, C["tan"], "middle"))


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
                             icons={r["label"]: r.get("icon") for r in rows}))

    gy = 142
    for r, items in enumerate(grid):
        for c in range(cols):
            sx, sy = gx + c * (slot + gap), gy + r * (slot + gap)
            it = items[c] if c < len(items) else None
            sel = it is not None and it is selected
            if sel:
                out.append(f'<rect x="{sx}" y="{sy}" width="{slot}" height="{slot}" rx="3" fill="#000" '
                           f'fill-opacity=".6" filter="url(#glowSelect)"/>')
            out.append(f'<rect x="{sx + .5}" y="{sy + .5}" width="{slot - 1}" height="{slot - 1}" rx="3" '
                       f'fill="#000" fill-opacity="{.6 if it else .3}" '
                       + (f'stroke="#FFFBE6" stroke-width="2"/>' if sel else
                          f'stroke="{C["tan"]}" stroke-opacity="{.3 if it else .12}"/>'))
            if it:
                out.append(text(BOLD, it["glyph"], fit(BOLD, it["glyph"], 20, slot - 14), sx + slot / 2, sy + 33,
                                C["tan"], "middle")
                           + text(BODY, it["name"], fit(BODY, it["name"], 10, slot - 8, 7), sx + slot / 2, sy + 51,
                                  C["muted"], "middle"))
    gb = gy + len(grid) * (slot + gap) - gap
    my = (gy + gb) / 2
    for ax, d in ((gx - 26, -1), (gx + gw + 26, 1)):
        out.append(f'<polygon points="{ax + d * 8},{my} {ax - d * 4},{my - 12} {ax - d * 4},{my + 12}" fill="#F6EFD8"/>')

    px, pw = 448, 330
    if selected:
        desc = wrap(BODY, selected.get("description", ""), 14, pw - 32, C["text"])
        ph = 92 + max(len(desc), 1) * 19
        py = gb - ph
        kind = selected.get("kind", "")
        kw = BODY.width(kind, 11) + 16
        out.append(f'<rect x="{px}" y="{py}" width="{pw}" height="{ph}" rx="3" fill="#0B0E0B" fill-opacity=".78" '
                   f'stroke="{C["tan"]}" stroke-opacity=".3"/>'
                   + f'<rect x="{px}" y="{py}" width="{pw}" height="1.5" fill="url(#goldLine)"/>'
                   + text(BOLD, selected["name"], 20, px + 16, py + 32, C["text"])
                   + (f'<rect x="{px + 16}" y="{py + 42}" width="{kw}" height="18" rx="2" fill="{C["red"]}" '
                      f'fill-opacity=".18" stroke="{C["red"]}" stroke-opacity=".8"/>'
                      + text(BODY, kind, 11, px + 24, py + 55, C["text"]) if kind else "")
                   + draw_lines(BODY, desc, 14, px + 16, py + 86, 19))
        top, bottom = 70, py - 10
        rad = min(52, (bottom - top) / 2 - 4)
        if rad > 20:
            out.append(showcase(px + pw / 2, (top + bottom) / 2, rad, selected["glyph"]))
    return "".join(out), gb


def quest_bubble(x, y, color="#FFFEFF"):
    """Ícone de balão de fala com três pontinhos."""
    return (f'<rect x="{x}" y="{y}" width="20" height="14" rx="5" fill="{color}"/>'
            f'<polygon points="{x + 4},{y + 12} {x + 4},{y + 19} {x + 10},{y + 13}" fill="{color}"/>'
            + "".join(f'<circle cx="{x + 5 + k * 5}" cy="{y + 7}" r="1.4" fill="#1D1D1A"/>' for k in range(3)))


def quests_screen(p):
    """Diário de missões: lista de missões à esquerda e detalhes da selecionada à direita."""
    quests = p["quests"]
    selected = next((q for q in quests if q.get("selected")), None) \
        or next((q for q in quests if q.get("status") != "Complete"), quests[0])
    kinds = list(dict.fromkeys(q["kind"] for q in quests))
    out = []

    lx, lw, rh, rgap, ly0 = 48, 352, 44, 8, 142
    out.append(category_tabs([k + "s" for k in kinds], kinds.index(selected["kind"]), lx + lw / 2,
                             icons={k + "s": ("!" if k.lower().startswith("main") else "?") for k in kinds}))
    bottom = 344
    visible = quests[:max(1, (bottom - ly0 + rgap) // (rh + rgap))]
    for i, q in enumerate(visible):
        y = ly0 + i * (rh + rgap)
        sel = q is selected
        done = q.get("status") == "Complete" and not sel
        row = []
        if sel:
            row.append(f'<rect x="{lx}" y="{y}" width="{lw}" height="{rh}" rx="3" fill="#000" fill-opacity=".7" '
                       f'filter="url(#glowSelect)"/>')
        row.append(f'<rect x="{lx + .5}" y="{y + .5}" width="{lw - 1}" height="{rh - 1}" rx="3" fill="#000" '
                   f'fill-opacity=".62" '
                   + (f'stroke="#FFFBE6" stroke-width="2"/>' if sel else f'stroke="{C["tan"]}" stroke-opacity=".22"/>'))
        row.append(f'<rect x="{lx + lw - 12}" y="{y + 6}" width="6" height="{rh - 12}" rx="1" fill="{C["tan"]}" '
                   f'fill-opacity=".14"/>')
        if sel:
            row.append(f'<circle cx="{lx + lw - 9}" cy="{y + rh / 2}" r="5" fill="{C["yellow"]}"/>')
        row.append(quest_bubble(lx + 12, y + 12))
        row.append(text(BOLD, q["title"], fit(BOLD, q["title"], 16, lw - 64), lx + 42, y + 21, C["text"]))
        row.append(text(BODY, q.get("where", q["kind"]), 11, lx + 42, y + 36, QUEST_WHERE))
        g = "".join(row)
        out.append(f'<g opacity=".4">{g}</g>' if done else g)

    px, py, pw = 432, 70, 346
    ph = bottom - py
    status = selected.get("status", "")
    desc = wrap(BODY, selected["text"], 15, pw - 36, C["text"])
    scol = STATUS.get(status, C["muted"])
    link = selected.get("link", "")
    out.append(f'<rect x="{px}" y="{py}" width="{pw}" height="{ph}" rx="3" fill="#0B0E0B" fill-opacity=".72" '
               f'stroke="{C["tan"]}" stroke-opacity=".3"/>'
               + text(BOLD, selected["title"], fit(BOLD, selected["title"], 20, pw - 36), px + 18, py + 36, C["text"])
               + f'<circle cx="{px + 25}" cy="{py + 56}" r="7" fill="{C["red"]}"/>'
               + text(BOLD, "!", 11, px + 25, py + 60, C["text"], "middle")
               + text(BODY, status, 12, px + 38, py + 60, scol)
               + text(BODY, selected.get("where", selected["kind"]), 12, px + pw - 18, py + 60, QUEST_WHERE, "end")
               + f'<rect x="{px + 18}" y="{py + 72}" width="{pw - 36}" height="1" fill="{C["tan"]}" fill-opacity=".2"/>'
               + draw_lines(BODY, desc, 15, px + 18, py + 100, 21)
               + (text(BODY, re.sub(r"^https?://", "", link), fit(BODY, re.sub(r"^https?://", "", link), 12, pw - 36),
                       px + 18, py + ph - 18, C["muted"]) if link else ""))
    return "".join(out), bottom


def profile_screen(p):
    """Tela do aventureiro: retrato + saudação à esquerda, cartões empilhados à direita."""
    out = []
    cx = 220
    words = p["name"].split()
    initials = (words[0][:1] + (words[-1][:1] if len(words) > 1 else "")).upper()
    out.append(showcase(cx, 128, 50, initials))
    out.append(text(TITLE, p["name"], fit(TITLE, p["name"], 26, 340), cx, 216, C["tan"], "middle"))
    out.append(f'<rect x="{cx - 120}" y="228" width="240" height="1" fill="url(#goldLine)"/>')
    greet = wrap(BODY, p["greeting"], 15, 340, C["text"])
    out.append(draw_lines(BODY, greet, 15, cx, 256, 21, "middle"))

    cards = p["cards"]
    x, w, top, bottom, gap = 432, 346, 70, 344, 10
    h = (bottom - top - gap * (len(cards) - 1)) / len(cards)
    for i, c in enumerate(cards):
        y = top + i * (h + gap)
        out.append(frame(x, y, w, h, C["card"] + "@0.85" if "@" not in C["card"] else C["card"], c.get("selected", False))
                   + text(BODY, c["label"], 12, x + 20, y + h / 2 - 14, C["yellow"])
                   + text(TITLE, c["title"], fit(TITLE, c["title"], 19, w - 40), x + 20, y + h / 2 + 8, C["tan"])
                   + draw_lines(BODY, wrap(BODY, c["sub"], 13, w - 40, C["muted"])[:1], 13, x + 20, y + h / 2 + 27, 16))
    return "".join(out), bottom


MENU_SCREENS = [
    ("Adventurer", profile_screen, [("Next", "R"), ("Close", "B")]),
    ("Inventory", inventory_screen, [("Select", "A"), ("Back", "B"), ("Sort", "Y")]),
    ("Adventure Log", quests_screen, [("Open", "A"), ("Back", "B")]),
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
    still = menu_sides(names[(i - 1) % n], names[(i + 1) % n], i, n) + hint_bar(bottom + 22, hints)
    return still, menu_title(title) + content


def build_inventory(p):
    content, bottom = inventory_screen(p)
    H = bottom + 66
    names = ", ".join(it["name"] for r in p["inventory"] for it in r["items"])
    return svg(MENU_W, H, menu_chrome(p, H) + "".join(screen_parts(1, content, bottom)), f"Inventory: {names}")


def build_menu(p, hold=5.0, swap=0.5, slide=90):
    """Menu animado como apertar R no jogo: a cada `hold` segundos o título e o conteúdo
    da tela atual saem para a esquerda enquanto os da próxima entram pela direita (com fade).
    Fundo, corações, gemas e rodapé ficam parados; L/R, pontinhos e dicas fazem só fade.
    SMIL funciona dentro de <img> no GitHub; sem animação, fica parado na primeira tela."""
    screens = [fn(p) for _, fn, _ in MENU_SCREENS]
    bottom = max(b for _, b in screens)
    H = bottom + 66
    n, total = len(screens), hold * len(screens)
    eps = 0.01
    out = [menu_chrome(p, H), saving_spinner(34, H - 22)]
    for i, (content, _) in enumerate(screens):
        start, end = i * hold, (i + 1) * hold
        # Posição: desliza durante toda a janela de troca [fim - swap, fim].
        # Opacidade: a tela que sai some na 1ª metade e a que entra aparece na 2ª,
        # assim as duas quase não se sobrepõem.
        h = swap / 2
        if i == 0:
            move = [(0, 0), (end - swap, 0), (end, -slide), (end + eps, slide), (total - swap, slide), (total, 0)]
            fade = [(0, 1), (end - swap, 1), (end - h, 0), (total - h, 0), (total, 1)]
        elif i == n - 1:
            move = [(0, slide), (start - swap, slide), (start, 0), (total - swap, 0), (total, -slide)]
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


def build_quest(q):
    W, m = 800, 14
    cx, cw = m, W - 2 * m
    desc = wrap(BODY, q["text"], 16, 560, C["text"])
    last = m + 98 + (len(desc) - 1) * 23
    ch = last + 26 - m
    H = ch + 2 * m
    status = q.get("status", "")
    scol = STATUS.get(status, C["muted"])
    body = (frame(cx, m, cw, ch, C["sheikah_bg"], inner=C["blue"], inner_alpha=0.3, glow="glowSheikah")
            + f'<rect x="{cx + cw * .1}" y="{m}" width="{cw * .8}" height="1" fill="url(#blueLine)" opacity=".6"/>'
            + text(BODY, q["kind"], 14, cx + 26, m + 36, C["yellow"])
            + text(TITLE, q["title"], fit(TITLE, q["title"], 22, 520), cx + 26, m + 68, C["tan"])
            + draw_lines(BODY, desc, 16, cx + 26, m + 98, 23))
    if status:
        sw = BODY.width(status, 15)
        body += (diamond(cx + cw - 30 - sw - 12, m + 31, 3.5, scol.split("@")[0])
                 + text(BODY, status, 15, cx + cw - 26, m + 36, scol, "end"))
    return svg(W, H, body, f'{q["kind"]}: {q["title"]}. {plain(q["text"])} {status}')


def build_contact(c):
    W, H, m = 800, 242, 28
    bw, bh, by = 200, 48, 138
    cx1, cx2 = W / 2 - 12 - bw, W / 2 + 12
    body = (f'<rect x="{m}" y="{m}" width="{W - 2 * m}" height="{H - 2 * m}" rx="12" fill="{C["modal"]}" filter="url(#glowTan)"/>'
            + f'<rect x="{m}" y="{m}" width="{W - 2 * m}" height="{H - 2 * m}" rx="12" fill="{C["modal"]}"/>'
            + text(TITLE, c["title"], 22, W / 2, 80, C["tan"], "middle")
            + text(BODY, c["email"], 16, W / 2, 110, C["muted"], "middle")
            + f'<rect x="{cx1}" y="{by}" width="{bw}" height="{bh}" rx="4" fill="#302912" filter="url(#glowGold)"/>'
            + f'<rect x="{cx1 + .5}" y="{by + .5}" width="{bw - 1}" height="{bh - 1}" rx="4" fill="#302912" stroke="{C["gold"]}"/>'
            + text(BOLD, c["confirm"], 18, cx1 + bw / 2, by + 30, C["gold"], "middle")
            + f'<rect x="{cx2 + .5}" y="{by + .5}" width="{bw - 1}" height="{bh - 1}" rx="4" fill="none" stroke="{C["tan"]}" stroke-opacity=".3"/>'
            + text(BODY, c["cancel"], 18, cx2 + bw / 2, by + 30, C["text"], "middle"))
    return svg(W, H, body, f'{c["title"]} {c["email"]}')


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
    # O menu animado substitui as seções Adventurer / Inventory / Quest Log. Como uma imagem
    # não tem links por região, os links dos cartões e missões vão numa linha de texto abaixo.
    links = [(c["title"], c["link"]) for c in p["cards"] if c.get("link")] + \
            [(q["title"], q["link"]) for q in p["quests"] if q.get("link")]
    link_line = (f'<p align="center"><sub>{" · ".join(f"<a href=\"{u}\">{escape(t)}</a>" for t, u in links)}</sub></p>\n\n'
                 if links else "")
    alt = (f'{p["name"]}: {plain(p["greeting"])} '
           f'Cards: {"; ".join(c["title"] + ", " + plain(c["sub"]) for c in p["cards"])}. '
           f'Inventory: {", ".join(it["name"] for r in p["inventory"] for it in r["items"])}. '
           f'Quests: {"; ".join(q["title"] + " (" + q.get("status", "") + ")" for q in p["quests"])}.')
    return f"""<p align="center">{img("hero", f'{p["name"]}: {plain(p["greeting"])}', base=base)}</p>

<p align="center">{img("menu", alt, base=base)}</p>

{link_line}<p align="center">{linked("contact", f'Send a message: {p["contact"]["email"]}', "mailto:" + p["contact"]["email"], base=base)}</p>

<p align="center">{img("divider", "", base=base)}</p>

<p align="center"><sub><i>{escape(p["footer"])}</i></sub></p>
"""


GENERATED = "<!-- Gerado por tools/build.py. Não edite à mão: edite o script e rode de novo. -->\n\n"


TITLES = {"title-adventurer": "Adventurer", "title-inventory": "Inventory", "title-quests": "Quest Log"}


def DESCRIPTIONS(p, files):
    """Uma linha por SVG gerado, na ordem em que main() os cria."""
    known = {"hero": "Hearts, stamina wheel and the greeting dialogue box",
             "inventory": "Inventory menu: category tabs, item grid, showcase and description panel",
             "menu": "Animated game menu that cycles Adventurer → Inventory → Adventure Log (used in the profile)",
             "contact": "\"Send message?\" prompt with the e-mail link",
             "divider": "Ornamental divider above the footer"}
    for c in p["cards"]:
        known[c["file"]] = f'Card: {c["label"]}'
    for q in p["quests"]:
        known[q["file"]] = f'Quest log entry: {q["kind"].lower()} "{q["title"]}"'
    return [(n, known.get(n, f'Section title "{TITLES.get(n, n)}"')) for n in files]


def build_docs(p, files, profile):
    """README.md do repositório: explica o projeto e mostra o perfil recém-gerado."""
    outputs = "\n".join(f"| `assets/{name}.svg` | {desc} |" for name, desc in files)
    marks = "\n".join(f"| `[{k}:text]` | {label} | `{C[c]}` |" for k, label, c in
                      (("i", "item / keyword", "green"), ("l", "place", "red"), ("y", "highlight", "yellow")))
    h = p["hearts"]
    return GENERATED + f"""# GitHub profile builder

A Python script that renders a GitHub profile README as a set of SVG images styled after an
open-world adventure game HUD: hearts and a stamina wheel, a dialogue box, and an animated
game menu that flips between an adventurer page, an inventory and a quest log on its own,
followed by a "send message?" prompt.

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
screen crossfades into the next every few seconds without any JavaScript. Viewers that don't
run SVG animation see the first screen. The standalone section images (cards, inventory,
quests) are still generated, if you prefer a static layout.

Because the text is baked into the images, **never edit the SVGs by hand**: change the
`PROFILE` dictionary at the top of `build.py` and run the script again.

## Quick start

```sh
python3 -m venv venv
venv/bin/pip install fonttools
venv/bin/python tools/build.py
```

This writes:

| File | Contents |
| --- | --- |
{outputs}
| `PROFILE.md` | The profile page built from `PROFILE`, ready to be used as a profile README |
| `assets/example/` | The same images built from `EXAMPLE`, used only by the preview above |
| `README.md` | This document |

## Customizing

Edit `PROFILE` in [`tools/build.py`](tools/build.py). `EXAMPLE` has the same keys and only
feeds the preview in this README:

| Key | What it controls | Example value |
| --- | --- | --- |
| `name`, `greeting` | Dialogue box in the hero | `{escape(p["name"])}` |
| `hearts` | Hearts in the top-left: `full`, `empty` and yellow `bonus` | {h["full"]} full, {h["empty"]} empty, {h["bonus"]} bonus |
| `stamina` | Fill of the stamina wheel, from 0 to 1 | `{p["stamina"]}` |
| `cards` | The three cards under "Adventurer"; `selected` adds a glow | {len(p["cards"])} cards |
| `inventory` | Item categories (tabs) and their items; the `selected` item fills the showcase and description panel. A category can set a one-letter `icon` for its tab | {len(p["inventory"])} categories, {sum(len(r["items"]) for r in p["inventory"])} items |
| `gems` | Optional counter in the inventory's top-right corner | {p.get("gems", "not set")} |
| `quests` | Quest log entries; `status` is `Complete`, `In progress` or `Ongoing` | {len(p["quests"])} quests |
| `contact` | E-mail and button labels of the message prompt | |
| `footer` | Line at the very bottom | |

Text fields accept inline color markup:

| Markup | Meaning | Color |
| --- | --- | --- |
{marks}

Colors live in the `C` dictionary. The heart shape and its color come from the heart SVG
in `assets/`, so replacing that file changes every heart on the next build.

## Using it as your GitHub profile

GitHub shows a profile README from a public repository named exactly like your username.
Copy `PROFILE.md` (renamed to `README.md`) and the `assets/` folder into that repository,
or fork this project into it and point `build.py` to write the profile to `README.md`.

## Project layout

```
assets/          generated SVGs for your profile (plus the heart shape used as input)
assets/example/  generated SVGs for the README preview
tools/build.py   content, styles and the generator
tools/fonts/     Cinzel and Roboto, with their licenses
PROFILE.md       generated profile page
README.md        generated documentation (this file)
```

## Credits

- Fonts: [Cinzel](https://github.com/NDISCOVER/Cinzel) and [Roboto](https://github.com/googlefonts/roboto-classic),
  both under the SIL Open Font License (see `tools/fonts/`).
- The HUD style is a fan tribute to *The Legend of Zelda: Breath of the Wild / Tears of the Kingdom*.
  This project is not affiliated with or endorsed by Nintendo.
"""


def build_all(p, out):
    files = {
        "hero": build_hero(p),
        **{name: build_title(label) for name, label in TITLES.items()},
        "inventory": build_inventory(p),
        "menu": build_menu(p),
        "contact": build_contact(p["contact"]),
        "divider": build_divider(),
        **build_cards(p["cards"]),
        **{q["file"]: build_quest(q) for q in p["quests"]},
    }
    out.mkdir(parents=True, exist_ok=True)
    for name, content in files.items():
        (out / f"{name}.svg").write_text(content, encoding="utf-8")
    return files


def main():
    build_all(PROFILE, OUT)
    (ROOT.parent / "PROFILE.md").write_text(GENERATED + build_profile(PROFILE), encoding="utf-8")

    example = build_all(EXAMPLE, OUT / "example")
    preview = build_profile(EXAMPLE, "assets/example")
    (ROOT.parent / "README.md").write_text(build_docs(EXAMPLE, DESCRIPTIONS(EXAMPLE, example), preview),
                                           encoding="utf-8")
    print(f"PROFILE.md e assets/ (seu perfil), README.md e assets/example/ (exemplo) atualizados")


if __name__ == "__main__":
    main()
