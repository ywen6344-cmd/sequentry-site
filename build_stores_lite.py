# -*- coding: utf-8 -*-
"""从 assets/data/markets/*.json 分片抽每市场头部 6 站（域名+品牌），
生成 assets/data/stores_lite.js 供市场地图页在地球上铺图标簇。
数据刷新（brand-radar build_globe_data.py 重写分片）后需重跑本脚本。
"""
import io, json, os

root = os.path.dirname(os.path.abspath(__file__))
gd = io.open(os.path.join(root, 'assets', 'data', 'globe_data.js'), encoding='utf-8').read()
data = json.loads(gd.split('=', 1)[1].rstrip().rstrip(';'))

out = {}
for name, m in data['markets'].items():
    slug = m.get('slug')
    if not slug:
        continue
    p = os.path.join(root, 'assets', 'data', 'markets', slug + '.json')
    if not os.path.exists(p):
        continue
    rows = json.load(io.open(p, encoding='utf-8')).get('rows', [])[:6]
    out[name] = [[r[0], r[1] or r[0]] for r in rows]

js = 'window.STORES_LITE=' + json.dumps(out, ensure_ascii=False, separators=(',', ':')) + ';'
io.open(os.path.join(root, 'assets', 'data', 'stores_lite.js'), 'w', encoding='utf-8').write(js)
print('markets:', len(out), 'bytes:', len(js.encode('utf-8')))
