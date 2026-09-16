# -*- coding: utf-8 -*-
"""
build_layout.py — 序引站内页共用「头尾」注入器（单一真源）

做什么：
  1. 把 _partials/header.html（深海大导航 + 搜索下拉 + 手机抽屉）注入每个注册页面，整体替换原 <header>...</header>。
  2. 把 _partials/footer.html 注入每个注册页面，整体替换原 <footer>...</footer>。
  3. 在 <head> 末尾引入 2026 共用字体、样式与脚本（assets/sq/），放在页面内联 <style> 之后，保证新样式生效。
  4. 注入分析脚本（Umami + Clarity + 事件层）；清理旧版的 site.css、Pagefind 样式、搜索弹窗和 CF beacon。

注意：
  - 首页 index.html 为 2026 改版独立页面（自带页眉、页脚、样式与分析脚本），不参与注入。
  - 站内搜索在页眉下拉里按需加载 Pagefind（/pagefind/），不再在 <head> 预先引入样式。

特点：纯静态产物、幂等（可反复运行）、零第三方依赖。
用法：  python build_layout.py          # 应用
       python build_layout.py --check  # 只报告会改哪些，不写盘
"""
import re
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent
PARTIALS = ROOT / "_partials"

PAGES = [
    "about/index.html",
    "sources/index.html",
    "report/index.html",
    "report/01/index.html",
    "report/semrush-ai-visibility-2026/index.html",
    "briefs/index.html",
    "briefs/2026-05-27/index.html",
    "briefs/2026-06-01/index.html",
    "briefs/2026-06-03/index.html",
    "briefs/2026-07-08/index.html",
    "cases/index.html",
    "cases/wyze/index.html",
    "cases/comfrt/index.html",
    "cases/shein/index.html",
    "markets/index.html",
    "nav/index.html",
]

HEADER_RE = re.compile(r"<header\b.*?</header>", re.S | re.I)
FOOTER_RE = re.compile(r"<footer\b.*?</footer>", re.S | re.I)
# 清理早期版本遗留的游离标识注释
ORPHAN_MARKER_RE = re.compile(r"<!--[^>]*build_layout\.py[^>]*-->\s*", re.S)
# 旧版：共用 site.css、Pagefind 样式、搜索弹窗（新版搜索在页眉下拉里）
OLD_SITE_CSS_RE = re.compile(r'[ \t]*<link[^>]*href="[^"]*assets/site\.css"[^>]*>[ \t]*\n?')
OLD_PAGEFIND_CSS_RE = re.compile(r'[ \t]*<link[^>]*href="/pagefind/pagefind-ui\.css"[^>]*>[ \t]*\n?')
OLD_SEARCH_MODAL_RE = re.compile(r"[ \t]*<!-- sq-search -->.*?<!-- /sq-search -->[ \t]*\n?", re.S)

# 2026 共用资源块（字体 + 样式 + 脚本），{{REL}} 按页面深度替换，file:// 本地打开也能解析
ASSETS_RE = re.compile(r"[ \t]*<!-- sq-2026 -->.*?<!-- /sq-2026 -->[ \t]*\n?", re.S)
ASSETS_BLOCK = (
    '<!-- sq-2026 -->'
    '<link rel="stylesheet" href="{{REL}}assets/sq/fonts.css">'
    '<link rel="stylesheet" href="{{REL}}assets/sq/site.css">'
    '<script defer src="{{REL}}assets/sq/site.js"></script>'
    '<!-- /sq-2026 -->'
)

# 分析脚本块（Umami + Microsoft Clarity + 事件层）：注入每页 <head>，幂等可刷新。
ANALYTICS_RE = re.compile(r"<!-- sq-analytics -->.*?<!-- /sq-analytics -->", re.S)
ANALYTICS_BLOCK = (
    '<!-- sq-analytics -->'
    '<script defer src="https://cloud.umami.is/script.js" data-website-id="848b3b16-5345-41f3-84cf-612de3e75197"></script>'
    '<script>(function(c,l,a,r,i,t,y){c[a]=c[a]||function(){(c[a].q=c[a].q||[]).push(arguments)};'
    't=l.createElement(r);t.async=1;t.src="https://www.clarity.ms/tag/"+i;'
    'y=l.getElementsByTagName(r)[0];y.parentNode.insertBefore(t,y);})'
    '(window,document,"clarity","script","xa9yl3ejba");</script>'
    '<script defer src="{{REL}}analytics-events.js"></script>'
    '<!-- /sq-analytics -->'
)

# 官网已改用 Umami；移除两站共享 token 的 Cloudflare beacon，让该 token 仅由海图使用。
CF_BEACON_RE = re.compile(
    r"[ \t]*(?:<!--\s*Cloudflare Web Analytics\s*-->\s*)?"
    r"<script[^>]*cloudflareinsights[^>]*>\s*</script>"
    r"\s*(?:<!--\s*End Cloudflare Web Analytics\s*-->)?[ \t]*\n?",
    re.I | re.S,
)


def load_partial(name: str) -> str:
    return (PARTIALS / name).read_text(encoding="utf-8").strip()


def before_head_end(html: str, block: str) -> str:
    return html.replace("</head>", "  " + block + "\n</head>", 1)


def process(path: Path, parts: dict, check: bool):
    with open(path, encoding="utf-8", newline="") as fh:
        raw = fh.read()
    crlf = "\r\n" in raw  # 保留文件原有换行符，避免整页换行差异
    src = raw.replace("\r\n", "\n")
    out = src
    notes = []
    rel_prefix = "../" * path.relative_to(ROOT).as_posix().count("/")

    def sub(regex, repl, note):
        nonlocal out
        new = regex.sub(repl, out)
        if new != out:
            out = new
            notes.append(note)

    sub(ORPHAN_MARKER_RE, "", "清理游离注释")
    sub(OLD_SITE_CSS_RE, "", "移除旧 site.css")
    sub(OLD_PAGEFIND_CSS_RE, "", "移除预加载的 Pagefind 样式")
    sub(OLD_SEARCH_MODAL_RE, "", "移除旧搜索弹窗")
    sub(CF_BEACON_RE, "", "移除 CF beacon")

    if "</head>" not in out:
        notes.append("⚠ 无 </head>")
    else:
        # 分析脚本：存在则刷新，否则注入
        analytics_html = ANALYTICS_BLOCK.replace("{{REL}}", rel_prefix)
        if ANALYTICS_RE.search(out):
            sub(ANALYTICS_RE, lambda _m: analytics_html, "刷新分析脚本")
        else:
            out = before_head_end(out, analytics_html)
            notes.append("注入分析脚本")
        # 2026 共用资源：始终放在 </head> 前（内联样式之后）
        assets_html = ASSETS_BLOCK.replace("{{REL}}", rel_prefix)
        without = ASSETS_RE.sub("", out)
        placed = before_head_end(without, assets_html)
        if placed != out:
            out = placed
            notes.append("共用资源")

    if HEADER_RE.search(out):
        sub(HEADER_RE, lambda _m: parts["header"], "页眉")
    else:
        notes.append("⚠ 未找到 <header>")

    if FOOTER_RE.search(out):
        sub(FOOTER_RE, lambda _m: parts["footer"], "页脚")
    else:
        notes.append("⚠ 未找到 <footer>")

    changed = out != src
    if changed and not check:
        with open(path, "w", encoding="utf-8", newline="") as fh:
            fh.write(out.replace("\n", "\r\n") if crlf else out)
    status = "CHANGED" if changed else "已最新"
    print(f"  [{status}] {path.relative_to(ROOT)}  — {'; '.join(notes) or '无变化'}")
    return changed


def main():
    check = "--check" in sys.argv
    parts = {"header": load_partial("header.html"), "footer": load_partial("footer.html")}
    print(f"== build_layout {'(check)' if check else ''} ==")
    n = 0
    for rel in PAGES:
        p = ROOT / rel
        if not p.exists():
            print(f"  [缺失] {rel}")
            continue
        if process(p, parts, check):
            n += 1
    print(f"== 完成：{n} 个文件{'将' if check else '已'}更新 ==")


if __name__ == "__main__":
    main()
