#!/usr/bin/env python3
"""Generates the animated ASCII-art SVGs used in the profile README.

Everything is drawn with monospace glyphs on a character grid, coloured with the
@balijepallipavan "Cyanotype" palette. Animations are glyph-based (colour / opacity
changes on characters), so the art stays aligned whatever monospace font the
viewer's browser picks.

    python3 assets/generate.py      # rewrites assets/*.svg
"""
import os
import random
from html import escape

HERE = os.path.dirname(os.path.abspath(__file__))

# palette (tokens from the design system)
BG, SURFACE, INK, INK_MUTED = "#E8EDF2", "#F3F6F9", "#10243F", "#46566E"
COBALT, MIST, BORDER = "#1F4E8C", "#7E9CC4", "#C3CEDA"

FS, LH = 14, 18          # font size, line height (px)
CW = FS * 0.602          # nominal monospace advance, used only for canvas sizing
FONT = ("ui-monospace, 'JetBrains Mono', 'Cascadia Mono', SFMono-Regular, Menlo, "
        "Monaco, 'DejaVu Sans Mono', 'Liberation Mono', 'Courier New', monospace")


# --------------------------------------------------------------------------- grid
class Canvas:
    def __init__(self, rows, cols):
        self.rows, self.cols = rows, cols
        self.g = [[(" ", None) for _ in range(cols)] for _ in range(rows)]

    def put(self, r, c, text, cls, opaque=False):
        for i, ch in enumerate(text):
            if 0 <= r < self.rows and 0 <= c + i < self.cols and (ch != " " or opaque):
                self.g[r][c + i] = (ch, cls)

    def art(self, r, c, lines, cls, masks=None, palette=None):
        """Draw multi-line art; optional per-char mask letters map to classes."""
        for i, line in enumerate(lines):
            mask = masks[i] if masks and i < len(masks) else ""
            for j, ch in enumerate(line):
                k = mask[j] if j < len(mask) else "."
                self.put(r + i, c + j, ch, palette.get(k, cls) if palette else cls)

    def svg(self, x0, y0):
        out = []
        for r, row in enumerate(self.g):
            if all(ch == " " for ch, _ in row):
                continue
            last = max(i for i, (ch, _) in enumerate(row) if ch != " ")
            runs = []
            for ch, cls in row[: last + 1]:
                key = cls if ch != " " else None
                if runs and runs[-1][0] == key:
                    runs[-1][1] += ch
                else:
                    runs.append([key, ch])
            parts = "".join(
                escape(t) if c is None else f'<tspan class="{c}">{escape(t)}</tspan>'
                for c, t in runs)
            out.append(f'<text x="{x0}" y="{y0 + r * LH}">{parts}</text>')
        return "\n".join(out)


class Anim:
    """Collects CSS keyframes for timed reveals within a looping cycle."""

    def __init__(self, period):
        self.T, self.css, self.n = period, [], 0

    def reveal(self, t_on, t_off=None, hide_at=0.955):
        """Class that is invisible until t_on (s), visible until hide_at of the cycle."""
        self.n += 1
        name = f"k{self.n}"
        on = max(0.01, min(t_on / self.T, hide_at - 0.01)) * 100
        off = (t_off / self.T * 100) if t_off else hide_at * 100
        self.css.append(
            f".{name}{{animation:{name} {self.T}s linear infinite}}"
            f"@keyframes {name}{{0%,{on - 0.01:.2f}%{{fill-opacity:0}}"
            f"{on:.2f}%,{off - 0.01:.2f}%{{fill-opacity:1}}{off:.2f}%,100%{{fill-opacity:0}}}}")
        return name


def wrap_svg(w, h, style, body, title, desc, bg, radius=12, border=None):
    stroke = f' stroke="{border}" stroke-width="1"' if border else ""
    return f"""<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 {w} {h}" width="{w}" height="{h}" role="img" aria-labelledby="t d" xml:space="preserve">
<title id="t">{escape(title)}</title>
<desc id="d">{escape(desc)}</desc>
<style>
text{{font-family:{FONT};font-size:{FS}px;white-space:pre;font-variant-ligatures:none;font-feature-settings:'liga' 0,'calt' 0}}
{style}
@media (prefers-reduced-motion: reduce){{*{{animation:none!important;fill-opacity:1!important;opacity:1!important}}}}
</style>
<rect x=".5" y=".5" width="{w - 1}" height="{h - 1}" rx="{radius}" fill="{bg}"{stroke}/>
{body}
</svg>
"""


def stars(cv, rows, cols, n, avoid, seed, classes):
    rnd = random.Random(seed)
    placed = 0
    while placed < n:
        r, c = rnd.randrange(rows), rnd.randrange(cols)
        if any(r0 <= r <= r1 and c0 <= c <= c1 for r0, c0, r1, c1 in avoid):
            continue
        if cv.g[r][c][0] != " ":
            continue
        cv.put(r, c, rnd.choice(".  .+·*"), rnd.choice(classes) if True else None)
        placed += 1


# ============================================================================ HERO
BRAND = "@balijepallipavan"
PORTRAIT_RAMP = " .:-=+*#%@"


def portrait_svg(x, y, fs, lh, dev_step):
    """The ASCII portrait (assets/portrait.txt) as a cyanotype print that develops row by row."""
    lines = open(os.path.join(HERE, "portrait.txt"), encoding="utf-8").read().split("\n")
    tone = lambda ch: "pa" if PORTRAIT_RAMP.index(ch) >= 6 else "pb" if PORTRAIT_RAMP.index(ch) >= 3 else "pc"
    out = [f'<g font-size="{fs}">']
    for r, line in enumerate(lines):
        if not line.strip():
            continue
        runs = []
        for ch in line:
            k = None if ch == " " else tone(ch)
            if runs and runs[-1][0] == k:
                runs[-1][1] += ch
            else:
                runs.append([k, ch])
        body = "".join(escape(t) if k is None else f'<tspan class="{k}">{escape(t)}</tspan>' for k, t in runs)
        out.append(f'<text class="dev" style="font-size:{fs}px;animation-delay:{r * dev_step:.2f}s" '
                   f'x="{x}" y="{y + (r + 1) * lh:.1f}">{body}</text>')
    out.append("</g>")
    return "\n".join(out), len(lines)


def hero():
    ROWS, COLS = 33, 138
    T = 22.0
    a = Anim(T)
    cv = Canvas(ROWS, COLS)        # static + per-char animated glyphs
    x0, y0 = 26, 32

    # ---- blueprint frame + labels
    cv.put(0, 0, "+--", "d"); cv.put(0, COLS - 3, "--+", "d")
    cv.put(ROWS - 1, 0, "+--", "d"); cv.put(ROWS - 1, COLS - 3, "--+", "d")
    cv.put(1, 0, "|", "d"); cv.put(1, COLS - 1, "|", "d")
    cv.put(ROWS - 2, 0, "|", "d"); cv.put(ROWS - 2, COLS - 1, "|", "d")
    cv.put(0, 5, "FIG. 01", "m"); cv.put(0, 13, "PAVAN, THINKING  //  CYANOTYPE", "d")
    cv.put(ROWS - 1, COLS - 40, BRAND, "m")
    cv.put(ROWS - 1, COLS - 22, "// sheet 1 of 3", "d")

    # ---- portrait card (pixel-positioned, its own font size)
    card_x, card_y, card_w, card_h = 38, 50, 362, 426
    p_fs, p_lh = 7.0, 8.43
    portrait, p_rows = portrait_svg(card_x + 12, card_y + 4, p_fs, p_lh, 0.045)
    card = (f'<rect x="{card_x}" y="{card_y}" width="{card_w}" height="{card_h}" rx="6" fill="{SURFACE}"/>'
            f'<rect x="{card_x + 6}" y="{card_y + 6}" width="{card_w - 12}" height="{card_h - 12}" rx="3" '
            f'fill="none" stroke="{BORDER}" stroke-width="1"/>')
    scan = (f'<clipPath id="cardclip"><rect x="{card_x}" y="{card_y}" width="{card_w}" height="{card_h}" rx="6"/></clipPath>'
            f'<g clip-path="url(#cardclip)"><rect class="scan" x="{card_x}" y="{card_y - 24}" width="{card_w}" '
            f'height="24" fill="url(#scangrad)"/></g>')
    cv.put(26, 2, "PLATE 01", "m"); cv.put(26, 12, "self-portrait, cyanotype", "d")
    cv.put(27, 2, f"80 x {p_rows} chars", "d"); cv.put(27, 21, "//", "d")
    cv.put(27, 24, "ramp", "d"); cv.put(27, 29, ".:-=+*#%@", "m")

    # ---- callouts pointing at the portrait
    notes = [(12, "round glasses, reads papers"),
             (15, "mustache: load-bearing"),
             (19, "beard: grown, not prompted"),
             (22, "checked shirt, checked facts")]
    for r, text in notes:
        cv.put(r, 46, "<--", "m co"); cv.put(r, 50, text, "p co")

    # ---- thought bubbles rising from the curls into a neural-net cloud
    for i, (r, c, ch) in enumerate([(11, 45, "."), (10, 46, "o"), (9, 47, "O")]):
        cv.put(r, c, ch, f"m bub{i}")
    C_R, C_C = 0, 46
    cloud = [
        r"",
        r"      .-~~~-.     .-~~~~-.",
        r"  .-~'       '-~~-'       '~-.",
        r" (   o--.             .--o    )",
        r"(        \-( o )-.   /         )",
        r"(   o-----:       >-o-----o    )",
        r"(        /-( o )-'   \         )",
        r" (   o--'             '--o    )",
        r"  '-._      _.-~~-._      _.-'",
        r"      '~~~~'        '~~~~'",
    ]
    cv.art(C_R, C_C, cloud, "d")
    for r, line in enumerate(cloud):
        for c, ch in enumerate(line):
            if ch == "o":
                L = 0 if c < 8 else 1 if c < 16 else 2 if c < 23 else 3
                cv.put(C_R + r, C_C + c, "o", f"p node{L}")

    # dimension line
    cv.put(ROWS - 3, 2, "|<-------", "d")
    cv.put(ROWS - 3, 12, "7+ yrs in AI / ML", "m")
    cv.put(ROWS - 3, 30, "------->|", "d")

    # ---- terminal
    TR, TC, TW = 2, 79, 57
    cv.put(TR, TC, "." + "-" * (TW - 2) + ".", "m")
    cv.put(TR + 1, TC, "|", "m"); cv.put(TR + 1, TC + TW - 1, "|", "m")
    cv.put(TR + 1, TC + 2, "o", "p"); cv.put(TR + 1, TC + 4, "o", "m"); cv.put(TR + 1, TC + 6, "o", "m")
    cv.put(TR + 1, TC + 17, "pavan@balijepallipavan: ~", "m")
    cv.put(TR + 2, TC, "|" + "-" * (TW - 2) + "|", "m")
    body_rows = 25
    for i in range(body_rows):
        cv.put(TR + 3 + i, TC, "|", "m"); cv.put(TR + 3 + i, TC + TW - 1, "|", "m")
    cv.put(TR + 3 + body_rows, TC, "'" + "-" * (TW - 2) + "'", "m")

    t = 0.6
    row = TR + 4

    def cmd(text, pause=0.5):
        nonlocal t, row
        cv.put(row, TC + 2, "$", "m " + a.reveal(t))
        for j, ch in enumerate(text):
            t += 0.07
            cv.put(row, TC + 4 + j, ch, "p " + a.reveal(t))
        t += pause
        row += 1

    def out(segs, gap=0.12, indent=4):
        nonlocal t, row
        cls_t = a.reveal(t)
        col = TC + indent
        for text, c in segs:
            cv.put(row, col, text, f"{c} {cls_t}")
            col += len(text)
        t += gap
        row += 1

    cmd("whoami")
    out([("Pavan Kumar Balijepalli", "p")])
    out([("Lead Data Scientist / AI Lead ", "p"), ("@ Cigna", "m")])
    out([("7+ yrs in AI/ML, mostly the unglamorous middle", "p")])
    row += 1; t += 0.6
    cmd("cat now.txt")
    for k, v in [("shipping", "agentic systems, built to last"),
                 ("studying", "M.Tech AIML @ BITS Pilani"),
                 ("teaching", "guest lectures @ BITS WILP"),
                 ("digging", "how LLMs are actually pretrained"),
                 ("building", f"{BRAND}, a village"),
                 ]:
        out([(f"{k} ", "m"), ("." * (12 - len(k)), "d"), (" " + v, "p")])
    row += 1; t += 0.6
    cmd("ls ~/huggingface")
    out([("TeLLM/", "p"), ("          a Telugu LLM", "d")])
    out([("phi2-sqlcoder/", "p"), ("  plain English -> SQL", "d")])
    row += 1; t += 0.6
    cmd("./think --hard --no-hype")
    bar_row, bar_w = row, 36
    cv.put(bar_row, TC + 4, "[", "m " + a.reveal(t)); cv.put(bar_row, TC + 5 + bar_w, "]", "m " + a.reveal(t))
    for j in range(bar_w):
        cv.put(bar_row, TC + 5 + j, ".", "d " + a.reveal(t))
        cv.put(bar_row, TC + 5 + j, "#", "p " + a.reveal(t + 0.1 + j * 0.06), opaque=True)
    t += 0.1 + bar_w * 0.06
    row += 1
    out([("> ", "m"), ("what is the model ", "p"), ("*actually*", "m"), (" doing?", "p")], gap=0.5)
    out([("> ", "m"), ("be comfortable being wrong in public.", "p")], gap=0.8)
    row += 1
    cv.put(row, TC + 2, "$", "m " + a.reveal(t))
    cursor_row, cursor_col = row, TC + 4
    cursor_on = t / T * 100

    # stars, kept off the card, cloud, notes and terminal
    stars(cv, ROWS, COLS, 30, [(0, TC - 1, ROWS - 1, TC + TW), (0, 0, 27, 45), (0, 45, 10, 78),
                               (11, 45, 23, 78), (ROWS - 3, 0, ROWS - 1, COLS)],
          seed=7, classes=["d tw0", "d tw1", "d tw2", "m tw3"])

    W = int(COLS * CW + 56)
    H = ROWS * LH + 40
    cursor = Canvas(ROWS, COLS)
    cursor.put(cursor_row, cursor_col, "█", "m cur")

    style = f"""
.p{{fill:{BG}}} .m{{fill:{MIST}}} .d{{fill:{INK_MUTED}}}
.pa{{fill:{INK}}} .pb{{fill:{COBALT}}} .pc{{fill:{MIST}}}
.dev{{animation:dev 1.4s ease-out both}}
@keyframes dev{{0%{{fill-opacity:0}}40%{{fill-opacity:.35}}100%{{fill-opacity:1}}}}
.co{{animation:dev 1s ease-out 2.6s both}}
.scan{{animation:scan 7s ease-in-out infinite}}
@keyframes scan{{0%{{transform:translateY(0)}}70%,100%{{transform:translateY({card_h + 24}px)}}}}
.cur{{animation:blink 1s steps(1) infinite}}
@keyframes blink{{50%{{fill-opacity:0}}}}
.curwrap{{animation:cw {T}s linear infinite}}
@keyframes cw{{0%,{cursor_on - 0.01:.2f}%{{opacity:0}}{cursor_on:.2f}%,95.49%{{opacity:1}}95.5%,100%{{opacity:0}}}}
.node0,.node1,.node2,.node3{{animation:pulse 2.4s ease-in-out infinite}}
.node1{{animation-delay:.3s}} .node2{{animation-delay:.6s}} .node3{{animation-delay:.9s}}
@keyframes pulse{{0%,100%{{fill:{INK_MUTED}}}35%{{fill:{BG}}}60%{{fill:{MIST}}}}}
.bub0,.bub1,.bub2{{animation:bub 3s ease-in-out infinite}}
.bub1{{animation-delay:.4s}} .bub2{{animation-delay:.8s}}
@keyframes bub{{0%,100%{{fill-opacity:.25}}40%{{fill-opacity:1}}}}
.tw0,.tw1,.tw2,.tw3{{animation:tw 4s ease-in-out infinite}}
.tw1{{animation-delay:1s}} .tw2{{animation-delay:2.2s}} .tw3{{animation-delay:3.1s}}
@keyframes tw{{0%,100%{{fill-opacity:.25}}50%{{fill-opacity:1}}}}
{chr(10).join(a.css)}
"""
    defs = (f'<defs><linearGradient id="scangrad" x1="0" y1="0" x2="0" y2="1">'
            f'<stop offset="0" stop-color="{MIST}" stop-opacity="0"/>'
            f'<stop offset="1" stop-color="{COBALT}" stop-opacity=".22"/></linearGradient></defs>')
    body = (defs + card + "\n" + portrait + "\n" + scan + "\n" + cv.svg(x0, y0)
            + f'\n<g class="curwrap">{cursor.svg(x0, y0)}</g>')
    return wrap_svg(W, H, style, body, "Pavan, thinking",
                    "Animated ASCII art: an ASCII self-portrait of Pavan Kumar Balijepalli printed like a "
                    "cyanotype, with blueprint callouts, a neural-network thought cloud, and a terminal "
                    "introducing him as Lead Data Scientist / AI Lead at Cigna.", INK)


# ===================================================================== PRETRAINING
def pretraining():
    ROWS, COLS = 34, 138
    T = 12.0
    a = Anim(T)
    cv = Canvas(ROWS, COLS)

    cv.put(0, 0, "+--", "b"); cv.put(0, COLS - 3, "--+", "b")
    cv.put(ROWS - 1, 0, "+--", "b"); cv.put(ROWS - 1, COLS - 3, "--+", "b")
    cv.put(0, 5, "FIG. 02", "c"); cv.put(0, 13, "HOW LLMs ARE ACTUALLY PRETRAINED  //  what I'm digging into", "u")
    cv.put(ROWS - 1, COLS - 40, BRAND, "c")
    cv.put(ROWS - 1, COLS - 22, "// sheet 2 of 3", "u")

    # ---- left: loss curve drawing itself
    L_R, L_C = 4, 3
    cv.put(L_R, L_C, "loss", "c")
    cv.put(L_R + 1, L_C + 1, "^", "i")
    H = 18
    for i in range(H):
        cv.put(L_R + 2 + i, L_C + 1, "|", "i")
    cv.put(L_R + 2 + H, L_C + 1, "+" + "-" * 30 + "> steps", "i")
    for i, lab in enumerate(["0", "10k", "20k", "30k"]):
        cv.put(L_R + 3 + H, L_C + 2 + i * 9, lab, "u")
    import math
    prev, k = None, 0
    rnd_l = random.Random(11)
    for x in range(30):
        y = 0.9 * math.exp(-x / 5.5) + 0.07 + rnd_l.uniform(-0.02, 0.02) * math.exp(-x / 25)
        r = max(0, min(H - 1, int(round((1 - y) * (H - 1)))))
        rows_here = [r] if prev is None or r - prev <= 1 else list(range(prev + 1, r + 1))
        for rr in rows_here:
            ch = "*" if rr == r else ":"
            cv.put(L_R + 2 + rr, L_C + 2 + x, ch, "c " + a.reveal(0.3 + k * 0.11))
            k += 1
        prev = r
    cv.put(L_R + 5, L_C + 18, "next-token", "u")
    cv.put(L_R + 6, L_C + 18, "cross-entropy", "u")
    cv.put(L_R + 7, L_C + 18, "goes down.", "u")
    cv.put(L_R + 8, L_C + 18, "slowly.", "c " + a.reveal(5.0))

    # ---- centre: decoder block with a forward pass lighting up
    M_C = 46
    blocks = [
        (2, "  next-token probs  ", None),
        (5, "      softmax       ", 9),
        (8, "       linear       ", 8),
        (12, "    add  &  norm    ", 7),
        (15, "    feed forward    ", 6),
        (18, "    add  &  norm    ", 5),
        (21, " masked multi-head  ", 4),
        (22, "     attention      ", 4),
        (26, " token + pos embed  ", 2),
    ]
    W_ = 22
    def box(r, h, cls):
        cv.put(r, M_C, "." + "-" * W_ + ".", cls)
        for i in range(h):
            cv.put(r + 1 + i, M_C, "|", cls); cv.put(r + 1 + i, M_C + W_ + 1, "|", cls)
        cv.put(r + h + 1, M_C, "'" + "-" * W_ + "'", cls)
    box(4, 1, "i"); box(7, 1, "i"); box(11, 1, "u"); box(14, 1, "u"); box(17, 1, "u"); box(20, 2, "u"); box(25, 1, "i")
    # repeated-layer bracket
    cv.put(10, M_C - 3, ".-" + "-" * (W_ + 4) + "-.", "c")
    for r in range(11, 24):
        cv.put(r, M_C - 3, "|", "c"); cv.put(r, M_C + W_ + 4, "|", "c")
    cv.put(24, M_C - 3, "'-" + "-" * (W_ + 4) + "-'", "c")
    cv.put(17, M_C + W_ + 6, "x N", "c")
    mid = M_C + 1 + W_ // 2
    # forward pass: arrows and labels light up bottom -> top
    seq = [(29, "tok"), (28, "^"), (26, "lbl"), (24, "^"), (23, "^"), (21, "lbl"), (22, "lbl"),
           (19, "^"), (18, "lbl"), (16, "^"), (15, "lbl"), (13, "^"), (12, "lbl"), (10, "^"),
           (9, "^"), (8, "lbl"), (6, "^"), (5, "lbl"), (3, "^"), (2, "lbl")]
    labels = {r: txt for r, txt, _ in blocks}
    step = 0.32
    for k, (r, kind) in enumerate(seq):
        cls = f"fw fw{k}"
        if kind == "^":
            cv.put(r, mid, "^", "u " + cls)
        elif kind == "lbl":
            cv.put(r, M_C + 1, labels[r], "i " + cls)
    cv.put(29, M_C - 6, '"the model is actually ..."', "u fw fw0")
    cv.put(30, M_C + 1, "predict the next token.", "u")
    cv.put(31, M_C + 1, "then do it a trillion times.", "c")
    fw_css = "\n".join(f".fw{k}{{animation-delay:{k * step:.2f}s}}" for k in range(len(seq)))

    # ---- right: causal attention map, shimmering
    A_R, A_C = 4, 96
    toks = ["the", "model", "is", "actually", "just", "guessing", "the", "next", "word"]
    n = len(toks)
    cv.put(A_R, A_C, "causal self-attention (one head)", "c")
    shade = " .:-=+*#%@"
    rnd = random.Random(3)
    for i, tk in enumerate(toks):
        cv.put(A_R + 2 + i * 2, A_C, f"{tk:>9}", "u")
        weights = [rnd.random() ** 1.6 for _ in range(i + 1)]
        weights[-1] += 0.6; s = sum(weights)
        for j in range(n):
            col = A_C + 11 + j * 3
            if j <= i:
                v = weights[j] / s
                ch = shade[min(9, 1 + int(v * 14))]
                cv.put(A_R + 2 + i * 2, col, ch, f"c at{rnd.randrange(5)}")
            else:
                cv.put(A_R + 2 + i * 2, col, ".", "b")
    for j, tk in enumerate(toks):
        cv.put(A_R + 2 + n * 2, A_C + 11 + j * 3, tk[0], "u")
    cv.put(A_R + 4 + n * 2, A_C, "each token only looks back.", "u")
    cv.put(A_R + 5 + n * 2, A_C, "no peeking at the future.", "u")

    W = int(COLS * CW + 56)
    H = ROWS * LH + 40
    period = len(seq) * step + 2.0
    style = f"""
.i{{fill:{INK}}} .c{{fill:{COBALT}}} .u{{fill:{INK_MUTED}}} .b{{fill:{BORDER}}}
.fw{{animation:fw {period:.2f}s ease-out infinite}}
@keyframes fw{{0%,14%{{fill:{COBALT};fill-opacity:1}}4%{{fill:{MIST}}}28%,100%{{}}}}
{fw_css}
.at0,.at1,.at2,.at3,.at4{{animation:at 3.2s ease-in-out infinite}}
.at1{{animation-delay:.6s}} .at2{{animation-delay:1.3s}} .at3{{animation-delay:1.9s}} .at4{{animation-delay:2.6s}}
@keyframes at{{0%,100%{{fill-opacity:1}}50%{{fill-opacity:.35}}}}
{chr(10).join(a.css)}
"""
    grid = (f'<defs><pattern id="g" width="40" height="40" patternUnits="userSpaceOnUse">'
            f'<path d="M40 0H0V40" fill="none" stroke="{BORDER}" stroke-width="1"/></pattern></defs>'
            f'<rect x="1" y="1" width="{W - 2}" height="{H - 2}" rx="12" fill="url(#g)" opacity=".55"/>')
    return wrap_svg(W, H, style, grid + "\n" + cv.svg(26, 32), "How LLMs are actually pretrained",
                    "Animated ASCII blueprint: a loss curve drawing itself, a decoder-only "
                    "transformer block with a forward pass lighting up, and a causal attention map.",
                    BG, border=BORDER)


# ========================================================================== FOOTER
def footer():
    ROWS, COLS = 24, 138
    cv = Canvas(ROWS, COLS)
    waves = [Canvas(ROWS, COLS) for _ in range(4)]
    boat = Canvas(ROWS, COLS)

    cv.put(0, 0, "+--", "d"); cv.put(0, COLS - 3, "--+", "d")
    cv.put(ROWS - 1, 0, "+--", "d"); cv.put(ROWS - 1, COLS - 3, "--+", "d")
    cv.put(0, 5, "FIG. 03", "m"); cv.put(0, 13, "A CHART DRAWN AT SEA", "d")
    cv.put(ROWS - 1, COLS - 40, BRAND, "m")
    cv.put(ROWS - 1, COLS - 22, "// sheet 3 of 3", "d")

    # compass rose
    R0, C0 = 2, 6
    rose = [
        r"           N",
        r"           .",
        r"          /|\ ",
        r"     .   / | \   .",
        r"      './  |  \.'",
        r"  W -----<-+->----- E",
        r"      .'\  |  /'.",
        r"     '   \ | /   '",
        r"          \|/",
        r"           '",
        r"           S",
    ]
    cv.art(R0, C0, rose, "d")
    for (r, c, ch) in [(0, 11, "N"), (5, 2, "W"), (5, 20, "E"), (10, 11, "S")]:
        cv.put(R0 + r, C0 + c, ch, "m")
    cv.put(R0 + 5, C0 + 11, "+", "p needle")
    cv.put(R0 + 2, C0 + 11, "|", "p needle"); cv.put(R0 + 1, C0 + 11, ".", "p needle")
    cv.put(R0 + 11, C0 + 24, "lat:  ", "d"); cv.put(R0 + 11, C0 + 30, "curiosity", "m")
    cv.put(R0 + 12, C0 + 24, "long: ", "d"); cv.put(R0 + 12, C0 + 30, "consistency", "m")

    # course plotted across the chart
    cv.put(4, 36, "x  first video", "p")
    cv.put(5, 39, "\"4 things I had to unlearn\"", "d")
    def dotted(r0, c0, r1, c1):
        n = max(1, (c1 - c0) // 2)
        for i in range(n + 1):
            cv.put(round(r0 + (r1 - r0) * i / n), c0 + 2 * i, ".", "d dash")
    dotted(6, 40, 10, 54)       # first video -> boat
    dotted(13, 74, 11, 82)      # boat -> the village
    cv.put(11, 84, "x  the village", "p")
    cv.put(12, 87, "not an audience", "d")
    cv.put(3, 72, "~ here be hype ~", "d")
    cv.put(4, 74, "(steer clear)", "d")

    # lighthouse with a sweeping beam
    LR, LC = 3, 116
    house = [
        r"     _/\_",
        r"    |_  _|",
        r"     |  |",
        r"     |==|",
        r"     |  |",
        r"     |==|",
        r"     |  |",
        r"    /    \ ",
        r"   /______\ ",
    ]
    cv.art(LR, LC, house, "p")
    cv.put(LR + 1, LC + 6, "[]", "m lamp")
    rays = [(-1, "- - - - - - - .'"), (0, "= = = = = = = = = ="), (1, "- - - - - - - '.")]
    for k, (dr, ray) in enumerate(rays):
        cv.put(LR + 1 + dr, LC + 4 - len(ray) + (0 if dr == 0 else 1), ray, f"m beam beam{k}")
    # waves: 4 frames, each shifted, cycled
    pattern = "~~  ~   ~~~   ~~    ~    ~~~  "
    for f, wcv in enumerate(waves):
        for i, rr in enumerate(range(16, 20)):
            off = f * 2 * (1 if i % 2 == 0 else -1) + i * 5
            s = (pattern * 10)[off % len(pattern):][: COLS - 4]
            wcv.put(rr, 2, s, "m" if i % 2 == 0 else "d")

    # boat (bobs)
    bt = [
        r"       |\ ",
        r"       | \ ",
        r"       |  \ ",
        r"  _____|___\_",
        r"  \  b  b  /",
    ]
    boat.art(11, 57, bt, "p", ["", "", "", "", "     m  m"], {"m": "m"})

    cv.put(21, 6, "analog in a digital life.", "p")
    cv.put(21, 33, "//", "d")
    cv.put(21, 36, "be the mentor you never had.", "m")

    W = int(COLS * CW + 56)
    H = ROWS * LH + 40
    style = f"""
.p{{fill:{BG}}} .m{{fill:{MIST}}} .d{{fill:{INK_MUTED}}}
.w0,.w1,.w2,.w3{{opacity:0;animation:wv 1.6s steps(1) infinite}}
.w1{{animation-delay:.4s}} .w2{{animation-delay:.8s}} .w3{{animation-delay:1.2s}}
@keyframes wv{{0%{{opacity:1}}25%,100%{{opacity:0}}}}
.boat{{animation:bob 3.2s ease-in-out infinite}}
@keyframes bob{{0%,100%{{transform:translateY(0)}}50%{{transform:translateY(5px)}}}}
.lamp{{animation:lamp 2s ease-in-out infinite}}
@keyframes lamp{{0%,100%{{fill:{MIST}}}50%{{fill:{BG}}}}}
.beam{{animation:beam 2s ease-in-out infinite}} .beam1{{animation-delay:.2s}} .beam2{{animation-delay:.4s}}
@keyframes beam{{0%,100%{{fill-opacity:.1}}45%{{fill-opacity:1}}}}
.needle{{animation:needle 2.8s ease-in-out infinite}}
@keyframes needle{{0%,100%{{fill:{BG}}}50%{{fill:{MIST}}}}}
.dash{{animation:dash 2.4s linear infinite}}
@keyframes dash{{0%,100%{{fill-opacity:.4}}50%{{fill-opacity:1}}}}
"""
    body = cv.svg(26, 32)
    for f, wcv in enumerate(waves):
        body += f'\n<g class="w{f}">{wcv.svg(26, 32)}</g>'
    body += f'\n<g class="boat">{boat.svg(26, 32)}</g>'
    return wrap_svg(W, H, style, body, "A chart drawn at sea",
                    "Animated ASCII sea chart: compass rose, a lighthouse with a sweeping beam, "
                    "a bobbing boat on scrolling waves. Analog in a digital life.", INK)


if __name__ == "__main__":
    for name, fn in [("hero", hero), ("pretraining", pretraining), ("footer", footer)]:
        path = os.path.join(HERE, f"{name}.svg")
        with open(path, "w", encoding="utf-8") as fh:
            fh.write(fn())
        print("wrote", path, os.path.getsize(path), "bytes")
