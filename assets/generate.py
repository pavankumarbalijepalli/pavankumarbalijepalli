#!/usr/bin/env python3
"""Generates the animated SVGs used in the profile README (the "trailer").

    pip install fonttools brotli
    python3 assets/generate.py        # rewrites assets/*.svg

Art is drawn with monospace glyphs on a character grid, in the @balijepallipavan
"Cyanotype" palette. Fonts (assets/fonts, SIL OFL) are subset and embedded in each SVG,
so GitHub shows real type and the ASCII stays aligned on every machine.
"""
import base64
import io
import os
import random
from html import escape

from fontTools import subset
from fontTools.ttLib import TTFont

HERE = os.path.dirname(os.path.abspath(__file__))
BRAND = "@balijepallipavan"

# palette (design-system tokens)
BG, SURFACE, INK, INK_MUTED = "#E8EDF2", "#F3F6F9", "#10243F", "#46566E"
COBALT, MIST, BORDER = "#1F4E8C", "#7E9CC4", "#C3CEDA"

FS, LH = 14, 18           # grid font size and line height (px)
CW = FS * 0.6             # JetBrains Mono advance is exactly 0.6em
COLS = 138
WIDTH = int(COLS * CW + 56)
X0, Y0 = 26, 32

MONO = "'PKB Mono', ui-monospace, Menlo, Consolas, monospace"
DISPLAY = "'PKB Garamond', 'Apple Garamond', Garamond, Georgia, serif"
SERIF = "'PKB Lora', Georgia, serif"
SANS = "'PKB Grotesk', 'Helvetica Neue', Arial, sans-serif"
ASCII = "".join(chr(c) for c in range(32, 127)) + "·"


# --------------------------------------------------------------------------- fonts
def font_face(alias, file, text, weight=400, style="normal"):
    """@font-face with the font subset to `text`, as an embedded woff2 data URI."""
    font = TTFont(os.path.join(HERE, "fonts", file))
    opts = subset.Options()
    opts.flavor = "woff2"
    opts.layout_features = ["kern"]          # no ligatures: keeps ASCII art literal
    opts.name_IDs = []
    opts.notdef_outline = True
    sub = subset.Subsetter(opts)
    sub.populate(text=text + " ")
    sub.subset(font)
    buf = io.BytesIO()
    font.flavor = "woff2"
    font.save(buf)
    data = base64.b64encode(buf.getvalue()).decode()
    return (f"@font-face{{font-family:'{alias}';font-weight:{weight};font-style:{style};"
            f"src:url(data:font/woff2;base64,{data}) format('woff2')}}")


def mono_face():
    return font_face("PKB Mono", "JetBrainsMono-Regular.woff2", ASCII)


# --------------------------------------------------------------------------- grid
class Canvas:
    def __init__(self, rows, cols=COLS):
        self.rows, self.cols = rows, cols
        self.g = [[(" ", None) for _ in range(cols)] for _ in range(rows)]

    def put(self, r, c, text, cls, opaque=False):
        for i, ch in enumerate(text):
            if 0 <= r < self.rows and 0 <= c + i < self.cols and (ch != " " or opaque):
                self.g[r][c + i] = (ch, cls)

    def art(self, r, c, lines, cls, masks=None, palette=None):
        for i, line in enumerate(lines):
            mask = masks[i] if masks and i < len(masks) else ""
            for j, ch in enumerate(line):
                k = mask[j] if j < len(mask) else "."
                self.put(r + i, c + j, ch, palette.get(k, cls) if palette else cls)

    def svg(self, x0=X0, y0=Y0):
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
            parts = "".join(escape(t) if c is None else f'<tspan class="{c}">{escape(t)}</tspan>'
                            for c, t in runs)
            out.append(f'<text x="{x0}" y="{y0 + r * LH}">{parts}</text>')
        return "\n".join(out)


class Anim:
    """CSS keyframes for timed reveals within a looping cycle."""

    def __init__(self, period):
        self.T, self.css, self.n = period, [], 0

    def reveal(self, t_on, hide_at=0.955):
        self.n += 1
        name = f"k{self.n}"
        on = max(0.01, min(t_on / self.T, hide_at - 0.01)) * 100
        off = hide_at * 100
        self.css.append(
            f".{name}{{animation:{name} {self.T}s linear infinite}}"
            f"@keyframes {name}{{0%,{on - 0.01:.2f}%{{fill-opacity:0}}"
            f"{on:.2f}%,{off - 0.01:.2f}%{{fill-opacity:1}}{off:.2f}%,100%{{fill-opacity:0}}}}")
        return name


def wrap_svg(h, style, body, title, desc, fonts):
    w = WIDTH
    return f"""<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 {w} {h}" width="{w}" height="{h}" role="img" aria-labelledby="t d" xml:space="preserve">
<title id="t">{escape(title)}</title>
<desc id="d">{escape(desc)}</desc>
<style>
{chr(10).join(fonts)}
text{{font-family:{MONO};font-size:{FS}px;white-space:pre;font-variant-ligatures:none}}
.p{{fill:{BG}}} .m{{fill:{MIST}}} .d{{fill:{INK_MUTED}}}
{style}
@media (prefers-reduced-motion: reduce){{*{{animation:none!important;fill-opacity:1!important;opacity:1!important}}}}
</style>
<rect x=".5" y=".5" width="{w - 1}" height="{h - 1}" rx="12" fill="{INK}"/>
{body}
</svg>
"""


def frame(cv, fig, label, sheet):
    rows = cv.rows
    cv.put(0, 0, "+--", "d"); cv.put(0, COLS - 3, "--+", "d")
    cv.put(rows - 1, 0, "+--", "d"); cv.put(rows - 1, COLS - 3, "--+", "d")
    cv.put(0, 5, fig, "m"); cv.put(0, 6 + len(fig), label, "d")
    cv.put(rows - 1, COLS - 40, BRAND, "m")
    cv.put(rows - 1, COLS - 22, f"// sheet {sheet} of 3", "d")


def stars(cv, n, avoid, seed, classes):
    rnd = random.Random(seed)
    placed = 0
    while placed < n:
        r, c = rnd.randrange(1, cv.rows - 1), rnd.randrange(1, cv.cols - 1)
        if any(r0 <= r <= r1 and c0 <= c <= c1 for r0, c0, r1, c1 in avoid) or cv.g[r][c][0] != " ":
            continue
        cv.put(r, c, rnd.choice("..+·*"), rnd.choice(classes))
        placed += 1


TWINKLE = """.tw0,.tw1,.tw2,.tw3{animation:tw 4s ease-in-out infinite}
.tw1{animation-delay:1s} .tw2{animation-delay:2.2s} .tw3{animation-delay:3.1s}
@keyframes tw{0%,100%{fill-opacity:.25}50%{fill-opacity:1}}"""


# ============================================================================ HERO
PORTRAIT_RAMP = " .:-=+*#%@"


def portrait_svg(x, y, fs, dev_step):
    """assets/portrait.txt as chalk on the navy ground: shadows become light strokes."""
    lh = fs * 1.2
    lines = open(os.path.join(HERE, "portrait.txt"), encoding="utf-8").read().split("\n")
    tone = lambda ch: ("pa" if PORTRAIT_RAMP.index(ch) >= 6 else
                       "pb" if PORTRAIT_RAMP.index(ch) >= 3 else "pc")
    out = []
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
    return "\n".join(out), len(lines), max(map(len, lines)) * fs * 0.6, len(lines) * lh


def hero():
    ROWS, T = 26, 16.0
    a = Anim(T)
    cv = Canvas(ROWS)
    frame(cv, "FIG. 01", " PAVAN  //  CYANOTYPE", 1)

    # portrait: chalk strokes, developing top to bottom, a soft light sweeping over
    px, py = 46, 52
    portrait, p_rows, p_w, p_h = portrait_svg(px, py, 7.0, 0.045)
    sweep = (f'<clipPath id="pclip"><rect x="{px}" y="{py}" width="{p_w:.0f}" height="{p_h:.0f}"/></clipPath>'
             f'<g clip-path="url(#pclip)"><rect class="scan" x="{px}" y="{py - 40}" width="{p_w:.0f}" '
             f'height="40" fill="url(#sweep)"/></g>')

    # name block, set in the brand's type
    tx = 424
    name = (f'<text x="{tx}" y="118" style="font-family:{DISPLAY};font-weight:600;font-size:56px;'
            f'letter-spacing:-0.5px" class="p rise">Pavan Kumar Balijepalli</text>'
            f'<text x="{tx + 2}" y="158" style="font-family:{SERIF};font-style:italic;font-size:21px" '
            f'class="m rise r2">building things that think, ship, and hold up in production.</text>'
            f'<text x="{tx + 2}" y="196" style="font-family:{SANS};font-weight:500;font-size:16px" class="rise r3">'
            f'<tspan class="p">Lead Data Scientist / AI Lead</tspan><tspan class="m"> @ Cigna</tspan>'
            f'<tspan class="d">   ·   </tspan><tspan class="p">7+ yrs in AI/ML</tspan></text>'
            f'<rect x="{tx + 2}" y="214" width="96" height="2" fill="{MIST}" class="rise r3"/>')

    # terminal
    TR, TC, TW = 12, 47, 87
    title = " pavan@balijepallipavan: ~ "
    cv.put(TR, TC, ".--" + title + "-" * (TW - 5 - len(title)) + ".", "d")
    cv.put(TR, TC + 3, title, "m")
    for i in range(1, 10):
        cv.put(TR + i, TC, "|", "d"); cv.put(TR + i, TC + TW - 1, "|", "d")
    cv.put(TR + 10, TC, "'" + "-" * (TW - 2) + "'", "d")

    t, row = 1.2, TR + 1

    def cmd(text, pause=0.45):
        nonlocal t, row
        cv.put(row, TC + 2, "$", "m " + a.reveal(t))
        for j, ch in enumerate(text):
            t += 0.06
            cv.put(row, TC + 4 + j, ch, "p " + a.reveal(t))
        t += pause
        return TC + 4 + len(text)

    def out(segs, gap=0.12):
        nonlocal t, row
        cls_t = a.reveal(t)
        col = TC + 4
        for text, c in segs:
            cv.put(row, col, text, f"{c} {cls_t}")
            col += len(text)
        t += gap
        row += 1

    cmd("cat now.txt"); row += 1
    for k, v in [("shipping", "agentic systems, built to last"),
                 ("studying", "M.Tech AIML @ BITS Pilani"),
                 ("teaching", "guest lectures @ BITS Pilani WILP"),
                 ("open", "TeLLM, phi2-sqlcoder on Hugging Face")]:
        out([(f"{k} ", "m"), ("." * (11 - len(k)), "d"), ("  " + v, "p")])
    row += 1; t += 0.5
    end = cmd("./think --hard --no-hype", pause=0.2)
    bar_c, bar_w = end + 3, 24
    cv.put(row, bar_c, "[", "m " + a.reveal(t)); cv.put(row, bar_c + bar_w + 1, "]", "m " + a.reveal(t))
    for j in range(bar_w):
        cv.put(row, bar_c + 1 + j, ".", "d " + a.reveal(t))
        cv.put(row, bar_c + 1 + j, "#", "p " + a.reveal(t + 0.1 + j * 0.06), opaque=True)
    t += 0.1 + bar_w * 0.06 + 0.4
    row += 1
    out([("> ", "m"), ("what is the model ", "p"), ("actually", "m"), (" doing?", "p")], gap=0.8)
    cv.put(row, TC + 2, "$", "m " + a.reveal(t))
    cursor_x, cursor_y, cursor_on = X0 + (TC + 4) * CW, Y0 + row * LH - 13, t / T * 100

    stars(cv, 22, [(0, 0, ROWS - 1, 46), (1, 46, 11, COLS - 1), (TR, TC - 1, TR + 10, TC + TW)],
          seed=5, classes=["d tw0", "d tw1", "d tw2", "m tw3"])

    H = ROWS * LH + 30
    style = f"""
.pa{{fill:{BG}}} .pb{{fill:{MIST}}} .pc{{fill:{INK_MUTED}}}
.dev{{animation:dev 1.4s ease-out both}}
@keyframes dev{{0%{{fill-opacity:0}}40%{{fill-opacity:.35}}100%{{fill-opacity:1}}}}
.scan{{animation:scan 7s ease-in-out 2.2s infinite}}
@keyframes scan{{0%{{transform:translateY(0)}}70%,100%{{transform:translateY({p_h + 40:.0f}px)}}}}
.rise{{animation:rise 1s ease-out .3s both}} .r2{{animation-delay:.6s}} .r3{{animation-delay:.9s}}
@keyframes rise{{0%{{opacity:0;transform:translateY(8px)}}100%{{opacity:1;transform:none}}}}
.cur{{animation:blink 1s steps(1) infinite}}
@keyframes blink{{50%{{opacity:0}}}}
.curwrap{{animation:cw {T}s linear infinite}}
@keyframes cw{{0%,{cursor_on - 0.01:.2f}%{{opacity:0}}{cursor_on:.2f}%,95.49%{{opacity:1}}95.5%,100%{{opacity:0}}}}
{TWINKLE}
{chr(10).join(a.css)}
"""
    used = "Pavan Kumar Balijepalli"
    fonts = [mono_face(),
             font_face("PKB Garamond", "EBGaramond-SemiBold.woff2", used, 600),
             font_face("PKB Lora", "Lora-Italic.woff2",
                       "building things that think, ship, and hold up in production.", 400, "italic"),
             font_face("PKB Grotesk", "SpaceGrotesk-Medium.woff2",
                       "Lead Data Scientist / AI Lead @ Cigna · 7+ yrs in AI/ML", 500)]
    defs = (f'<defs><linearGradient id="sweep" x1="0" y1="0" x2="0" y2="1">'
            f'<stop offset="0" stop-color="{MIST}" stop-opacity="0"/>'
            f'<stop offset="1" stop-color="{MIST}" stop-opacity=".18"/></linearGradient></defs>')
    cursor = (f'<g class="curwrap"><rect class="cur" x="{cursor_x:.1f}" y="{cursor_y}" width="8" '
              f'height="16" fill="{MIST}"/></g>')
    body = defs + portrait + "\n" + sweep + "\n" + name + "\n" + cv.svg() + "\n" + cursor
    return wrap_svg(H, style, body, "Pavan Kumar Balijepalli",
                    "An ASCII self-portrait drawn like chalk on navy, beside the name Pavan Kumar "
                    "Balijepalli, the line 'building things that think, ship, and hold up in production', "
                    "Lead Data Scientist / AI Lead at Cigna, 7+ years in AI/ML, and a terminal: shipping "
                    "agentic systems, studying M.Tech AIML at BITS Pilani, guest lecturing at BITS Pilani "
                    "WILP, TeLLM and phi2-sqlcoder on Hugging Face.", fonts)


# =========================================================================== BRAND
def brand():
    ROWS = 12
    cv = Canvas(ROWS)
    frame(cv, "FIG. 02", " THE VILLAGE", 2)

    line1 = "AI/ML for people who feel like outsiders in AI."
    line2 = "be the mentor I never had."
    text = (f'<text x="48" y="104" style="font-family:{DISPLAY};font-weight:600;font-size:48px" '
            f'class="p">{BRAND}</text>'
            f'<text x="50" y="146" style="font-family:{SANS};font-size:19px" class="p">{escape(line1)}</text>'
            f'<text x="50" y="180" style="font-family:{SERIF};font-style:italic;font-size:19px" class="m">'
            f'{escape(line2)}</text>')

    # a little village, windows lighting up one by one (houses share one ground line)
    small = ["   /\\   ", "  /  \\  ", " /____\\ ", " | [] | ", " |_[]_| "]
    tall = ["   /\\   ", "  /  \\  ", " /____\\ ", " | [] | ", " | [] | ", " |_[]_| "]
    wide = ["    /\\      ", "   /  \\____ ", "  /____\\   \\", "  | [] | [] |", "  |_[]_|____|"]
    ground, c, win = 8, 80, 0
    for art in [small, tall, wide, small, tall, small]:
        top = ground - len(art)
        for i, line in enumerate(art):
            for j, ch in enumerate(line):
                if ch != " ":
                    cv.put(top + i, c + j, ch, "m")
            k = line.find("[]")
            while k != -1:
                cv.put(top + i, c + k, "[]", f"win w{win % 6}")
                win += 1
                k = line.find("[]", k + 2)
        c += max(map(len, art))
    cv.put(ground, 79, "-" * (c - 79 + 1), "d")
    cv.put(ground + 1, 80, "a village, not an audience.", "d")
    cv.put(1, 96, "*", "m tw0"); cv.put(1, 84, ".", "d tw1"); cv.put(2, 112, "+", "d tw2"); cv.put(1, 124, ".", "m tw3")

    H = ROWS * LH + 30
    style = f"""
.win{{fill:{INK_MUTED};animation:win 6s ease-in-out infinite}}
.w1{{animation-delay:.8s}} .w2{{animation-delay:1.9s}} .w3{{animation-delay:2.7s}} .w4{{animation-delay:3.6s}} .w5{{animation-delay:4.4s}}
@keyframes win{{0%,100%{{fill:{INK_MUTED}}}30%,70%{{fill:{BG}}}}}
{TWINKLE}
"""
    fonts = [mono_face(),
             font_face("PKB Garamond", "EBGaramond-SemiBold.woff2", BRAND, 600),
             font_face("PKB Lora", "Lora-Italic.woff2", line2, 400, "italic"),
             font_face("PKB Grotesk", "SpaceGrotesk-Regular.woff2", line1, 400)]
    return wrap_svg(H, style, text + "\n" + cv.svg(), BRAND,
                    f"{BRAND}: {line1} {line2} A little ASCII village: a village, not an audience.", fonts)


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
    motto = "analog in a digital life."
    body += (f'\n<text x="76" y="412" style="font-family:{SERIF};font-style:italic;font-size:20px" '
             f'class="p">{motto}</text>')
    fonts = [mono_face(), font_face("PKB Lora", "Lora-Italic.woff2", motto, 400, "italic")]
    return wrap_svg(H, style, body, "A chart drawn at sea",
                    "Animated ASCII sea chart: compass rose, a lighthouse with a sweeping beam, "
                    "a bobbing boat on scrolling waves, sailing from 'first video' to 'the village'. "
                    "Analog in a digital life.", fonts)


if __name__ == "__main__":
    for name, fn in [("hero", hero), ("brand", brand), ("footer", footer)]:
        path = os.path.join(HERE, f"{name}.svg")
        with open(path, "w", encoding="utf-8") as fh:
            fh.write(fn())
        print("wrote", path, os.path.getsize(path), "bytes")
