#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
build_visibility_snapshot.py — 原始采样档 → 首屏用的可见度快照。

    python -m visibility.collect outdoor-power-us     # 先采集（要 API key）
    python build_visibility_snapshot.py               # 再构建

产物：assets/data/visibility_snapshot.js
    window.SQ_VISIBILITY = {...};

和 build_seo.py / build_stores_lite.py 一样：纯静态产物、幂等、零第三方依赖。
内容没变时重复运行不产生 diff。

--check 只报告会写什么，不写盘。
"""
import json
import sys
import datetime
from pathlib import Path

from visibility import config, collect, metrics

ROOT = Path(__file__).resolve().parent
OUT = ROOT / "assets" / "data" / "visibility_snapshot.js"

# 公开展示用周频，付费客户用日频 —— 见 README 里的成本说明
HISTORY_DAYS = 12          # 趋势线最多回看多少个采样批次


def build_category(slug):
    days = sorted(p.stem for p in (config.RAW / slug).glob("*.jsonl")) \
        if (config.RAW / slug).exists() else []
    if not days:
        return None

    meta = config.CATEGORIES[slug]
    brands = meta["brands"]

    series = []
    for day in days[-HISTORY_DAYS:]:
        recs = collect.load(slug, day)
        if not recs:
            continue
        m = metrics.score(recs, brands)
        series.append({"date": day, **m})

    if not series:
        return None

    latest = series[-1]
    return {
        "slug": slug,
        "label": meta["label"],
        "market": meta["market"],
        "latest_date": latest["date"],
        "questions": latest["answered"],
        "citations": latest["citations"],
        "engines": sorted(latest["engines"].keys()),
        "brands": list(brands.keys()),
        # 首屏只要这四块，和面板上的四个 KPI 一一对应
        "overall": latest["overall"],
        "by_engine": {e: v["brands"] for e, v in latest["engines"].items()},
        "sources": latest["sources"],
        "trend": [{"date": s["date"],
                   "overall": {b: s["overall"][b]["mention_rate"] for b in brands}}
                  for s in series],
    }


def main():
    check = "--check" in sys.argv
    cats = {}
    for slug in config.CATEGORIES:
        c = build_category(slug)
        if c:
            cats[slug] = c
        else:
            print("· %s：还没有采样档，跳过。先跑 python -m visibility.collect %s"
                  % (slug, slug))

    if not cats:
        print("没有任何可用采样，未写盘。")
        return 1

    payload = {
        "updated": datetime.date.today().isoformat(),
        "source": "visibility/ 采样档",
        "note": "公开快照按周采样；付费项目按日采样。",
        "categories": cats,
    }
    text = "window.SQ_VISIBILITY = " + json.dumps(payload, ensure_ascii=False,
                                                  sort_keys=True) + ";\n"

    old = OUT.read_text(encoding="utf-8") if OUT.exists() else ""
    if old == text:
        print("无变化：%s" % OUT.name)
        return 0
    if check:
        print("会写入 %s（%d 字节，当前 %d）" % (OUT.name, len(text), len(old)))
        return 0

    OUT.parent.mkdir(parents=True, exist_ok=True)
    OUT.write_text(text, encoding="utf-8")
    for slug, c in cats.items():
        print("· %s  %s ／ %d 题 ／ %d 引用 ／ 引擎 %s"
              % (slug, c["latest_date"], c["questions"], c["citations"],
                 ",".join(c["engines"])))
    print("已写入 %s" % OUT)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
