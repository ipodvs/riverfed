import json

OUT = "module-1-the-theory-install-how-these-agents-actually-think.excalidraw"

BG = "#0f1729"
CARD_FILL = "#181b22"
TEXT = "#e6e8ee"
SOFT = "#cae3ff"
MUTED = "#9aa3b5"
FAINT = "#6e7686"

els = []
_seed = [1000]

def base(id_, **kw):
    _seed[0] += 1
    d = {
        "id": id_, "angle": 0, "backgroundColor": "transparent",
        "fillStyle": "solid", "strokeWidth": 1, "strokeStyle": "solid",
        "roughness": 0, "opacity": 100, "groupIds": [], "frameId": None,
        "roundness": None, "seed": _seed[0], "version": 1,
        "versionNonce": _seed[0], "isDeleted": False, "boundElements": None,
        "updated": 1, "link": None, "locked": False,
    }
    d.update(kw)
    return d

def text(id_, x, y, w, h, s, color, size, family=4, align="left"):
    e = base(id_, type="text", x=x, y=y, width=w, height=h,
             strokeColor=color, text=s, originalText=s,
             fontSize=size, fontFamily=family, textAlign=align,
             verticalAlign="top", containerId=None, lineHeight=1.4)
    els.append(e)
    return e

def rect(id_, x, y, w, h, stroke, fill=CARD_FILL, sw=1):
    e = base(id_, type="rectangle", x=x, y=y, width=w, height=h,
             strokeColor=stroke, backgroundColor=fill, strokeWidth=sw,
             roundness={"type": 3})
    els.append(e)
    return e

def vline(id_, x, y, h, color, sw=3):
    e = base(id_, type="line", x=x, y=y, width=4, height=h,
             strokeColor=color, strokeWidth=sw,
             points=[[0, 0], [0, h]], lastCommittedPoint=None,
             startBinding=None, endBinding=None,
             startArrowhead=None, endArrowhead=None)
    els.append(e)
    return e

def connector(id_, x, y, pts, color, sw=1):
    e = base(id_, type="line", x=x, y=y,
             width=max(abs(p[0]) for p in pts) or 1,
             height=max(abs(p[1]) for p in pts) or 1,
             strokeColor=color, strokeWidth=sw,
             points=pts, lastCommittedPoint=None,
             startBinding=None, endBinding=None,
             startArrowhead=None, endArrowhead=None)
    els.append(e)
    return e

# ------- header -------
text("h1", 60, 50, 1300, 56, "The Six-Module Build", TEXT, 44)
text("h2", 60, 116, 1380, 28, "From “how do these things think” to a real thing you shipped — each module ends with something on your machine.", SOFT, 20)
text("h3", 1560, 66, 40, 30, "◆", "#4f8cff", 22, align="right")

# ------- module cards -------
COLORS = ["#4f8cff", "#7a59e2", "#46c98b", "#ffd93d", "#ff6b35", "#4f8cff"]

modules = [
    {
        "n": "MODULE 1",
        "title": "The Theory + Install",
        "desc": [
            "How these agents actually think — the engine",
            "and the three dials you control. Then my entire",
            "setup lands on your machine with one command.",
            "No blank screens, no config marathon.",
        ],
        "out": [
            "Your AI OS installed and running,",
            "your folders scaffolded for your business",
        ],
    },
    {
        "n": "MODULE 2",
        "title": "Context",
        "desc": [
            "Teach it your business. What it should know",
            "about you, your customers and how you work",
            "— written once, used everywhere.",
        ],
        "out": [
            "Context files that know your",
            "business — the interview, done",
        ],
    },
    {
        "n": "MODULE 3",
        "title": "Memory",
        "desc": [
            "The self-improving loop. Correct it once and",
            "it stays corrected — your system gets sharper",
            "the more you use it.",
        ],
        "out": [
            "A memory that compiles your",
            "corrections into rules",
        ],
    },
    {
        "n": "MODULE 4",
        "title": "Tools",
        "desc": [
            "Wire it into the apps you already run — email,",
            "calendar, docs, the lot. This is where it stops",
            "being a chatbot and starts being staff.",
        ],
        "out": [
            "Your system connected to",
            "your real stack",
        ],
    },
    {
        "n": "MODULE 5",
        "title": "Skills",
        "desc": [
            "Teach it how you do things, your way.",
            "Repeatable playbooks it runs on command —",
            "written once, run forever.",
        ],
        "out": [
            "Your first custom skills,",
            "built from scratch",
        ],
    },
    {
        "n": "MODULE 6",
        "title": "The Live Build",
        "desc": [
            "One real piece, end to end — a landing page,",
            "a dashboard, an automation. You build it, you",
            "ship it, it’s yours.",
        ],
        "out": [
            "A working build you",
            "shipped yourself",
        ],
    },
]

CARD_W = 430
CARD_H = 310
COL_X = [60, 546, 1032]
ROW_Y = [200, 565]

for i, m in enumerate(modules):
    col = i % 3
    row = i // 3
    x = COL_X[col]
    y = ROW_Y[row]
    c = COLORS[i]
    pid = f"m{i}"

    rect(f"{pid}r", x, y, CARD_W, CARD_H, c, sw=2)
    # eyebrow
    text(f"{pid}e", x + 22, y + 20, CARD_W - 44, 18, m["n"], c, 13, family=3)
    # title
    text(f"{pid}t", x + 22, y + 46, CARD_W - 44, 30, m["title"], TEXT, 24)
    # description
    desc = "\n".join(m["desc"])
    text(f"{pid}d", x + 22, y + 90, CARD_W - 44, 22 * len(m["desc"]), desc, SOFT, 14)
    # outcome accent bar + label
    bar_y = y + CARD_H - 78
    vline(f"{pid}b", x + 22, bar_y, 52, c, sw=3)
    text(f"{pid}ol", x + 40, bar_y - 2, CARD_W - 64, 16, "YOU LEAVE WITH", MUTED, 11, family=3)
    out = "\n".join(m["out"])
    text(f"{pid}o", x + 40, bar_y + 18, CARD_W - 64, 20 * len(m["out"]), out, TEXT, 14)

# ------- connectors: linear progression 1..6 -------
# horizontal links within a row
def card_center_right(col, row):
    return (COL_X[col] + CARD_W, ROW_Y[row] + CARD_H // 2)

def card_left(col, row):
    return (COL_X[col], ROW_Y[row] + CARD_H // 2)

# row 1: 1->2->3
for col in range(2):
    x1, y1 = card_center_right(col, 0)
    x2, y2 = card_left(col + 1, 0)
    connector(f"c1_{col}", x1, y1, [[0, 0], [x2 - x1, 0]], "#4f8cff", sw=1)
# 3 -> 4 : clean snake connector through the gap band between rows
c3x = COL_X[2] + CARD_W // 2          # card 3 bottom-center
c4x = COL_X[0] + CARD_W // 2          # card 4 top-center
top = ROW_Y[0] + CARD_H               # 875... actually row1 bottom
row1_bottom = ROW_Y[0] + CARD_H
mid = row1_bottom + (ROW_Y[1] - row1_bottom) // 2
connector("c34", c3x, row1_bottom,
          [[0, 0],
           [0, mid - row1_bottom],
           [c4x - c3x, mid - row1_bottom],
           [c4x - c3x, ROW_Y[1] - row1_bottom]],
          "#4f8cff", sw=1)
# row 2: 4->5->6
for col in range(2):
    x1, y1 = card_center_right(col, 1)
    x2, y2 = card_left(col + 1, 1)
    connector(f"c2_{col}", x1, y1, [[0, 0], [x2 - x1, 0]], "#4f8cff", sw=1)

# ------- footer note -------
text("f1", 60, 910, 1380, 22,
     "Six modules · each ends with something real on your machine — not notes, not theory.",
     FAINT, 13, family=3)

doc = {
    "type": "excalidraw",
    "version": 2,
    "source": "riverfed · studio_diagram",
    "elements": els,
    "appState": {"viewBackgroundColor": BG, "gridSize": None},
    "files": {},
}

with open(OUT, "w", encoding="utf-8") as f:
    json.dump(doc, f, ensure_ascii=False, indent=2)
print("WROTE", OUT)
