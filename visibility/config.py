# -*- coding: utf-8 -*-
"""
visibility/config.py — 采样对象的唯一真源。

改这里，不要改 engines.py / metrics.py。
每个品类一条 CATEGORY，问题集单独放在 visibility/questions/<slug>.json。
"""
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
RAW = ROOT / "data" / "visibility"          # 原始回答留档（进 .gitignore）
QUESTIONS = Path(__file__).resolve().parent / "questions"

# ---------------------------------------------------------------- 品类

# brands: 展示名 -> 匹配用的别名（小写匹配，含常见错写）
# site:  该品牌自有域名，用于算「官网被引用」
CATEGORIES = {
    "outdoor-power-us": {
        "label": "户外储能 · 美国",
        "market": "US",
        "language": "en",
        "brands": {
            "Jackery":  {"aliases": ["jackery"],                 "site": "jackery.com"},
            "EcoFlow":  {"aliases": ["ecoflow", "eco flow"],     "site": "ecoflow.com"},
            "Bluetti":  {"aliases": ["bluetti", "blueti"],       "site": "bluettipower.com"},
            "Anker SOLIX": {"aliases": ["anker solix", "solix", "anker"], "site": "anker.com"},
            "Goal Zero": {"aliases": ["goal zero", "goalzero"],  "site": "goalzero.com"},
        },
    },
}

# ---------------------------------------------------------------- 引用来源分类

# 引用域名 -> 桶。首屏「AI 引用来源」那块用这个分。
# 命中顺序：精确域名 > 后缀规则 > 品牌官网 > 其他
SOURCE_BUCKETS = {
    "社区论坛": [
        "reddit.com", "quora.com", "stackexchange.com",
        "candlepowerforums.com", "rvforum.net", "ihavenet.com",
    ],
    "测评媒体": [
        "outdoorgearlab.com", "wirecutter.com", "nytimes.com", "cnet.com",
        "tomsguide.com", "techradar.com", "popularmechanics.com", "rtings.com",
        "consumerreports.org", "pcmag.com", "theverge.com", "engadget.com",
        "gearjunkie.com", "switchbacktravel.com", "treehugger.com",
    ],
    "视频": ["youtube.com", "youtu.be", "tiktok.com", "vimeo.com"],
    "电商": ["amazon.com", "walmart.com", "bestbuy.com", "homedepot.com",
             "rei.com", "lowes.com", "target.com", "costco.com"],
}

# ---------------------------------------------------------------- 引擎

# 每个引擎：环境变量名 + 是否默认启用。
# Google AI Overviews 没有官方 API，需要第三方 SERP 供应商，默认关闭。
ENGINES = {
    "perplexity": {"label": "Perplexity", "env": "PERPLEXITY_API_KEY", "default": True},
    "openai":     {"label": "ChatGPT",    "env": "OPENAI_API_KEY",     "default": True},
    "gemini":     {"label": "Gemini",     "env": "GEMINI_API_KEY",     "default": True},
    "google_ai":  {"label": "Google AI 概览", "env": "SERPAPI_API_KEY", "default": False},
}


def load_questions(slug):
    """读问题集。格式：{"questions": ["...", "..."]}"""
    import json
    p = QUESTIONS / (slug + ".json")
    with p.open(encoding="utf-8") as f:
        return json.load(f)["questions"]
