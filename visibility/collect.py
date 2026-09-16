# -*- coding: utf-8 -*-
"""
visibility/collect.py — 采集层：问题集 × 引擎 → 原始回答留档。

  python -m visibility.collect outdoor-power-us
  python -m visibility.collect outdoor-power-us --engines perplexity,openai --limit 10

产物：data/visibility/<slug>/<YYYY-MM-DD>.jsonl，一行一条原始回答。

为什么要留原始档而不是只存指标：
  1. 指标定义以后一定会改，改了要能重算历史；
  2. 「每一条结论都追得到来源」是对外承诺，原始回答就是那个来源；
  3. 趋势图需要历史，指标文件只有当期。
留档不进 git（见 .gitignore），首屏只吃 build 出来的聚合结果。
"""
import argparse
import json
import os
import sys
import time
import datetime

from . import config, engines


def available_engines(requested=None):
    out = []
    for key, meta in config.ENGINES.items():
        if requested is not None and key not in requested:
            continue
        if requested is None and not meta["default"]:
            continue
        if not os.environ.get(meta["env"]):
            print("  跳过 %-11s 缺环境变量 %s" % (key, meta["env"]), file=sys.stderr)
            continue
        out.append(key)
    return out


def run(slug, requested=None, limit=None, sleep=1.0, date=None):
    if slug not in config.CATEGORIES:
        raise SystemExit("未知品类：%s（可选：%s）" % (slug, ", ".join(config.CATEGORIES)))

    questions = config.load_questions(slug)
    if limit:
        questions = questions[:limit]
    engs = available_engines(requested)
    if not engs:
        raise SystemExit("没有可用引擎：请先设置 API key 环境变量。")

    day = date or datetime.date.today().isoformat()
    out_dir = config.RAW / slug
    out_dir.mkdir(parents=True, exist_ok=True)
    out_path = out_dir / (day + ".jsonl")

    print("品类 %s ／ 问题 %d ／ 引擎 %s ／ 共 %d 次调用"
          % (slug, len(questions), ",".join(engs), len(questions) * len(engs)))

    ok = err = 0
    with out_path.open("a", encoding="utf-8") as f:
        for i, q in enumerate(questions, 1):
            for eng in engs:
                try:
                    rec = engines.ASK[eng](q)
                    rec.update({"question": q, "date": day,
                                "ts": datetime.datetime.now().isoformat(timespec="seconds")})
                    f.write(json.dumps(rec, ensure_ascii=False) + "\n")
                    f.flush()
                    ok += 1
                except Exception as e:                      # 单条失败不能断整批
                    err += 1
                    print("  ! %s / Q%d: %s" % (eng, i, e), file=sys.stderr)
                time.sleep(sleep)
            if i % 10 == 0:
                print("  ... %d/%d" % (i, len(questions)))

    print("完成：成功 %d，失败 %d → %s" % (ok, err, out_path))
    return out_path


def load(slug, day):
    """读回某一天的原始档。"""
    p = config.RAW / slug / (day + ".jsonl")
    if not p.exists():
        return []
    recs = []
    with p.open(encoding="utf-8") as f:
        for line in f:
            line = line.strip()
            if line:
                recs.append(json.loads(line))
    return recs


def latest_day(slug):
    d = config.RAW / slug
    days = sorted(p.stem for p in d.glob("*.jsonl")) if d.exists() else []
    return days[-1] if days else None


if __name__ == "__main__":
    ap = argparse.ArgumentParser()
    ap.add_argument("slug")
    ap.add_argument("--engines", help="逗号分隔，默认用 config 里 default=True 的")
    ap.add_argument("--limit", type=int, help="只跑前 N 个问题（试跑用）")
    ap.add_argument("--sleep", type=float, default=1.0)
    a = ap.parse_args()
    run(a.slug,
        requested=set(a.engines.split(",")) if a.engines else None,
        limit=a.limit, sleep=a.sleep)
