# AI 搜索可见度采样

把「可见度 Agent」从官网文案变成真的在跑的东西。

```
visibility/
  config.py      品类、品牌别名、来源分桶、引擎开关   ← 只改这里
  engines.py     四个引擎的适配器，统一返回结构
  collect.py     采集层：问题集 × 引擎 → 原始回答留档
  metrics.py     指标层：原始回答 → 提及率 / 位次 / 引用份额 / 来源结构
  questions/     问题集（JSON，零依赖）
../build_visibility_snapshot.py   构建层：指标 → assets/data/visibility_snapshot.js
```

## 跑一次

```bash
# 1. 设 key（至少一个）
setx PERPLEXITY_API_KEY "..."
setx OPENAI_API_KEY "..."
setx GEMINI_API_KEY "..."

# 2. 先用 5 个问题试跑，确认返回结构没变
python -m visibility.collect outdoor-power-us --engines perplexity --limit 5

# 3. 全量采集
python -m visibility.collect outdoor-power-us

# 4. 构建首屏数据
python build_visibility_snapshot.py
```

## 三层分开，是有意的

| 层 | 产物 | 为什么要单独存在 |
|---|---|---|
| 采集 | `data/visibility/<品类>/<日期>.jsonl` | 原始回答必须留档：指标定义以后一定会改，改了要能拿历史重算；「每一条结论都追得到来源」这句话，来源就是它 |
| 指标 | 内存中 | 定义写死在 `metrics.py` 一处，不在别处重算 |
| 构建 | `assets/data/visibility_snapshot.js` | 首屏只吃聚合后的几十行，不吃原始档 |

原始档不进 git（见 `.gitignore`），体积会很快涨起来。

## 指标定义

改定义就是改 `metrics.py`，别在别处再算一遍。

- **提及率** `mention_rate` = 提到该品牌的问题数 ÷ 有效问题数。空回答不计入分母。
- **平均位次** `avg_rank` = 被提及时，该品牌在答案正文里**首次出现**的品牌序位（1 起）。
- **引用份额** `citation_share` = 该品牌自有域名 ÷ 全部引用域名。
- **来源结构** `sources` = 引用域名按社区论坛 / 测评媒体 / 视频 / 电商 / 官网 / 其他分桶。

这四个正好对应首屏面板上已有的四块 KPI，面板不用重做，换数据源即可。

## 四个引擎的现实

| 引擎 | 接法 | 状况 |
|---|---|---|
| Perplexity | 官方 API，直接返回 `search_results` | 引用数据最干净，**优先接** |
| ChatGPT | Responses API + `web_search` 工具 | **必须开联网**，否则拿到的是模型记忆，不是用户真实会看到的答案 |
| Gemini | `google_search` grounding | 引用在 `groundingMetadata.groundingChunks` |
| Google AI 概览 | **没有官方 API** | 只能走 SerpApi / DataForSEO 等第三方，最贵也最脆，`config.ENGINES` 里默认关闭 |

四家的返回结构都在变。`engines.py` 每个适配器都做了防御式取值，拿不到引用就返回空列表——采集不能因为一条问题失败就整批断掉。**每次全量采集前，先用 `--limit 5` 试跑一遍。**

## 频率与成本

一批调用数 = 问题数 × 引擎数。120 题 × 4 引擎 = 480 次/批。

- 周频（公开快照）：480 × 4.3 ≈ **2,100 次/月/品类**
- 日频（付费项目）：480 × 30 = **14,400 次/月/品类**

差 7 倍。所以：

> **公开展示用周频，日频留给付费客户。**

这不只是省钱——它同时给了「为什么要付费」一个具体答案。官网上说「每天 120 个问题 × 4 个引擎」指的是付费项目的规格，公开快照标注自己的采样日期即可，不要混为一谈。

带联网检索的调用单价明显高于纯文本，且各家在调价。**别照搬任何写死的报价，跑全量前先按当期价目自己算一遍上限。**

## 加一个品类

1. 在 `config.CATEGORIES` 加一条，写清品牌别名和自有域名（别名要包含常见错写）。
2. 在 `questions/` 加同名 JSON。问题按 7 类购买意图铺开：品类入门、推荐选型、对比、顾虑异议、场景、价格价值、品牌口碑。每类均衡取样，才代表得了真实需求。
3. **新增问题只往列表末尾加，不要改已有问题的措辞**——改了措辞就断了趋势。
