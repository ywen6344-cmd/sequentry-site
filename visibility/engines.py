# -*- coding: utf-8 -*-
"""
visibility/engines.py — 四个引擎的适配器，统一成同一个返回结构。

统一返回：
    {"engine": "perplexity", "text": "<回答正文>", "citations": ["https://...", ...]}

只用标准库（urllib），和仓库里其他 build 脚本保持零第三方依赖。

⚠️ 这四家的 API 形状都在变。每个适配器都做了防御式取值：
   拿不到 citations 时返回空列表，而不是抛异常——采集不能因为一条问题失败就整批断掉。
"""
import json
import os
import urllib.request
import urllib.error

TIMEOUT = 90


def _post(url, payload, headers):
    req = urllib.request.Request(
        url,
        data=json.dumps(payload).encode("utf-8"),
        headers=dict({"Content-Type": "application/json"}, **headers),
        method="POST",
    )
    with urllib.request.urlopen(req, timeout=TIMEOUT) as r:
        return json.loads(r.read().decode("utf-8"))


def _dig(obj, *path, **kw):
    """安全地从嵌套 dict/list 里取值，任何一环缺失就返回 default。"""
    default = kw.get("default")
    cur = obj
    for k in path:
        try:
            cur = cur[k]
        except (KeyError, IndexError, TypeError):
            return default
    return cur if cur is not None else default


# ---------------------------------------------------------------- Perplexity
# 引用数据最干净的一家，优先接。
def ask_perplexity(question, model="sonar-pro"):
    key = os.environ["PERPLEXITY_API_KEY"]
    data = _post(
        "https://api.perplexity.ai/chat/completions",
        {"model": model, "messages": [{"role": "user", "content": question}]},
        {"Authorization": "Bearer " + key},
    )
    text = _dig(data, "choices", 0, "message", "content", default="")
    # 新版放在 search_results，旧版放在 citations，两个都兜着
    cites = []
    for r in (_dig(data, "search_results", default=[]) or []):
        u = r.get("url") if isinstance(r, dict) else r
        if u:
            cites.append(u)
    if not cites:
        cites = [c for c in (_dig(data, "citations", default=[]) or []) if c]
    return {"engine": "perplexity", "text": text, "citations": cites}


# ---------------------------------------------------------------- OpenAI
# 必须开 web_search，否则拿到的是模型记忆，不是「用户真实会看到的答案」。
def ask_openai(question, model="gpt-4.1"):
    key = os.environ["OPENAI_API_KEY"]
    data = _post(
        "https://api.openai.com/v1/responses",
        {"model": model, "input": question, "tools": [{"type": "web_search"}]},
        {"Authorization": "Bearer " + key},
    )
    text, cites = "", []
    for item in (data.get("output") or []):
        for part in (item.get("content") or []):
            if part.get("type") in ("output_text", "text"):
                text += part.get("text") or ""
            for ann in (part.get("annotations") or []):
                if ann.get("type") == "url_citation" and ann.get("url"):
                    cites.append(ann["url"])
    if not text:
        text = data.get("output_text") or ""
    return {"engine": "openai", "text": text, "citations": cites}


# ---------------------------------------------------------------- Gemini
# 用 google_search grounding，引用在 groundingMetadata 里。
def ask_gemini(question, model="gemini-2.5-flash"):
    key = os.environ["GEMINI_API_KEY"]
    url = ("https://generativelanguage.googleapis.com/v1beta/models/"
           + model + ":generateContent?key=" + key)
    data = _post(
        url,
        {"contents": [{"parts": [{"text": question}]}],
         "tools": [{"google_search": {}}]},
        {},
    )
    parts = _dig(data, "candidates", 0, "content", "parts", default=[]) or []
    text = "".join(p.get("text", "") for p in parts)
    cites = []
    for ch in (_dig(data, "candidates", 0, "groundingMetadata",
                    "groundingChunks", default=[]) or []):
        u = _dig(ch, "web", "uri")
        if u:
            cites.append(u)
    return {"engine": "gemini", "text": text, "citations": cites}


# ---------------------------------------------------------------- Google AI 概览
# 没有官方 API。这里走 SerpApi；换 DataForSEO 只要改这一个函数。
# 这是四个引擎里最贵、最脆的一环，默认关闭（见 config.ENGINES）。
def ask_google_ai(question):
    key = os.environ["SERPAPI_API_KEY"]
    q = urllib.parse.urlencode({"q": question, "api_key": key, "engine": "google",
                                "hl": "en", "gl": "us"})
    req = urllib.request.Request("https://serpapi.com/search.json?" + q)
    with urllib.request.urlopen(req, timeout=TIMEOUT) as r:
        data = json.loads(r.read().decode("utf-8"))

    ov = data.get("ai_overview") or {}
    blocks = ov.get("text_blocks") or []
    text = " ".join(b.get("snippet", "") for b in blocks)
    cites = [ref.get("link") for ref in (ov.get("references") or []) if ref.get("link")]
    return {"engine": "google_ai", "text": text, "citations": cites}


import urllib.parse  # noqa: E402  (ask_google_ai 用到)

ASK = {
    "perplexity": ask_perplexity,
    "openai": ask_openai,
    "gemini": ask_gemini,
    "google_ai": ask_google_ai,
}
