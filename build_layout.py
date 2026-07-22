# -*- coding: utf-8 -*-
"""
build_layout.py — 序引站全站共用「头尾」注入器（单一真源）

做什么：
  1. 把 _partials/footer.html 注入每个注册页面（整体替换原 <footer>...</footer>）。
  2. 把 _partials/header.html 注入「内容页」（整体替换原 <header>...</header>）。
  3. 确保每页 <head> 内引入 /assets/site.css。

注意：
  - 首页 index.html 用专属深色地球页眉，不纳入页眉替换（仅替换页脚）。
  - nav/index.html 是特殊侧栏页，暂只替换页脚。

特点：纯静态产物、幂等（可反复运行）、零第三方依赖。
用法：  python build_layout.py          # 应用
       python build_layout.py --check  # 只报告会改哪些，不写盘
"""
import re
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent
PARTIALS = ROOT / "_partials"
CSS_LINK_RE = re.compile(r'<link[^>]*href="[^"]*assets/site\.css"[^>]*>')

# 每页应用哪些共用块。footer=全站；header=True 冷白内容页眉，"dark"=深色地球页眉。
PAGES = {
    "index.html":                  {"footer": True, "header": "dark"},
    "about/index.html":            {"footer": True, "header": True},
    "sources/index.html":          {"footer": True, "header": True},
    "report/index.html":           {"footer": True, "header": True},
    "report/01/index.html":        {"footer": True, "header": True},
    "briefs/index.html":           {"footer": True, "header": True},
    "briefs/2026-05-27/index.html":{"footer": True, "header": True},
    "briefs/2026-06-01/index.html":{"footer": True, "header": True},
    "briefs/2026-06-03/index.html":{"footer": True, "header": True},
    "briefs/2026-07-08/index.html":{"footer": True, "header": True},
    "cases/index.html":            {"footer": True, "header": True},
    "cases/wyze/index.html":       {"footer": True, "header": True},
    "cases/comfrt/index.html":     {"footer": True, "header": True},
    "markets/index.html":          {"footer": True, "header": "dark"},# 市场地图：深色地球页眉
    "nav/index.html":              {"footer": True},                  # 特殊侧栏页，暂只替换页脚
}

HEADER_RE = re.compile(r"<header\b.*?</header>", re.S | re.I)
FOOTER_RE = re.compile(r"<footer\b.*?</footer>", re.S | re.I)
# 清理早期版本遗留的游离标识注释（曾被注入在 <footer>/<header> 标签外，导致重复累积）
ORPHAN_MARKER_RE = re.compile(r"<!--[^>]*build_layout\.py[^>]*-->\s*", re.S)

# 分析脚本块（Umami + Microsoft Clarity + 事件层）：注入每页 <head>，幂等可刷新。
# {{REL}} 按页面深度替换为相对前缀，使 analytics-events.js 在任意目录层级都能解析。
# 改 website-id / clarity-id 后重跑本脚本即可全站刷新。
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

# 官网已改用 Umami；移除两站共享 token 的 Cloudflare beacon，让该 token 仅由海图使用，
# 终结官网/海图 PV 混报。匹配 CF beacon <script> 及其可选包裹注释。
CF_BEACON_RE = re.compile(
    r"[ \t]*(?:<!--\s*Cloudflare Web Analytics\s*-->\s*)?"
    r"<script[^>]*cloudflareinsights[^>]*>\s*</script>"
    r"\s*(?:<!--\s*End Cloudflare Web Analytics\s*-->)?[ \t]*\n?",
    re.I | re.S,
)


def load_partial(name: str) -> str:
    return (PARTIALS / name).read_text(encoding="utf-8").strip()


def process(path: Path, spec: dict, parts: dict, check: bool):
    src = path.read_text(encoding="utf-8")
    out = src
    notes = []

    # 0) 清理早期遗留的游离标识注释（幂等修复）
    if ORPHAN_MARKER_RE.search(out):
        out = ORPHAN_MARKER_RE.sub("", out)
        notes.append("清理游离注释")

    # 按页面深度算相对前缀：让 /assets、二维码等在 file:// 本地双击打开也能解析
    #（相对路径在部署到根域时同样正确，故两种打开方式都对）
    rel_prefix = "../" * path.relative_to(ROOT).as_posix().count("/")
    header_key = "header_dark" if spec.get("header") == "dark" else "header"
    header_html = parts[header_key].replace("{{REL}}", rel_prefix)
    footer_html = parts["footer"].replace("{{REL}}", rel_prefix)
    desired_link = f'<link rel="stylesheet" href="{rel_prefix}assets/site.css">'

    # 1) 确保引入共享 CSS（相对路径；已存在则规范化为正确深度）
    if "assets/site.css" in out:
        new_out = CSS_LINK_RE.sub(desired_link, out, count=1)
        if new_out != out:
            out = new_out
            notes.append("规范 site.css 路径")
    elif "</head>" in out:
        out = out.replace("</head>", "  " + desired_link + "\n</head>", 1)
        notes.append("注入 site.css")
    else:
        notes.append("⚠ 无 </head>")

    # 1.4) 移除官网 CF beacon（官网改用 Umami；CF token 让海图独占，终结混报）
    if CF_BEACON_RE.search(out):
        out = CF_BEACON_RE.sub("", out)
        notes.append("移除 CF beacon")

    # 1.5) 分析脚本（Umami + Clarity + 事件层）：注入/刷新到 <head>（幂等）
    analytics_html = ANALYTICS_BLOCK.replace("{{REL}}", rel_prefix)
    if ANALYTICS_RE.search(out):
        new_out = ANALYTICS_RE.sub(lambda _m: analytics_html, out, count=1)
        if new_out != out:
            out = new_out
            notes.append("刷新分析脚本")
    elif "</head>" in out:
        out = out.replace("</head>", "  " + analytics_html + "\n</head>", 1)
        notes.append("注入分析脚本")

    # 2) 页眉（仅内容页）
    if spec.get("header"):
        if HEADER_RE.search(out):
            out = HEADER_RE.sub(lambda _m: header_html, out, count=1)
            notes.append("替换 <header>")
        else:
            notes.append("⚠ 未找到 <header>")

    # 3) 页脚（全站）
    if spec.get("footer"):
        if FOOTER_RE.search(out):
            out = FOOTER_RE.sub(lambda _m: footer_html, out, count=1)
            notes.append("替换 <footer>")
        else:
            notes.append("⚠ 未找到 <footer>")

    changed = out != src
    if changed and not check:
        path.write_text(out, encoding="utf-8")
    status = "CHANGED" if changed else "已最新"
    print(f"  [{status}] {path.relative_to(ROOT)}  — {'; '.join(notes)}")
    return changed


def main():
    check = "--check" in sys.argv
    parts = {
        "header": load_partial("header.html"),
        "header_dark": load_partial("header_dark.html"),
        "footer": load_partial("footer.html"),
    }
    print(f"== build_layout {'(check)' if check else ''} ==")
    n = 0
    for rel, spec in PAGES.items():
        p = ROOT / rel
        if not p.exists():
            print(f"  [缺失] {rel}")
            continue
        if process(p, spec, parts, check):
            n += 1
    print(f"== 完成：{n} 个文件{'将' if check else '已'}更新 ==")


if __name__ == "__main__":
    main()
