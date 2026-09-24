"""PDF 原理图适配器：从矢量 PDF（带文字层）提取元件、引脚与网络连通性。

技术路线（详见 references/pdf_extraction_guide.md）：
1. 文字提取：pdfplumber（优先）/ PyMuPDF 兜底，提取全部文本及坐标
2. 图形提取：线条 / 矩形 / 曲线及坐标、线宽
3. 元件识别：位号正则 + 元件框（矩形）关联；无框元件（电阻等）按邻域引脚号识别
4. 连接推断：导线段并查集（端点 / T 型 / junction 圆点合并）+ 引脚点吸附 + 网络标号
5. 置信度评估：每个连接按判定依据给出 confidence / method / note
6. LLM 辅助校验：留给 Agent 阶段补充（method=llm_assisted），本适配器不调用 LLM

精度声明：PDF 提取不保证 100% 精确（矢量图形 + 文字推断的技术本质决定），
置信度 < 0.7 的连接全部进入人工核对清单（outputs/pdf_review.md），不得静默丢弃。
"""

from __future__ import annotations

import re
from dataclasses import dataclass, field
from pathlib import Path

# ---------------------------------------------------------------------------
# 常量与正则
# ---------------------------------------------------------------------------

# 位号（正点原子/野火等常见前缀；1~3 位数字，可带一位后缀字母）
DESIGNATOR_RE = re.compile(
    r"^(?:U|R|C|L|D|Q|Y|J|P|K|SW|FB|T|X|BZ|RV|BT|IC|CN|TP|LED|RN|RT|HS|F|LS|SP|VR|W)\d{1,3}[A-Z]?$"
)
# 引脚号：独立 1~3 位数字
PIN_NUM_RE = re.compile(r"^\d{1,3}$")
# 无框元件引脚号：限 1~2 位（3 位纯数字是电容 EIA 值码，如 '104'）
FREE_PIN_RE = re.compile(r"^\d{1,2}$")
# 粘连词：前导引脚号 + 标识符（如 '8VDDAMP' → 8 / VDDAMP），仅用于元件框边缘带
GLUED_PIN_RE = re.compile(r"^(\d{1,3})([A-Za-z][A-Za-z0-9_+/.-]{1,})$")
# 引脚标注词：'PI' + 位号 + 两位脚号（带前导 0），如 PIU601 = U6 引脚 1、
# PIC3702 = C37 引脚 2。正点原子等原理图在每个引脚旁标注，是部分符号
# （连接器/红外接收头等无独立数字引脚号）的引脚号唯一来源。
# 匹配按 'PI'+位号 前缀截断后验尾码（不用单一正则）：'PIC1103' 对位号
# C11 解析为脚 03，对 C110 不匹配（尾码 '3' 无前导 0），避免贪婪歧义。
PI_TAIL_RE = re.compile(r"^0(\d{1,2})$")
PI_PIN_DIST = 80.0       # PI 标注词与位号的最大关联距离（文本自带位号，可靠性强）
# 网络名：ASCII 字母开头，不含空格，长度 2~32（排除数字开头的元件值/频率等）
NETNAME_RE = re.compile(r"^[A-Za-z][A-Za-z0-9_+/.-]{1,31}$")
# 元件值：数字开头（10K2 / 100nF / 12.288MHz / 4.7K 等）
VALUE_RE = re.compile(r"^\d")
# 电源网络词（大写匹配）
_POWER_EXTRA = {"GND", "AGND", "DGND", "PGND", "EGND", "VCC", "VDD", "VSS", "VDDA", "VBAT", "VREF", "VIN", "AVDD", "DVDD", "AVCC", "DVCC", "VBUS"}
_POWER_VOLT_RE = re.compile(r"^\+?\d+(\.\d+)?V\d*$")
# 电源引脚名（用于 pin_type 推断）
_POWER_PIN_RE = re.compile(r"^(VDD|VSS|VCC|VEE|VBAT|VREF|GND|AVDD|DVDD|AVCC|DVCC).*$")

WIRE_LW_MIN = 0.3        # 导线线宽下限（图框/分栏线通常 ≤ 0.1）
SEG_SNAP = 2.5           # 线段端点网格化容差
PIN_SNAP = 3.0           # 引脚点吸附导线容差（精确命中）
PIN_NEAR = 8.0           # 引脚点邻近导线容差（模糊命中，低置信度）
LABEL_DIST = 6.0         # 网络标号贴线判定距离
EDGE_BAND = 7.0          # 元件框边缘带半宽（引脚号所在区域）
EDGE_OUTER = 12.0        # 框外侧引脚号距框边最大距离（引线中部标注 5~10pt）
EDGE_INNER = 8.0         # 框内侧引脚号最大深度（更深的是框内引脚名等）
EDGE_MIN = 2.0           # 距框边最小距离：贴边（< 2pt）的是网络标号/框线标注，非引脚号
BOX_MIN_DIM = 15.0       # 元件框最小边长
SYMBOL_MAX_DIM = 22.0    # 电阻等图形符号的最大边长（粗线小矩形，非元件框）
DESIG_BOX_DIST = 35.0    # 位号与元件框的关联距离
DESIG_PIN_DIST = 30.0    # 无框元件位号与引脚号的关联距离
VALUE_DIST = 35.0        # 位号与值的关联距离
PAGE_LONG_RATIO = 0.7    # 线长超过页面尺寸该比例视为图框线，丢弃

HIGH_CONF = 0.90         # 网络标号 / 电源符号命中的基准置信度
LINE_CONF = 0.75         # 线交点命中（自动命名网络）的基准置信度
NEAR_CONF = 0.50         # 邻近推断（未精确落线）的置信度
REVIEW_THRESHOLD = 0.70  # 低于该值必须进入人工核对清单


@dataclass
class _Word:
    text: str
    x0: float
    x1: float
    top: float
    bottom: float
    size: float = 0.0  # 字号（pt），0 表示未知

    @property
    def cx(self) -> float:
        return (self.x0 + self.x1) / 2.0

    @property
    def cy(self) -> float:
        return (self.top + self.bottom) / 2.0


@dataclass(eq=False)  # 按身份哈希，供空间索引进行集合去重
class _Seg:
    x0: float
    y0: float
    x1: float
    y1: float
    lw: float = 0.0

    @property
    def horizontal(self) -> bool:
        return abs(self.y1 - self.y0) <= SEG_SNAP and abs(self.x1 - self.x0) > 1e-6

    @property
    def vertical(self) -> bool:
        return abs(self.x1 - self.x0) <= SEG_SNAP and abs(self.y1 - self.y0) > 1e-6


@dataclass
class _Box:
    x0: float
    y0: float
    x1: float
    y1: float

    @property
    def band(self) -> float:
        """自适应边缘带半宽：小框 7pt，大框（如 MCU 符号）按短边 11% 放宽至 25pt。

        Altium 导出 PDF 的引脚号常标注在框外引线中部（距框边 5~20pt），
        固定窄带会大量丢脚；放宽后框内侧的引脚号标注也能覆盖。
        """
        return min(25.0, max(EDGE_BAND, 0.11 * min(self.x1 - self.x0, self.y1 - self.y0)))

    def contains(self, w: _Word) -> bool:
        return self.x0 <= w.cx <= self.x1 and self.y0 <= w.cy <= self.y1

    def near_edge(self, w: _Word) -> str | None:
        """词落在哪条边的引脚号带内，返回 'left'/'right'/'top'/'bottom'。

        每条边独立判定有效性：垂直边要求 x 在 [-EDGE_INNER, +EDGE_OUTER]
        带内且 y 不越框太多（水平边对称）。有效边中取距离最近者；
        若最近边距离 < EDGE_MIN（贴边网络标号）则退而取次近有效边——
        框角引脚号（如左列首脚 y 与框顶平齐）距相邻边可能 < 1pt。
        """
        dl, dr = w.cx - self.x0, self.x1 - w.cx
        dt, db = w.cy - self.y0, self.y1 - w.cy
        # d < 0 在框外（限 EDGE_OUTER），d > 0 在框内（限 EDGE_INNER）
        cand: list[tuple[float, str]] = []
        if -EDGE_OUTER <= dl <= EDGE_INNER and dt > -EDGE_INNER and db > -EDGE_INNER:
            cand.append((abs(dl), "left"))
        if -EDGE_OUTER <= dr <= EDGE_INNER and dt > -EDGE_INNER and db > -EDGE_INNER:
            cand.append((abs(dr), "right"))
        if -EDGE_OUTER <= dt <= EDGE_INNER and dl > -EDGE_INNER and dr > -EDGE_INNER:
            cand.append((abs(dt), "top"))
        if -EDGE_OUTER <= db <= EDGE_INNER and dl > -EDGE_INNER and dr > -EDGE_INNER:
            cand.append((abs(db), "bottom"))
        if not cand:
            return None
        cand.sort()
        dist, edge = cand[0]
        if dist < EDGE_MIN and len(cand) > 1:
            dist, edge = cand[1]  # 框角引脚：最近边是越界边，取次近的有效边
        return None if dist < EDGE_MIN else edge


@dataclass
class _PageData:
    """与解析库无关的页面中间结构（pdfplumber / PyMuPDF 统一转换）。"""
    width: float
    height: float
    words: list = field(default_factory=list)   # list[_Word]
    lines: list = field(default_factory=list)   # list[_Seg]
    rects: list = field(default_factory=list)   # list[dict]：x0/x1/top/bottom/linewidth
    curves: list = field(default_factory=list)  # list[dict]：x0/x1/top/bottom


class _UnionFind:
    def __init__(self):
        self.parent: dict[tuple, tuple] = {}

    def find(self, p: tuple) -> tuple:
        self.parent.setdefault(p, p)
        while self.parent[p] != p:
            self.parent[p] = self.parent[self.parent[p]]
            p = self.parent[p]
        return p

    def union(self, a: tuple, b: tuple) -> None:
        ra, rb = self.find(a), self.find(b)
        if ra != rb:
            self.parent[rb] = ra

    def groups(self) -> dict[tuple, list[tuple]]:
        out: dict[tuple, list[tuple]] = {}
        for p in self.parent:
            out.setdefault(self.find(p), []).append(p)
        return out


def _grid(p: tuple) -> tuple:
    return (round(p[0] / SEG_SNAP), round(p[1] / SEG_SNAP))


def _pt_seg_dist(px: float, py: float, seg: _Seg) -> float:
    """点到线段的最短距离（投影法，水平/垂直线段走快速路径）。"""
    ax, ay, bx, by = seg.x0, seg.y0, seg.x1, seg.y1
    if seg.horizontal:
        qx = min(max(px, min(ax, bx)), max(ax, bx))
        return ((px - qx) ** 2 + (py - ay) ** 2) ** 0.5
    if seg.vertical:
        qy = min(max(py, min(ay, by)), max(ay, by))
        return ((px - ax) ** 2 + (py - qy) ** 2) ** 0.5
    dx, dy = bx - ax, by - ay
    if dx == 0 and dy == 0:
        return ((px - ax) ** 2 + (py - ay) ** 2) ** 0.5
    t = ((px - ax) * dx + (py - ay) * dy) / (dx * dx + dy * dy)
    t = min(max(t, 0.0), 1.0)
    qx, qy = ax + t * dx, ay + t * dy
    return ((px - qx) ** 2 + (py - qy) ** 2) ** 0.5


class _SegIndex:
    """线段空间网格索引：点查询只扫邻近桶，把点-段匹配从 O(n·m) 降到近线性。

    桶边长 INDEX_CELL=8pt，查询 3×3 邻域即可覆盖任意距点 < 8pt 的线段
    （覆盖 PIN_NEAR / LABEL_DIST / PIN_SNAP / SEG_SNAP 全部容差）。
    """

    CELL = 8.0

    def __init__(self, segs: list[_Seg]):
        self.buckets: dict[tuple, list[_Seg]] = {}
        for s in segs:
            for key in self._cells(s):
                self.buckets.setdefault(key, []).append(s)

    def _cells(self, s: _Seg) -> set[tuple]:
        c = self.CELL
        keys = set()
        if s.horizontal:
            y = int(s.y0 // c)
            for ix in range(int(min(s.x0, s.x1) // c), int(max(s.x0, s.x1) // c) + 1):
                keys.add((ix, y))
        elif s.vertical:
            x = int(s.x0 // c)
            for iy in range(int(min(s.y0, s.y1) // c), int(max(s.y0, s.y1) // c) + 1):
                keys.add((x, iy))
        else:  # 斜线：沿长度步进采样
            length = ((s.x1 - s.x0) ** 2 + (s.y1 - s.y0) ** 2) ** 0.5
            steps = max(1, int(length / c) + 1)
            for i in range(steps + 1):
                t = i / steps
                keys.add((int((s.x0 + t * (s.x1 - s.x0)) // c),
                          int((s.y0 + t * (s.y1 - s.y0)) // c)))
        return keys

    def query(self, px: float, py: float) -> list[_Seg]:
        """返回与点 3×3 邻域桶相交的线段（可能重复，调用方按需去重）。"""
        cx, cy = int(px // self.CELL), int(py // self.CELL)
        out: list[_Seg] = []
        for ix in (cx - 1, cx, cx + 1):
            for iy in (cy - 1, cy, cy + 1):
                out.extend(self.buckets.get((ix, iy), ()))
        return out


# ---------------------------------------------------------------------------
# PDF 打开层：pdfplumber 优先，PyMuPDF 兜底
# ---------------------------------------------------------------------------

CHAR_X_GAP = 1.6      # 同词相邻字符最大 x 间隙
CHAR_SIZE_TOL = 0.5   # 同词字号容差


def _cluster_words(chars: list[dict]) -> list[_Word]:
    """从字符列表聚类出词：按字号分层 → 层内 y 聚行 → 行内 x 聚词。

    不直接用库的 extract_words/get_text("words")：Altium 导出 PDF 中
    引脚名（如 4.64pt）、引脚号、网络标号（如 3.0pt）字号不同且 x 区间
    交错重叠，库的词聚类会把紧排字符（间距 0.01pt）也拆成单字 word，
    导致 'PA0' → 'P'+'A'+'0'、引脚号 '34' → '3'+'4'。
    按字号分层后各层内字符 x 单调、间距规整，可稳定聚词。
    """
    layers: dict[float, list[dict]] = {}
    for c in chars:
        if not str(c.get("text", "")).strip():
            continue
        layers.setdefault(round(float(c.get("size") or 0.0) * 2) / 2, []).append(c)

    words: list[_Word] = []
    for layer in layers.values():
        layer.sort(key=lambda c: (c["top"], c["x0"]))
        # y 聚行：与行内最后字符 y 区间重叠 >= 50%（取较小字符高）视为同行
        rows: list[list[dict]] = []
        for c in layer:
            if rows:
                last = rows[-1][-1]
                ov = min(c["bottom"], last["bottom"]) - max(c["top"], last["top"])
                min_h = min(c["bottom"] - c["top"], last["bottom"] - last["top"])
                if ov > 0.5 * min_h:
                    rows[-1].append(c)
                    continue
            rows.append([c])
        # 行内 x 聚词：x 递增、间隙（含字符框微重叠）在容差内且字号相近。
        # CAD 导出 PDF 的字符框常互相重叠 0.01~0.1pt（紧排字距），gap 为
        # 微小负数时仍是同一词，必须允许。
        for row in rows:
            row.sort(key=lambda c: c["x0"])
            cur: list[dict] = []
            for c in row:
                if cur:
                    gap = c["x0"] - cur[-1]["x1"]
                    if -3.0 <= gap <= CHAR_X_GAP and abs(c["size"] - cur[-1]["size"]) <= CHAR_SIZE_TOL:
                        cur.append(c)
                        continue
                    _flush_word(cur, words)
                    cur = []
                cur.append(c)
            if cur:
                _flush_word(cur, words)
    words.sort(key=lambda w: (w.top, w.x0))
    return words


def _flush_word(cur: list[dict], out: list[_Word]) -> None:
    if not cur:
        return
    out.append(_Word(
        "".join(str(c["text"]) for c in cur),
        min(c["x0"] for c in cur), max(c["x1"] for c in cur),
        min(c["top"] for c in cur), max(c["bottom"] for c in cur),
        float(cur[0]["size"]),
    ))


_OVERLAY_DIST = 3.0  # 双层文本同位判定：词中心距


def _dedup_overlay_words(words: list[_Word]) -> list[_Word]:
    """双层 PDF 文本去重。

    CAD 导出 PDF 常叠加"完整词层 + 逐字符层"两份文本（位置几乎重合、
    字号略异），聚类后产生 'U12' 与 'U','1','2'、'10' 与 '010'（零填充）
    双份。规则：
    1) 多字符词覆盖的单字符词，按位置排序拼接后文本相等（纯数字容许
       前导 0 差异）→ 删除单字符组；
    2) 其余同文本（纯数字按去前导 0 归一化）且中心距 < 3pt 的词对 →
       保留一个。
    """
    drop: set[int] = set()

    # ---- 规则 1：多字符词吸收其覆盖的单字符词 ----
    singles = [w for w in words if len(w.text) == 1]
    multi = [w for w in words if len(w.text) >= 2]
    if singles and multi:
        bucket: dict[tuple, list[_Word]] = {}
        cell = 16.0
        for s in singles:
            bucket.setdefault((int(s.cx // cell), int(s.cy // cell)), []).append(s)
        for w in multi:
            pad = 2.0
            x0b, x1b = int((w.x0 - pad) // cell), int((w.x1 + pad) // cell)
            y0b, y1b = int((w.top - pad) // cell), int((w.bottom + pad) // cell)
            inner = [
                s for bx in range(x0b, x1b + 1) for by in range(y0b, y1b + 1)
                for s in bucket.get((bx, by), ())
                if w.x0 - pad <= s.cx <= w.x1 + pad and w.top - pad <= s.cy <= w.bottom + pad
            ]
            if not inner:
                continue
            inner.sort(key=lambda s: (s.cy, s.cx))
            joined = "".join(s.text for s in inner)
            wt, jt = w.text, joined
            if wt.isdigit() and jt.isdigit():
                wt, jt = wt.lstrip("0") or "0", jt.lstrip("0") or "0"
            if wt == jt:
                drop.update(id(s) for s in inner)

    rest = [w for w in words if id(w) not in drop]

    # ---- 规则 2：同位同文（数字归一化）词对去重 ----
    groups: dict[str, list[_Word]] = {}
    for w in rest:
        key = (w.text.lstrip("0") or "0") if w.text.isdigit() else w.text
        groups.setdefault(key, []).append(w)
    for grp in groups.values():
        if len(grp) < 2:
            continue
        keep = [grp[0]]
        for w in grp[1:]:
            if any(abs(w.cx - k.cx) < _OVERLAY_DIST and abs(w.cy - k.cy) < _OVERLAY_DIST
                   for k in keep):
                drop.add(id(w))
            else:
                keep.append(w)
    return [w for w in rest if id(w) not in drop]


def _load_pages(path: Path) -> list[_PageData]:
    try:
        import pdfplumber  # noqa: PLC0415
    except ImportError:
        pdfplumber = None  # type: ignore[assignment]
    if pdfplumber is not None:
        with pdfplumber.open(str(path)) as pdf:
            return [_page_from_plumber(pg) for pg in pdf.pages]
    try:
        import pymupdf  # noqa: PLC0415
    except ImportError:
        raise ImportError(
            "PDF 解析需要 pdfplumber 或 PyMuPDF，请安装其一: pip install pdfplumber"
        ) from None
    doc = pymupdf.open(str(path))
    try:
        return [_page_from_pymupdf(pg) for pg in doc]
    finally:
        doc.close()


def _page_from_plumber(pg) -> _PageData:
    chars = [
        {"text": c["text"], "x0": float(c["x0"]), "x1": float(c["x1"]),
         "top": float(c["top"]), "bottom": float(c["bottom"]),
         "size": float(c.get("size") or 0.0)}
        for c in pg.chars if c.get("upright", True)
    ]
    words = _dedup_overlay_words(_cluster_words(chars))
    lines = [
        _Seg(min(l["x0"], l["x1"]), min(l["top"], l["bottom"]),
             max(l["x0"], l["x1"]), max(l["top"], l["bottom"]),
             float(l.get("linewidth") or 0.0))
        for l in pg.lines
    ]
    rects = [
        {"x0": r["x0"], "x1": r["x1"], "top": r["top"], "bottom": r["bottom"],
         "linewidth": r.get("linewidth") or 0.0}
        for r in pg.rects
    ]
    curves = [
        {"x0": c["x0"], "x1": c["x1"], "top": c["top"], "bottom": c["bottom"]}
        for c in pg.curves
    ]
    return _PageData(float(pg.width), float(pg.height), words, lines, rects, curves)


def _pymupdf_chars(pg) -> list[dict]:
    """PyMuPDF rawdict → 统一字符列表（仅水平文本，旋转文本与 pdfplumber 路径一致地跳过）。"""
    out: list[dict] = []
    for block in pg.get_text("rawdict").get("blocks", []):
        if block.get("type") != 0:
            continue
        for line in block.get("lines", []):
            _dx, dy = line.get("dir", (1, 0))
            if abs(dy) > 0.01:
                continue
            for span in line.get("spans", []):
                size = float(span.get("size") or 0.0)
                for ch in span.get("chars", []):
                    x0, y0, x1, y1 = ch["bbox"]
                    out.append({"text": ch["c"], "x0": float(x0), "x1": float(x1),
                                "top": float(y0), "bottom": float(y1), "size": size})
    return out


def _page_from_pymupdf(pg) -> _PageData:
    words = _dedup_overlay_words(_cluster_words(_pymupdf_chars(pg)))
    lines: list[_Seg] = []
    rects: list[dict] = []
    curves: list[dict] = []
    for path in pg.get_drawings():
        lw = float(path.get("width") or 0.0)
        r = path["rect"]
        item_kinds = {it[0] for it in path.get("items", [])}
        box = {"x0": r.x0, "x1": r.x1, "top": r.y0, "bottom": r.y1, "linewidth": lw}
        if item_kinds <= {"l"} and (r.width < 3 or r.height < 3):
            lines.append(_Seg(r.x0, r.y0, r.x1, r.y1, lw))
        elif item_kinds == {"re"}:
            rects.append(box)
        elif item_kinds & {"c"}:
            curves.append({"x0": r.x0, "x1": r.x1, "top": r.y0, "bottom": r.y1})
    return _PageData(float(pg.rect.width), float(pg.rect.height), words, lines, rects, curves)


# ---------------------------------------------------------------------------
# 每页解析
# ---------------------------------------------------------------------------

def _collect_wires(page: _PageData, warnings: list[str]) -> tuple[list[_Seg], list[_Box]]:
    """收集导线段与元件框。返回 (线段, 框)。

    - 导线：linewidth >= WIRE_LW_MIN 的 line + 细长 rect；超长线（图框/分栏）丢弃
    - 若页面不存在粗线，则降级为收集全部非超长线并告警（兼容无图框 PDF）
    - 元件框：尺寸 >= BOX_MIN_DIM 且面积 < 30% 页面的 rect；
      粗线小矩形（电阻符号，max 边 < SYMBOL_MAX_DIM 且 lw >= WIRE_LW_MIN）排除
    """
    raw = [s for s in page.lines if s.lw >= WIRE_LW_MIN]
    degraded = False
    if not raw:
        raw = list(page.lines)
        degraded = True
    for r in page.rects:
        w = r["x1"] - r["x0"]
        h = r["bottom"] - r["top"]
        lw = r.get("linewidth") or 0.0
        if lw >= WIRE_LW_MIN and (w < 3 or h < 3):
            raw.append(_Seg(r["x0"], r["top"], r["x1"], r["bottom"], lw))
    if degraded:
        warnings.append("页面未发现粗线宽导线，已按全部线段降级解析（可能混入图框线）")
    # 超长线过滤（图框/分栏线：长度 > 70% 页面对应尺寸）
    long_lim_x = page.width * PAGE_LONG_RATIO
    long_lim_y = page.height * PAGE_LONG_RATIO
    segs = [
        s for s in raw
        if not (s.horizontal and abs(s.x1 - s.x0) > long_lim_x)
        and not (s.vertical and abs(s.y1 - s.y0) > long_lim_y)
    ]
    if not segs:
        warnings.append("页面未发现导线线段（可能为纯图框页或扫描页）")

    boxes = []
    page_area = page.width * page.height
    for r in page.rects:
        w = r["x1"] - r["x0"]
        h = r["bottom"] - r["top"]
        lw = r.get("linewidth") or 0.0
        if w < BOX_MIN_DIM or h < BOX_MIN_DIM:
            continue
        if w * h > 0.3 * page_area:
            continue
        if lw >= WIRE_LW_MIN and max(w, h) < SYMBOL_MAX_DIM:
            continue  # 电阻等图形符号
        boxes.append(_Box(r["x0"], r["top"], r["x1"], r["bottom"]))
    return segs, boxes


def _pick_designators(words: list[_Word]) -> list[_Word]:
    return [w for w in words if DESIGNATOR_RE.match(w.text)]


def _link_boxes(desig_words: list[_Word], boxes: list[_Box]) -> dict[str, list[_Box]]:
    """位号 → 元件框列表：多部件符号（MCU 拆 Part A/B/C/D）同位号标注多次，
    每个标注关联自己的框，合并去重后一并返回。

    框外距离关联采用互最近（每个框只归距它最近的位号）：电容等无框元件的
    位号常落在邻近 IC 框 35pt 内，纯距离阈值会把它误关联到 IC 框，导致
    同一框被两个位号共享（引脚号重复消费，连接成倍增长）。
    """
    link: dict[str, list[_Box]] = {}
    claimed: set[int] = set()  # 已被包含关联占用的框
    for dw in desig_words:
        inside = [b for b in boxes if b.contains(dw)]
        if inside:
            b = min(inside, key=lambda b: (b.x1 - b.x0) * (b.y1 - b.y0))
            cur = link.setdefault(dw.text, [])
            if b not in cur:
                cur.append(b)
            claimed.add(id(b))
    for b in boxes:
        if id(b) in claimed:
            continue
        best, best_d = None, DESIG_BOX_DIST
        for dw in desig_words:
            dx = max(b.x0 - dw.cx, 0.0, dw.cx - b.x1)
            dy = max(b.y0 - dw.cy, 0.0, dw.cy - b.y1)
            d = (dx * dx + dy * dy) ** 0.5
            if d < best_d:
                best, best_d = dw, d
        if best is not None:
            cur = link.setdefault(best.text, [])
            if b not in cur:
                cur.append(b)
    return link


def _pin_type_of(name: str) -> str:
    return "POWER" if _POWER_PIN_RE.match((name or "").upper()) else "UNKNOWN"


def _box_pins(box: _Box, words: list[_Word]) -> tuple[list[dict], set[int]]:
    """识别元件框边缘的引脚：纯数字词 + 前导粘连词。

    返回 ([{pin, pin_name, px, py}], 已消费的词索引集合)，
    px/py 为连接点（框边上的投影）。
    """
    pins: list[dict] = []
    used: set[int] = set()
    seen: set[str] = set()
    # 粗滤带必须覆盖 near_edge 的完整判定带（框外 EDGE_OUTER / 框内 EDGE_INNER），
    # 否则框外 7~12pt 的引脚号（如小 IC 框 band=7 时引脚号在 7.3pt）会被提前滤掉
    band = max(box.band, EDGE_OUTER)
    for i, w in enumerate(words):
        num, name = None, ""
        if PIN_NUM_RE.match(w.text):
            num = w.text
        elif m := GLUED_PIN_RE.match(w.text):
            num, name = m.group(1), m.group(2)
        if num is None:
            continue
        if not (box.y0 - band <= w.cy <= box.y1 + band
                and box.x0 - band <= w.cx <= box.x1 + band):
            continue
        edge = box.near_edge(w)
        if edge is None:
            continue  # 框中央的数字（如表格编号）不算引脚
        if num in seen:
            continue
        seen.add(num)
        used.add(i)
        if edge == "left":
            px, py = box.x0, w.cy
        elif edge == "right":
            px, py = box.x1, w.cy
        elif edge == "top":
            px, py = w.cx, box.y0
        else:
            px, py = w.cx, box.y1
        pins.append({"pin": num, "pin_name": name, "px": px, "py": py})
    # 引脚名补充：框内、与连接点最近的非数字词（仅给还没有名的引脚）
    for p in pins:
        if p["pin_name"]:
            continue
        best, best_d = None, 14.0
        for w in words:
            if PIN_NUM_RE.match(w.text) or DESIGNATOR_RE.match(w.text):
                continue
            if not (box.x0 <= w.cx <= box.x1 and box.y0 <= w.cy <= box.y1):
                continue
            d = ((w.cx - p["px"]) ** 2 + (w.cy - p["py"]) ** 2) ** 0.5
            if d < best_d:
                best, best_d = w, d
        if best is not None:
            p["pin_name"] = best.text
    pins.sort(key=lambda p: _natural_key(p["pin"]))
    return pins, used


def _pi_pins(desig: str, desig_word: _Word, words: list[_Word],
            pinned: set[int], blist: list[_Box]) -> tuple[list[dict], set[int]]:
    """解析 'PI<位号><脚号>' 引脚标注词（如 PIU601 = U6 引脚 01）。

    部分符号（连接器 / 红外接收头 / 稳压器等）在 PDF 中没有独立的数字
    引脚号词，唯一引脚线索是紧贴引脚的 PI 标注。文本自带位号，可靠性强，
    关联距离放宽到 PI_PIN_DIST；有框时连接点取词在框边上的投影。
    """
    pins: list[dict] = []
    used: set[int] = set()
    seen: set[str] = set()
    prefix = "PI" + desig
    for i, w in enumerate(words):
        if i in pinned or not w.text.startswith(prefix):
            continue
        m = PI_TAIL_RE.match(w.text[len(prefix):])
        if not m:
            continue
        if ((w.cx - desig_word.cx) ** 2 + (w.cy - desig_word.cy) ** 2) ** 0.5 > PI_PIN_DIST:
            continue
        num = str(int(m.group(1)))  # 去前导 0（'01' → '1'）
        if num in seen:
            continue
        seen.add(num)
        used.add(i)
        px = py = None
        for b in blist:
            edge = b.near_edge(w)
            if edge == "left":
                px, py = b.x0, w.cy
            elif edge == "right":
                px, py = b.x1, w.cy
            elif edge == "top":
                px, py = w.cx, b.y0
            elif edge == "bottom":
                px, py = w.cx, b.y1
            if px is not None:
                break
        if px is None:
            px, py = w.cx, w.cy  # 无框：词中心即连接点
        pins.append({"pin": num, "pin_name": "", "px": px, "py": py})
    return pins, used


def _free_pins(desig: _Word, words: list[_Word], pinned: set[int]) -> list[dict]:
    """无框元件（电阻/电容等）：位号邻域的独立数字词作为引脚，词中心即连接点。

    电阻/电容/二极管/晶振等无框符号引脚数 <= 4，超出视为吸附噪声丢弃；
    有框元件已消费的引脚号词（pinned）不再复用。
    引脚号限 1~2 位：3 位纯数字（'104'/'102'）是电容 EIA 值码，
    无框元件（R/C/L/D/连接器）不存在 3 位引脚号。
    """
    pins: list[dict] = []
    seen: set[str] = set()
    cand = []
    for i, w in enumerate(words):
        if i in pinned or not FREE_PIN_RE.match(w.text):
            continue
        d = ((w.cx - desig.cx) ** 2 + (w.cy - desig.cy) ** 2) ** 0.5
        if d <= DESIG_PIN_DIST and w.text not in seen:
            seen.add(w.text)
            cand.append((d, i, w))
    cand.sort(key=lambda t: t[0])
    for _d, i, w in cand[:4]:
        pinned.add(i)
        pins.append({"pin": w.text, "pin_name": "", "px": w.cx, "py": w.cy})
    pins.sort(key=lambda p: _natural_key(p["pin"]))
    return pins


def _pick_value(desig: _Word, words: list[_Word], index: _SegIndex) -> str:
    """位号邻域最近的非网络标号文本作为元件值。"""
    best, best_d = None, VALUE_DIST
    for w in words:
        if w is desig or DESIGNATOR_RE.match(w.text) or PIN_NUM_RE.match(w.text):
            continue
        if not ((VALUE_RE.match(w.text) and len(w.text) >= 3)
                or (len(w.text) >= 6 and any(ch.isdigit() for ch in w.text))):
            continue  # 值以数字开头（10K/100nF），或为含数字的长型号串（STM32F103ZET6）
        if any(_pt_seg_dist(w.cx, w.cy, s) < LABEL_DIST for s in index.query(w.cx, w.cy)):
            continue  # 贴线的是网络标号
        d = ((w.cx - desig.cx) ** 2 + (w.cy - desig.cy) ** 2) ** 0.5
        if d < best_d:
            best, best_d = w, d
    return best.text if best else ""


def _parse_page(page: _PageData, page_label: str) -> dict:
    """单页解析，返回中间结果（components/nets/review/warnings）。"""
    warnings: list[str] = []
    segs, boxes = _collect_wires(page, warnings)
    words = page.words

    # junction 圆点：小尺寸曲线（半径 < 2.5pt）中心，作为强制连通节点
    junctions = [
        ((c["x0"] + c["x1"]) / 2.0, (c["top"] + c["bottom"]) / 2.0)
        for c in page.curves
        if (c["x1"] - c["x0"]) < 5.0 and (c["bottom"] - c["top"]) < 5.0
    ]

    # ---- 并查集：线段端点（经空间索引匹配，近线性）----
    uf = _UnionFind()
    index = _SegIndex(segs)
    for s in segs:
        uf.union(_grid((s.x0, s.y0)), _grid((s.x1, s.y1)))
    # 端点落在其他线段上（T 型 / 共线重叠）→ 合并
    for s in segs:
        cands = {t for ex, ey in ((s.x0, s.y0), (s.x1, s.y1))
                 for t in index.query(ex, ey)}
        cands.discard(s)
        for t in cands:
            if (_pt_seg_dist(s.x0, s.y0, t) <= SEG_SNAP
                    or _pt_seg_dist(s.x1, s.y1, t) <= SEG_SNAP):
                uf.union(_grid((s.x0, s.y0)), _grid((t.x0, t.y0)))
    # junction 点：强制合并所有覆盖它的线段
    for jx, jy in junctions:
        jk = _grid((jx, jy))
        for t in index.query(jx, jy):
            if _pt_seg_dist(jx, jy, t) <= PIN_SNAP:
                uf.union(jk, _grid((t.x0, t.y0)))

    # ---- 元件与引脚（两轮：先有框元件锁定框边缘引脚号，再无框元件吸收剩余数字词）----
    desig_words = _pick_designators(words)
    desig_box = _link_boxes(desig_words, boxes)
    uniq_desigs = list(dict.fromkeys(w.text for w in desig_words))
    pinned: set[int] = set()
    comp_pins: dict[str, list[dict]] = {}
    for dw in desig_words:  # 第一轮：有框元件（多部件同位号多框合并）
        blist = desig_box.get(dw.text) or []
        if not blist:
            continue
        all_pins: list[dict] = []
        seen_nums: set[str] = set()
        used_all: set[int] = set()
        for box in blist:
            pins, used = _box_pins(box, words)
            used_all |= used
            for p in pins:
                if p["pin"] not in seen_nums:
                    seen_nums.add(p["pin"])
                    all_pins.append(p)
        # PI 标注兜底：补充无独立数字引脚号的引脚（连接器/小 IC 等）
        pi_pins, pi_used = _pi_pins(dw.text, dw, words, used_all, blist)
        used_all |= pi_used
        for p in pi_pins:
            if p["pin"] not in seen_nums:
                seen_nums.add(p["pin"])
                all_pins.append(p)
        pinned |= used_all
        comp_pins[dw.text] = all_pins
    for dw in desig_words:  # 第二轮：无框元件
        if desig_box.get(dw.text):
            continue
        if dw.text in comp_pins:
            continue
        free = _free_pins(dw, words, pinned)
        pi_pins, pi_used = _pi_pins(dw.text, dw, words, pinned, [])
        pinned |= pi_used
        for p in pi_pins:
            if all(p["pin"] != q["pin"] for q in free):
                free.append(p)
        comp_pins[dw.text] = free
    for desig in uniq_desigs:
        if not comp_pins.get(desig):
            warnings.append(f"{page_label}: 元件 {desig} 未识别到引脚（无框符号可能未标引脚号）")

    # ---- 网络标号：贴线、非位号/引脚/值、在框外 ----
    labels: list[tuple[str, tuple]] = []
    power_labels: list[tuple[str, tuple]] = []
    for i, w in enumerate(words):
        if i in pinned or DESIGNATOR_RE.match(w.text):
            continue
        if not NETNAME_RE.match(w.text):
            continue
        if any(b.contains(w) or (b.near_edge(w) is not None) for b in boxes):
            continue
        hit = next(
            (s for s in index.query(w.cx, w.cy) if _pt_seg_dist(w.cx, w.cy, s) < LABEL_DIST),
            None,
        )
        if hit is None:
            continue
        key = _grid((w.cx, w.cy))
        upper = w.text.upper()
        if upper in _POWER_EXTRA or _POWER_VOLT_RE.match(upper):
            power_labels.append((w.text, key))
        else:
            labels.append((w.text, key))

    # 标号锚点 union 到覆盖线段
    for _name, (lx, ly) in labels + power_labels:
        for t in index.query(lx * SEG_SNAP, ly * SEG_SNAP):
            if _pt_seg_dist(lx * SEG_SNAP, ly * SEG_SNAP, t) < LABEL_DIST:
                uf.union((lx, ly), _grid((t.x0, t.y0)))
                break

    # ---- 组命名 ----
    name_by_group: dict[tuple, str] = {}
    for name, key in power_labels + labels:
        g = uf.find(key)
        name_by_group.setdefault(g, name)

    # ---- 引脚连接 ----
    connections: list[dict] = []  # {designator, pin, pin_name, group, conf, method, note}
    for desig, pins in comp_pins.items():
        for p in pins:
            px, py = p["px"], p["py"]
            cands = index.query(px, py)
            exact = next((s for s in cands if _pt_seg_dist(px, py, s) <= PIN_SNAP), None)
            near, near_d = None, PIN_NEAR
            if exact is None:
                for s in cands:
                    d = _pt_seg_dist(px, py, s)
                    if d < near_d:
                        near, near_d = s, d
            seg = exact if exact is not None else near
            if seg is None:
                continue  # 悬空
            g = uf.find(_grid((seg.x0, seg.y0)))
            if exact is not None:
                conf, method = HIGH_CONF, "net_label" if g in name_by_group else "line_intersection"
                note = "线与引脚交点明确" + (f"，网络标号 {name_by_group[g]}" if g in name_by_group else "（网络自动命名）")
            else:
                conf, method = NEAR_CONF, "net_label" if g in name_by_group else "line_intersection"
                note = f"引脚未精确落线（距最近导线 {near_d:.1f}pt），按邻近推断，请人工核对"
            # 引脚名与网络名一致 → 提升置信度
            if p["pin_name"] and g in name_by_group and name_by_group[g].upper() == p["pin_name"].upper():
                conf, method = 0.95, "pin_name_match"
                note = f"引脚名 {p['pin_name']} 与网络名 {name_by_group[g]} 一致"
            connections.append({
                "designator": desig, "pin": p["pin"], "pin_name": p["pin_name"],
                "group": g, "conf": round(conf, 2), "method": method, "note": note,
                "px": px, "py": py,
            })

    return {
        "page_label": page_label,
        "designators": [w.text for w in desig_words],
        "comp_pins": comp_pins,
        "connections": connections,
        "name_by_group": name_by_group,
        "values": {w.text: _pick_value(w, words, index) for w in desig_words},
        "warnings": warnings,
    }


# ---------------------------------------------------------------------------
# 主入口
# ---------------------------------------------------------------------------

def parse(schematic_path: str) -> dict:
    """解析 PDF 原理图，返回通用网表中间结构 + pdf_meta（置信度与核对数据）。"""
    path = Path(schematic_path)
    pages = _load_pages(path)

    total_words = sum(len(p.words) for p in pages)
    if total_words < 20:
        raise ValueError(
            "PDF 文字层缺失（疑似扫描件）：需要 OCR，当前不支持，请提供矢量 PDF 或源文件"
        )

    # BOM/表格页跳过：无元件框 + 大量表格线/文本（BOM 页会产生成百上千条假网络）
    warnings: list[str] = []
    active_pages: list[tuple[int, _PageData]] = []
    for i, pg in enumerate(pages, start=1):
        segs, boxes = _collect_wires(pg, [])
        if not boxes and (len(segs) > 300 or len(pg.words) > 2000):
            warnings.append(f"第{i}页 疑似 BOM/表格页（无元件框），已跳过")
            continue
        active_pages.append((i, pg))

    pages_res = [
        _parse_page(pg, f"第{i}页") for i, pg in active_pages
    ]

    for pr in pages_res:
        warnings.extend(pr["warnings"])

    # ---- 合并元件（跨页同位号）----
    components: dict[str, dict] = {}
    for pr in pages_res:
        for desig in pr["designators"]:
            comp = components.setdefault(desig, {
                "designator": desig,
                "value": pr["values"].get(desig, ""),
                "footprint": "",
                "library_ref": "pdf-extract",
                "description": "从 PDF 原理图推断（几何 + 文字启发式）",
                "parameters": {},
                "pins": [],
                "_pin_keys": set(),
            })

    # ---- 连接 → 网络 ----
    # 全局组名（跨页：同名标号的组在各自页面独立成组，按网络名合并）
    nets: dict[str, dict] = {}
    conn_records: list[dict] = []
    for pr in pages_res:
        name_by_group = pr["name_by_group"]
        for conn in pr["connections"]:
            g = conn["group"]
            net_name = name_by_group.get(g) or f"Net{conn['designator']}_{conn['pin']}"
            auto = g not in name_by_group
            net = nets.setdefault(net_name, {
                "name": net_name, "auto_named": auto,
                "source_sheets": [], "terminals": [], "_term_keys": set(),
            })
            if pr["page_label"] not in net["source_sheets"]:
                net["source_sheets"].append(pr["page_label"])
            rec = dict(conn)
            rec["net"] = net_name
            conn_records.append(rec)
            term_key = (conn["designator"], conn["pin"])
            if term_key not in net["_term_keys"]:
                net["_term_keys"].add(term_key)
                net["terminals"].append({
                    "designator": conn["designator"], "pin": conn["pin"],
                    "pin_name": conn["pin_name"], "pin_type": _pin_type_of(conn["pin_name"]),
                    "confidence": conn["conf"], "method": conn["method"], "note": conn["note"],
                })

    # 悬空网络过滤：自动命名且仅 1 个端点的网络 = 单根引脚线（无标号、
    # 另一端断线/电源符号未连通），无连接价值，按悬空处理不计入连接与
    # 置信度统计。有标号的网络（named）即使单端点也保留——线上有真实
    # 网络标号，断线应进入人工核对清单。
    alive_conns: list[dict] = []
    for c in conn_records:
        net = nets[c["net"]]
        if net["auto_named"] and len(net["terminals"]) <= 1:
            continue
        alive_conns.append(c)
    for n in [n for n in nets.values() if n["auto_named"] and len(n["terminals"]) <= 1]:
        del nets[n["name"]]

    for c in alive_conns:
        comp = components.get(c["designator"])
        if comp is not None and (c["pin"], c["net"]) not in comp["_pin_keys"]:
            comp["_pin_keys"].add((c["pin"], c["net"]))
            comp["pins"].append({
                "pin": c["pin"], "pin_name": c["pin_name"],
                "pin_type": _pin_type_of(c["pin_name"]), "net": c["net"],
                "confidence": c["conf"], "method": c["method"], "note": c["note"],
            })

    # 未连接引脚也写入元件（net=null，PDF 推断不出悬空语义时仍保留引脚号）
    # 悬空引脚保留（net=null）：引脚号已识别但未连通到任何网络（断线/
    # 电源符号未吸附），对下游 S4 而言"知道引脚存在但网络未知"优于丢失
    alive_pairs = {(c["designator"], c["pin"]) for c in alive_conns}
    for pr in pages_res:
        for desig, pins in pr["comp_pins"].items():
            comp = components.get(desig)
            if comp is None:
                continue
            for p in pins:
                if (desig, p["pin"]) in alive_pairs or (p["pin"], None) in comp["_pin_keys"]:
                    continue
                comp["_pin_keys"].add((p["pin"], None))
                comp["pins"].append({
                    "pin": p["pin"], "pin_name": p["pin_name"],
                    "pin_type": _pin_type_of(p["pin_name"]), "net": None,
                })

    unconnected = 0
    for pr in pages_res:
        for desig, pins in pr["comp_pins"].items():
            unconnected += sum(1 for p in pins if (desig, p["pin"]) not in alive_pairs)

    # ---- 置信度与核对清单 ----
    connected = alive_conns
    overall = round(sum(c["conf"] for c in connected) / len(connected), 3) if connected else 0.0
    low_items = [c for c in connected if c["conf"] < REVIEW_THRESHOLD]
    mid_items = [c for c in connected if REVIEW_THRESHOLD <= c["conf"] < 0.95]

    # review 条目：目标 = 同网络其他端点（最多 3 个）
    net_terminals: dict[str, list[str]] = {}
    for c in connected:
        net_terminals.setdefault(c["net"], []).append(f"{c['designator']}.{c['pin']}")

    def _review_row(c: dict) -> dict:
        targets = [t for t in net_terminals[c["net"]] if t != f"{c['designator']}.{c['pin']}"]
        return {
            "pin": f"{c['designator']}.{c['pin']}",
            "pin_name": c["pin_name"],
            "net": c["net"],
            "target": "、".join(targets[:3]) if targets else "（无其他端点）",
            "confidence": c["conf"],
            "method": c["method"],
            "note": c["note"],
            "suggestion": _suggest(c),
        }

    review_low = [_review_row(c) for c in sorted(low_items, key=lambda c: c["conf"])]
    review_mid = [_review_row(c) for c in sorted(mid_items, key=lambda c: c["conf"])]

    if low_items:
        warnings.append(f"低置信度连接 {len(low_items)} 条（< 0.7），已写入人工核对清单")
    if overall < REVIEW_THRESHOLD and connected:
        warnings.append(f"整体置信度 {overall} < 0.7，请人工全面核对网表")
    if unconnected:
        warnings.append(f"{unconnected} 个引脚未吸附到导线，未生成连接")

    # 清理内部键并排序
    for comp in components.values():
        comp.pop("_pin_keys", None)
        comp["pins"].sort(key=lambda p: _natural_key(p["pin"]))
    net_list = sorted(nets.values(), key=lambda n: _natural_key(n["name"]))
    for net in net_list:
        net.pop("_term_keys", None)
        net["terminals"].sort(
            key=lambda t: (t["designator"], _natural_key(t["pin"]))
        )

    return {
        "components": sorted(components.values(), key=lambda c: _natural_key(c["designator"])),
        "nets": net_list,
        "warnings": warnings,
        "pdf_meta": {
            "source_format": "pdf",
            "confidence": overall,
            "low_confidence_count": len(low_items),
            "review_low": review_low,
            "review_mid": review_mid,
        },
    }


def _suggest(c: dict) -> str:
    """按判定依据生成人工核对建议（中文）。"""
    if c["conf"] < REVIEW_THRESHOLD:
        return f"请人工确认 {c['designator']}.{c['pin']}"
        f"（{c['pin_name'] or '引脚名未知'}）是否连接到网络 {c['net']}"
    return f"建议在 S4 电路核查阶段重点核对 {c['designator']}.{c['pin']} 与 {c['net']} 的连接"


def _natural_key(s: str):
    """数字感知排序键：'2' < '10'。"""
    return [int(t) if t.isdigit() else t for t in re.split(r"(\d+)", str(s))]
