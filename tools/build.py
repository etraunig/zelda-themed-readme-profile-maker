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

    "cards": [
        {"file": "card-degree", "label": "Degree", "title": "B.S. in Astrophysics",
         "sub": "[l:Duskwater University]"},
        {"file": "card-current", "label": "Current quest", "title": "ML Engineer",
         "sub": "[l:Lantern Observatory]", "selected": True},
        {"file": "card-former", "label": "Former role", "title": "Star Cartographer",
         "sub": "[l:Northwind Survey Guild]"},
    ],

    "inventory": [
        {"label": "Main weapons", "items": [
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


def heart(x, y, color):
    return (f'<path transform="translate({x} {y}) scale({HEART_SCALE})" d="{HEART}" fill="{color}" '
            f'stroke="#1D1D1A" stroke-width="{1.5 / HEART_SCALE:.3f}" stroke-linejoin="round"/>')


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


def build_inventory(rows):
    W = 800
    slot, gap, x0 = 84, 18, 32
    y = 40
    parts, selected = [], None
    for row in rows:
        parts.append(text(BODY, row["label"], 15, x0, y, C["muted"]))
        sy = y + 14
        for i, it in enumerate(row["items"]):
            sx = x0 + i * (slot + gap)
            sel = it.get("selected", False)
            selected = it if sel else selected
            parts.append(frame(sx, sy, slot, slot, "#000@0.6", sel))
            parts.append(text(BODY, it["glyph"], 26, sx + slot / 2, sy + 52, C["tan"], "middle"))
            parts.append(text(BODY, it["name"], 13, sx + slot / 2, sy + slot + 20, C["text"], "middle"))
        y = sy + slot + 58
    H = y - 18

    px, py, pw = 470, 54, 298
    ph = H - py - 28
    panel = frame(px, py, pw, ph, "#000@0.6")
    if selected:
        desc = wrap(BODY, selected.get("description", ""), 16, pw - 48, C["text"])
        panel += (text(TITLE, selected["name"], 24, px + 24, py + 44, C["tan"])
                  + text(BODY, selected.get("kind", ""), 14, px + 24, py + 68, C["yellow"])
                  + f'<rect x="{px + 24}" y="{py + 84}" width="{pw - 48}" height="1" fill="url(#goldLine)"/>'
                  + draw_lines(BODY, desc, 16, px + 24, py + 114, 23))
    names = ", ".join(it["name"] for r in rows for it in r["items"])
    return svg(W, H, scene(W, H) + "".join(parts) + panel, f"Inventory: {names}")


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
    cards = "\n".join(linked(c["file"], f'{c["label"]}: {c["title"]}, {plain(c["sub"])}', c.get("link"), "32%", base)
                      for c in p["cards"])
    quest_lines = []
    for q in p["quests"]:
        alt = f'{q["kind"]}: {q["title"]}. {plain(q["text"])}'
        quest_lines.append(f'<p align="center">{linked(q["file"], alt, q.get("link"), base=base)}</p>')
    quests = "\n".join(quest_lines)
    return f"""<p align="center">{img("hero", f'{p["name"]}: {plain(p["greeting"])}', base=base)}</p>

<p align="center">{img("title-adventurer", "Adventurer", base=base)}</p>

<p align="center">
{cards}
</p>

<p align="center">{img("title-inventory", "Inventory", base=base)}</p>

<p align="center">{img("inventory", "Inventory: " + ", ".join(it["name"] for r in p["inventory"] for it in r["items"]), base=base)}</p>

<p align="center">{img("title-quests", "Quest Log", base=base)}</p>

{quests}

<p align="center">{linked("contact", f'Send a message: {p["contact"]["email"]}', "mailto:" + p["contact"]["email"], base=base)}</p>

<p align="center">{img("divider", "", base=base)}</p>

<p align="center"><sub><i>{escape(p["footer"])}</i></sub></p>
"""


GENERATED = "<!-- Gerado por tools/build.py. Não edite à mão: edite o script e rode de novo. -->\n\n"


TITLES = {"title-adventurer": "Adventurer", "title-inventory": "Inventory", "title-quests": "Quest Log"}


def DESCRIPTIONS(p, files):
    """Uma linha por SVG gerado, na ordem em que main() os cria."""
    known = {"hero": "Hearts, stamina wheel and the greeting dialogue box",
             "inventory": "Item grid with a detail panel for the selected item",
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
open-world adventure game HUD: hearts and a stamina wheel, a dialogue box, item cards,
an inventory grid, a quest log and a "send message?" prompt.

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
| `inventory` | Rows of item slots; the `selected` item fills the side panel | {sum(len(r["items"]) for r in p["inventory"])} items |
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
        "inventory": build_inventory(p["inventory"]),
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
