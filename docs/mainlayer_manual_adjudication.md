# 主体层更新说明

- 更新时间：2026-05-23
- 当前主体层主线口径：
  `point_slot_onset_distribution.csv -> 取最高频音值 -> type_phonetic_chains.csv -> mainlayer_merge.csv`
- 当前自动更新脚本：
  - `scripts/clean_wenzhou.py`
  - `scripts/analyze_rhyme_phonetics.py`
  - `scripts/update_mainlayer_tables.py`

## 当前状态

- `clean_wenzhou.py` 已补入项目中常见的 IPA 元音字符，`ɷ / ɑ / ᴀ / ᴇ / ʮ / ɥ` 不再漏抽。
- `type_phonetic_chains.csv` 与 `phonetic_evolution_chains.csv` 当前由同一脚本同步更新。
- `mainlayer_merge.csv` 已按当前 82 个方言点重建。

## 主体层合并描述性统计

统计口径：当前 `data_raw/mainlayer_merge.csv` 全表，共 `410` 行，即 `82` 个方言点 × `5` 个核心声组。

### 一级分类

- `合流型`：314 / 410，`76.6%`
- `分立型`：96 / 410，`23.4%`

### 二级分类

- `单一合并`：249 / 410，`60.7%`
- `全不等`：96 / 410，`23.4%`
- `多元合并`：65 / 410，`15.9%`

### 三级详细模式

- `S2=S3`：197 / 410，`48.0%`
- `全对立`：96 / 410，`23.4%`
- `S1=S2`：44 / 410，`10.7%`
- `S0=S1，S2=S3`：38 / 410，`9.3%`
- `S1=S2=S3`：27 / 410，`6.6%`
- `S0=S1`：5 / 410，`1.2%`
- `S1=S3 [越级]`：3 / 410，`0.7%`

### 图示说明

- 旭日图中，`分立型 / 全不等 / 全对立` 现在不再拆成三层，而是统一显示为一个 `全对立` 分支。
- 其他类型保留合并模式细分，便于直接读出 `S2=S3 / S1=S2 / S0=S1，S2=S3 / S1=S3 [越级]` 等结构。

## 关于人工裁定表

- `data_clean/value_type/mainlayer_manual_adjudication_candidates.csv`
  这张表是旧一轮排查时生成的辅助文件。
- 由于当时元音抽取规则还没补全，其中一部分 `missing` 属于伪缺失。
- 因此它现在只能作为排查参考，不能再直接当成最新裁定清单。

## `是否越级 = True` 的 3 例

当前 `mainlayer_merge.csv` 中共有 3 个 `True`：

1. `CS02` 常熟虞山镇 `Ø`
   - 链值：`S0=ᴀ, S1=u, S2=ɯ, S3=u`
   - 详细模式：`S1=S3 [越级]`
   - 说明：这是比较典型的“中间链位与两端不相同”的越级格位，S1 与 S3 同值，而 S2 保持独立。

2. `WX01` 无锡城区 `Ø`
   - 链值：`S0=a, S1=u, S2=əɯ, S3=u`
   - 详细模式：`S1=S3 [越级]`
   - 说明：它和常熟这例相近，也属于 `Ø` 组内部的越级同值，S2 没有并入 S1/S3。

3. `SJ02` 泗泾 `M`
   - 链值：`S0=ɑ, S1=o, S2=u, S3=o`
   - 详细模式：`S1=S3 [越级]`
   - 说明：这例和上面两例不太一样。它不是 `Ø` 组，而是 `M` 组；并且链条表现为 `o -> u -> o` 的回摆式结构，属于“中段抬高、末段回返”的类型，不只是单纯的越级同值。

## 对 `SJ02` 的当前理解

- `泗泾 M` 这例应继续保留 `True` 标记。
- 但在解释时，最好不要把它和 `常熟 Ø / 无锡 Ø` 简单并列成同一种越级机制。
- 更稳妥的写法是：
  - `常熟 Ø / 无锡 Ø`：典型 `S1=S3` 越级同值例
  - `泗泾 M`：带“回摆/回返”性质的 `S1=S3` 特例

## 如果后面继续更新主体层

建议总是按这个顺序：

```bash
env/bin/python scripts/clean_wenzhou.py
env/bin/python scripts/analyze_rhyme_phonetics.py
env/bin/python scripts/update_mainlayer_tables.py
```
