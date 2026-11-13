# v1.0.0 发布说明（2026-11-13）

> 版本号：`VERSION` = **1.0.0**　｜　代码仓库：本地 git（无远端）
> 验收结论：**通过** —— 见 `_review_items/验收_检索接入_20261112.md` 与 `_review_items/接入报告_章节索引_20261112.md`

---

## 1. 这一版交付了什么

校园办事向导从「整份文件 = 一条事项」升级为 **文件 → 章节 → 条目** 三层：

| 层 | 内容 | 规模 |
|---|---|---|
| 条目层 | 一件办事一条，逐字段挂逐字引文 | **39,274 条** / 42,414 个字段带 evidence，校验失败 0 |
| 章节层 | 每份文件的章节 + 条目落节 | **531 份 / 11,886 节 / 22,117 条落节** |
| 检索层 | ② 章节点加分（默认开）+ ③ 节向量（默认关） | 向量库 **2,153 份 / 24,971 段**（含节 11,531 段） |

## 2. 验收结论与指标

| 评测 | 本版实测 | 判据 |
|---|---|---|
| `eval.py` 33 条规则识别 | 29/33 = **87.9%** | 不回归（基线同值） |
| 同族对照 29 条 | 28/29 = **96.6%** | 不回归 |
| 50 条规则腿 diff（② 关 vs 改动前） | **50/50 一致** | 零回归 |
| 章级 20 条 · ② 开 vs 关 | top1 0.00 → **0.15**、top3 0.10 → **0.15** | 有增益 |
| 章级 20 条 · ③ 节向量 | top1 **0.60** / top3 **0.80** | 达任务书门槛（≥12 条） |
| API 冒烟 | `/api/health`、`/api/stats`、`/api/search` 全部 200 | 可服务 |

**默认开关**：`SECTIONS_BOOST=1`（② 开）、`SECTIONS_VEC=0`（③ 关）。
**演示口径**：评审现场用 `SECTIONS_VEC=1` 跑一次章级问答——0.60 / 0.80 是全系统最强的一组数。

## 3. 部署

### 3.1 代码（本仓库）

```bash
git clone <repo> && cd 智能体节
python -m venv .venv
.venv/Scripts/pip install -r requirements.txt     # fastapi uvicorn numpy pypdf python-docx …
```

### 3.2 数据（不进 git，按目录放置）

`.gitignore` 已排除 `/sources/`、`/items*.json`、`/_review_items/`，**仓库里只有代码**。

| 需要放置的 | 位置 | 说明 |
|---|---|---|
| 事项库 | `items.json` | ~57 MB；没有它系统起不来 |
| 语料与抽取文本 | `sources/` | ~710 MB（PDF + `.txt`） |
| 向量库 | `sources/vector/` | ~356 MB（`vectors.npy` 195 MB + `chunks.jsonl` 34 MB） |
| 章节索引 | `_review_items/sections/` | 531 份 JSON |

**从零重建**：

```bash
.venv/Scripts/python.exe tools/build_vector.py      # 全量重建向量库（约数分钟）
.venv/Scripts/python.exe tools/check_quotes.py      # 必须「失败 0 个」
.venv/Scripts/python.exe tools/check_counts.py      # 口径核对（有 1 条历史红项，见 §5）
```

**只要增量**（补了新文件）：

```bash
.venv/Scripts/python.exe tools/vector_add.py <slug> ...   # 增量入向量库（几秒/份）
```

### 3.3 启动

```bash
.venv/Scripts/python.exe -m uvicorn app:app --host 127.0.0.1 --port 8000
```

`.env` 需要 `DEEPSEEK_API_KEY`（模型与视觉都走它）；`.env` 不进仓库，模板见 `.env.example`。

## 4. 回滚

| 层 | 回滚方式 |
|---|---|
| 代码 | `git checkout 88141b9`（上一版） |
| 检索开关 | 不想要 ②：设 `SECTIONS_BOOST=0` 重启；③ 本来就是关的 |
| 向量库 | `sources/vector/` 旁有 `vectors.npy.bak`、`chunks.jsonl.bak`，换回即可 |
| 事项库 | 本版改动前的备份：`items.json.bak-wd-evidence`、`.bak-wd-ev2`、`.bak-filecov`、`.bak-cz-evidence` |

## 5. 已知限制（发布时必须一起说）

1. **③ 默认关**：节向量只在演示与 `/api/search` 使用；生产答案链路没启用，等于「修好了但没上线」。
2. **章节索引只覆盖 25%**（531 / 2,153 份文档），剩余文档的条目拿不到节加分。
3. **② 触发面窄、加分面宽**：70 条真实问句只有 17% 触发；触发时平均 220 条（最多 449 条）被加分，实质是给整篇文档抬分——这是章级 top1 只有 0.15 的主因，下一步应收紧到「命中的那一节 + 相邻节」。
4. **答案层不用节信息**：引用只到文档，不显示「第X章 节名 / 第X条」；`lines` 字段目前只给 4 条 `doc_only` 条目反查。
5. **33 份 `truncated` 文档**：正文只到截断处（如 82 页的修缮工程办法只到第六条），节区间与答案都不能当全文。
6. **`check_counts.py` 有 1 条历史红项**：30,648 条碎片条目的 `source` 是对象不是数组，早于本版存在，未批量改写。
7. **预置问法未覆盖新条目**：`presets.json` 仍是 11-05 版；`gen_presets.py` 全量约 10 分钟以上，未纳入本版。

## 6. 发布清单

| 文件 | 说明 |
|---|---|
| `VERSION` / `CHANGELOG.md` / `RELEASE_v1.0.md` | 版本、变更、发布说明 |
| `app.py` | ② 接入 `rank()`；`vector_item_hits()` 接入 ③ |
| `sections_index.py` | 章节索引加载 + 加分（默认开） |
| `vector_index.py` | `search(kind=)`、`exclude=`、`stats()` 增节数 |
| `tools/build_vector.py` / `vector_add.py` | 节 chunk 构建；增量入库 |
| `tools/eval_sections.py` | 章级 20 条评测（索引计数已修） |
| `_review_items/sections/*.json` | 531 份章节索引（数据，不入 git） |
