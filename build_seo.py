#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
build_seo.py — 自动重建 SEO 资产。

扫描 briefs/<YYYY-MM-DD>/index.html，提取每篇 brief 的标题与日期，然后重写：
  1. sitemap.xml            —— 静态页 + 动态 brief 页
  2. briefs/index.html      —— Blog 结构化数据里的 blogPost 数组

新增一篇 brief（在 briefs/ 下建一个日期命名的目录 + index.html）后，
跑一次即可：

    python build_seo.py

幂等：内容没变时重复运行不产生 diff。
"""
import re
import sys
import json
import html
from pathlib import Path

SITE = "https://www.sequentry.com"
ROOT = Path(__file__).resolve().parent

# 静态页面（非 brief）：(路径, lastmod, changefreq, priority)
# lastmod 取相对稳定的值，避免每次运行都产生无意义 diff。
STATIC_TAIL = [
    ("/report/",    "2026-05-27", "monthly", "0.8"),
    ("/report/01/", "2026-05-27", "monthly", "0.8"),
    ("/markets/",   "2026-07-09", "weekly",  "0.8"),
    ("/about/",     "2026-06-16", "monthly", "0.5"),
    ("/sources/",   "2026-06-16", "weekly",  "0.5"),
    ("/nav/",       "2026-06-16", "weekly",  "0.6"),
]

DATE_RE = re.compile(r"^\d{4}-\d{2}-\d{2}$")
BRAND_SUFFIX_RE = re.compile(r"\s*[—–\-]\s*序引效能\s*$")


def extract_title(html_text: str) -> str | None:
    """优先用 <title>（去掉品牌后缀），回退 og:title。"""
    m = re.search(r"<title>(.*?)</title>", html_text, re.S)
    if m:
        t = BRAND_SUFFIX_RE.sub("", html.unescape(m.group(1).strip())).strip()
        if t:
            return t
    m = re.search(r'<meta property="og:title" content="([^"]+)"', html_text)
    if m:
        return html.unescape(m.group(1).strip())
    return None


def discover_briefs() -> list[dict]:
    """返回按日期倒序的 brief 列表：[{date, title}, ...]"""
    briefs = []
    bdir = ROOT / "briefs"
    for child in bdir.iterdir():
        if child.is_dir() and DATE_RE.match(child.name):
            idx = child / "index.html"
            if idx.exists():
                title = extract_title(idx.read_text(encoding="utf-8"))
                briefs.append({"date": child.name, "title": title or child.name})
    briefs.sort(key=lambda b: b["date"], reverse=True)
    return briefs


def _url_block(loc: str, lastmod: str, freq: str, prio: str) -> str:
    return (
        "  <url>\n"
        f"    <loc>{SITE}{loc}</loc>\n"
        f"    <lastmod>{lastmod}</lastmod>\n"
        f"    <changefreq>{freq}</changefreq>\n"
        f"    <priority>{prio}</priority>\n"
        "  </url>"
    )


def build_sitemap(briefs: list[dict]) -> str:
    newest = briefs[0]["date"] if briefs else "2026-06-16"
    blocks = [
        _url_block("/", newest, "weekly", "1.0"),
        _url_block("/briefs/", newest, "weekly", "0.9"),
    ]
    for b in briefs:
        blocks.append(_url_block(f"/briefs/{b['date']}/", b["date"], "monthly", "0.7"))
    for loc, lastmod, freq, prio in STATIC_TAIL:
        blocks.append(_url_block(loc, lastmod, freq, prio))
    return (
        '<?xml version="1.0" encoding="UTF-8"?>\n'
        '<urlset xmlns="http://www.sitemaps.org/schemas/sitemap/0.9">\n'
        + "\n".join(blocks)
        + "\n</urlset>\n"
    )


def render_blogposts(briefs: list[dict]) -> str:
    """生成 "blogPost": [...] 片段，缩进对齐 briefs/index.html 的 JSON-LD。"""
    items = []
    for b in briefs:
        headline = json.dumps(b["title"], ensure_ascii=False)
        items.append(
            "    {\n"
            '      "@type": "BlogPosting",\n'
            f"      \"headline\": {headline},\n"
            f"      \"url\": \"{SITE}/briefs/{b['date']}/\",\n"
            f"      \"datePublished\": \"{b['date']}\",\n"
            '      "inLanguage": "zh-CN"\n'
            "    }"
        )
    return '"blogPost": [\n' + ",\n".join(items) + "\n  ]"


def update_briefs_index(briefs: list[dict]) -> bool:
    path = ROOT / "briefs" / "index.html"
    text = path.read_text(encoding="utf-8")
    new_block = render_blogposts(briefs)
    # 替换 Blog JSON-LD 里的 blogPost 数组（数组元素内不含 ']'，非贪婪匹配到首个 ']' 即闭合）
    new_text, n = re.subn(
        r'"blogPost":\s*\[.*?\]',
        lambda _m: new_block,
        text,
        count=1,
        flags=re.S,
    )
    if n == 0:
        print("  ! briefs/index.html 里没找到 Blog 的 blogPost 数组，跳过", file=sys.stderr)
        return False
    if new_text != text:
        path.write_text(new_text, encoding="utf-8", newline="\n")
        return True
    return False


def write_if_changed(path: Path, content: str) -> bool:
    old = path.read_text(encoding="utf-8") if path.exists() else None
    if old != content:
        path.write_text(content, encoding="utf-8", newline="\n")
        return True
    return False


def main() -> None:
    briefs = discover_briefs()
    print(f"发现 {len(briefs)} 篇 brief：")
    for b in briefs:
        print(f"  · {b['date']}  {b['title']}")

    changed_sitemap = write_if_changed(ROOT / "sitemap.xml", build_sitemap(briefs))
    changed_index = update_briefs_index(briefs)

    print()
    print(f"sitemap.xml        {'已更新' if changed_sitemap else '无变化'}")
    print(f"briefs/index.html  {'已更新' if changed_index else '无变化'}")


if __name__ == "__main__":
    main()
