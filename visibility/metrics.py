# -*- coding: utf-8 -*-
"""
visibility/metrics.py — 原始回答 → 指标。

指标定义写死在这里，改定义要改这一个文件，别在别处重算。
四个指标正好对应首屏面板上已有的四块：

  mention_rate    提及率 = 提到该品牌的问题数 / 有效问题数
  avg_rank        平均位次 = 被提及时，该品牌在答案中首次出现的品牌序位（1 起）
  citation_share  引用份额 = 该品牌官网域名 / 全部引用域名
  source_mix      来源结构 = 引用域名按类型分桶的占比
"""
import re
from urllib.parse import urlparse

from .config import SOURCE_BUCKETS


def domain(url):
    try:
        h = (urlparse(url).hostname or "").lower()
    except ValueError:
        return ""
    return h[4:] if h.startswith("www.") else h


def bucket(dom, own_sites):
    """把一个引用域名归到来源桶。own_sites: {域名: 品牌名}"""
    if not dom:
        return "其他"
    if dom in own_sites:
        return "官网"
    for name, doms in SOURCE_BUCKETS.items():
        for d in doms:
            if dom == d or dom.endswith("." + d):
                return name
    return "其他"


def _find_first(text_low, aliases):
    """返回该品牌在正文里第一次出现的字符位置，没出现返回 None。"""
    best = None
    for a in aliases:
        m = re.search(r"\b" + re.escape(a.lower()) + r"\b", text_low)
        if m and (best is None or m.start() < best):
            best = m.start()
    return best


def score(records, brands):
    """
    records: [{"engine":..., "text":..., "citations":[...]}, ...]，同一品类同一批次
    brands:  config.CATEGORIES[slug]["brands"]

    返回 {"engines": {...}, "overall": {...}, "sources": {...}, "answered": n}
    """
    own_sites = {}
    for name, meta in brands.items():
        if meta.get("site"):
            own_sites[meta["site"]] = name

    by_engine = {}
    src_counts = {}
    src_total = 0

    for r in records:
        eng = r["engine"]
        text = (r.get("text") or "").strip()
        st = by_engine.setdefault(eng, {
            "answered": 0,
            "brands": {n: {"hits": 0, "rank_sum": 0, "cites": 0} for n in brands},
            "cites": 0,
        })
        if not text:
            continue                       # 空回答不计入分母
        st["answered"] += 1
        low = text.lower()

        # 位次：按首次出现位置排序，得出该答案里的品牌序位
        firsts = []
        for name, meta in brands.items():
            pos = _find_first(low, meta["aliases"])
            if pos is not None:
                firsts.append((pos, name))
        firsts.sort()
        for rank, (_, name) in enumerate(firsts, start=1):
            st["brands"][name]["hits"] += 1
            st["brands"][name]["rank_sum"] += rank

        # 引用
        for url in (r.get("citations") or []):
            d = domain(url)
            if not d:
                continue
            st["cites"] += 1
            src_total += 1
            b = bucket(d, own_sites)
            src_counts[b] = src_counts.get(b, 0) + 1
            if d in own_sites:
                st["brands"][own_sites[d]]["cites"] += 1

    def pack(st):
        n = st["answered"] or 1
        out = {}
        for name, b in st["brands"].items():
            out[name] = {
                "mention_rate": round(b["hits"] / n * 100, 1),
                "avg_rank": round(b["rank_sum"] / b["hits"], 2) if b["hits"] else None,
                "citation_share": round(b["cites"] / st["cites"] * 100, 1) if st["cites"] else 0.0,
                "hits": b["hits"],
            }
        return {"answered": st["answered"], "citations": st["cites"], "brands": out}

    engines = {e: pack(st) for e, st in by_engine.items()}

    # overall：按各引擎的有效问题数加权
    total_answered = sum(s["answered"] for s in engines.values())
    overall = {}
    for name in brands:
        hits = sum(s["brands"][name]["hits"] for s in engines.values())
        overall[name] = {
            "mention_rate": round(hits / total_answered * 100, 1) if total_answered else 0.0,
            "hits": hits,
        }

    sources = {k: round(v / src_total * 100, 1) for k, v in src_counts.items()} if src_total else {}

    return {
        "engines": engines,
        "overall": overall,
        "sources": dict(sorted(sources.items(), key=lambda kv: -kv[1])),
        "answered": total_answered,
        "citations": src_total,
    }
