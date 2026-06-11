---
name: technical-analysis
description: 个股技术面分析模块——对单只美股给出「格局/动量/信号/趋势/期权结构/资金」六维结构化判读,并加入 WSB/X 社媒热度、喊单方向、拥挤度与 HYPE 阶段;数据优先取长桥 Longbridge MCP 只读行情(K线/盘口/期权链),并输出深色科技风 PDF 报告和 PNG 图表。报告末尾必须附术语解释(GEX/Gamma/OI/IV/WSB/HYPE 等)。当用户说"看看 XXXX 的技术面/技术分析""现在是多头还是空头格局""画个 GEX/期权结构图""这只票的压力位支撑位在哪""动量/趋势强不强"时使用。⚠️ 只做分析,绝不下单/交易。始终简体中文。
---

# technical-analysis 个股技术面分析模块

对**单只票**做六维技术面体检,**结论先行、每条结论配可度量证据 + 图**。这是技术面(价、量、期权持仓结构)分析,与 `tech-research`(基本面卡点 thesis)互补——前者看"现在盘面在说什么",后者看"这门生意值不值得"。需要时两者交叉印证。

**绝不自主下单/交易/移动资金。** 数字标 as-of + 来源;区分 已证实 / 推断 / 推测。

## 一、取数(按可用性降级)

1. **长桥 Longbridge MCP(优先,只读)**——同 `portfolio-advisor` 的连接方式(自定义远程 MCP,OAuth)。连上后**先探测实际工具名与返回字段**再解析。本模块用到的只读行情工具:
   - 价/量:`candlesticks`(日/周/分钟 K,算均线/动量/ATR)· `quote`(现价/涨跌/量)· `depth`(盘口买卖档,看即时压力支撑)· `top_movers`(相对强弱参照)
   - 期权:`option_chain_info_by_date`(到期日列表)· `option_chain_info`/`option_chain`(某到期日各行权价的 strike、call/put、**gamma、未平仓 OI、IV**)· `option_quote`(单合约报价/希腊字母)
   - 辅助:`capital_flow` / `capital_distribution`(资金流入流出、大中小单分布,若可用)· `valuation`(估值参照)
   - **🚫 硬黑名单(永不调用)**:`submit_order`·`replace_order`·`cancel_order`·`dca_*`·`alert_*`·任何写/下单工具。需要操作时只给"去 App 手动"提示。
2. **降级**:长桥不可用 → 用 `WebSearch`/`web_fetch` 取公开行情与期权链(标来源);或请用户粘贴 K 线/期权链 CSV。GEX 缺一手期权链时如实说"数据不全,以下为近似"。

> 长桥 MCP 不在 Claude 连接器目录,需用户在 设置 → 连接器 添加自定义远程 MCP(`https://openapi.longbridge.com/mcp`,国内加速 `https://openapi.longbridge.cn/mcp`)并完成 OAuth;说明见 https://open.longbridge.com/zh-CN/skill/ 。

## 二、六维判读(逐项给"结论 + 证据 + 怎么算出来的")

### ① 格局(Regime)——多头 / 空头 / 震荡 / 转折
判据(综合,不靠单一指标):价相对 MA20/50/200 的位置与排列(多头排列=价>MA20>MA50>MA200 且均线上倾;空头排列反之);200 日均线斜率;近 60 日高低点结构(higher-high/higher-low=多头结构,lower-high/lower-low=空头)。
输出:`多头格局 / 空头格局 / 高位震荡 / 低位震荡 / 多转空(顶部背离)/ 空转多(底部企稳)` 之一 + 一句因由 + 关键均线数值(as-of)。

### ② 动量(Momentum)——方向 + 强弱档
用 RSI(14)、MACD(柱状/快慢线)、ROC(变动率)、量能配合。判档:`向上增强 / 向上钝化 / 走平 / 向下增强 / 向下钝化 / 顶背离 / 底背离`。说清"价创新高但 RSI/MACD 未创新高=动量背离"这类关键信号。给具体数值。

### ③ 信号(Signal)——市场是否给出看多信号
扫一组经典信号并明确"触发/未触发":均线金叉/死叉、MACD 金叉、突破/跌破关键位带量、缩量回踩不破、RSI 超买超卖回归、布林带挤压后扩张方向、跳空缺口。汇总成 **看多分数(0~5)/ 看空分数(0~5)** 并给净信号方向。不要只罗列,要给"当前最该关注的 1-2 个信号"。

### ④ 趋势(Trend)——强弱量化 + 出图
用 ADX(趋势强度,>25 有趋势、>40 强趋势)、DI+/DI-(方向)、线性回归斜率/R²(趋势纯度)、价格通道。判档:`强趋势向上 / 偏强 / 偏弱 / 强趋势向下 / 无趋势(震荡)`。
**必出图**:调用脚本画**趋势证据图**(价 + MA20/50/200 + 通道 + ADX 副图),把上面结论的证据可视化。

### ⑤ 期权结构(Options Structure)——是否优秀 + 出 GEX 图
从长桥期权链自算 **Gamma Exposure(GEX)**:
- 单行权价 GEX ≈ `gamma × OI × 100 × spot² × 0.01 × 符号`(做市商视角:**Call OI 记 +、Put OI 记 −**;即 dealer 对 call 多头为正 gamma、对 put 为负 gamma 的常用约定)。逐 strike 汇总。
- **Call Wall** = 正 GEX 最大的行权价(上方磁吸/压制位);**Put Wall** = 负 GEX 最大(绝对值)的行权价(下方支撑/加速位)。
- **Gamma Flip(零 GEX 翻转位)** = 累计 GEX 由负转正的价位:现价在其上方→做市商正 gamma→压波动(盘面黏);下方→负 gamma→助涨助跌(放波动)。
- **GEX PCR** = Put 侧 GEX 绝对值之和 / Call 侧 GEX 之和(衡量对冲压力的多空偏向)。
判"是否优秀":结构清晰(墙明确)、现价相对 Gamma Flip 的位置、PCR 是否极端、近月 OI 是否集中。
**必出图**:**Gamma Exposure 柱形图**(x=行权价,y=各 strike 净 GEX,正绿负红),标注 Call Wall、Put Wall、Gamma Flip、现价竖线,并在图注写 GEX PCR。

### ⑥ 资金(Capital / Flow)——流入流出 + 筹码标尺 + 压力支撑
- **资金方向**:用 `capital_flow`/`capital_distribution`(或成交量价、OBV、主力大单净额)判 `净流入 / 净流出 / 分歧`,给近 1/5/20 日净额。
- **主力筹码标尺**:用成交量分布(Volume Profile / 按价格区间累计成交量)近似筹码峰,标 **最大堆积区(成本密集区)** 与 套牢盘/获利盘分界。
- **压力位 / 支撑位**:综合 ④的均线/通道、⑤的 Call/Put Wall、⑥的筹码峰、近端摆动高低点 + 盘口大单,给 **2-3 档压力、2-3 档支撑**(价位 + 依据)。
**必出图**:**资金流向 + 筹码标尺图**(成交量分布横条 + 价格、标压力支撑带)。

### ⑦ 社媒热度(Social Hype)——WSB/X 热度 + HYPE 阶段
个股报告必须加入一段 `社媒热度与 HYPE 阶段`。按 `wsb-sentiment` 技能做窄版单票分析:
- **WSB 主源**:抓 `r/wallstreetbets` hot/rising/new/top(day) 和 ticker 搜索。若该 ticker 不在 WSB hot 前排,必须写明“未进入 WSB 当前 hot 前 N 样本”,不能夸大热度。
- **X / Twitter 交叉验证**:搜 `$TICKER OR TICKER` 最近 20 条或更多,摘要互动量、核心账号、主要叙事。若 X 搜索不可用,明确写“X 数据不可得”。
- **必给字段**:热度强度(低/中/高/极端)、喊单方向(看多/看空/双向分歧/纯 Meme/不明)、常见玩法(Call/Put/0DTE/周权/YOLO/正股/短挤压/财报赌局)、拥挤度(低/中/高/极端)、HYPE 阶段(早期/中期/末期/退潮)、监控评分(0-10)。
- **HYPE 判定**:早期=少量 DD 与分歧;中期=叙事成形且讨论扩散;末期=情绪高度一致、YOLO/0DTE/FOMO 密集;退潮=亏损截图、自嘲、bag-holder 与互动降温。
- **诚实层**:社媒只代表样本热度和传播阶段,不是基本面事实,也不是买卖信号。引用社区内容只做短句转述,标注 as-of 与抓取窗口。

## 三、出图与 PDF 导出(Python / matplotlib)

图表脚本在同目录 `scripts/charts.py`。流程:**长桥取数 → 整理成脚本要的 JSON/CSV → 调脚本生成 PNG → 用 present_files 给用户(或嵌进研报)**。图表默认使用深色模式,普通文本优先 Google Noto Sans SC (`NotoSansSC-VF.ttf`) 的 regular-text/body 字体族并实例化到 900 字重,标题优先 Noto Serif SC 形成层级,再降级到 Microsoft YaHei / SimHei。图内所有文字必须纯白、加粗、字号不小于 9pt,标题不小于 15pt。

```bash
# 趋势证据图:需要 OHLC + 日期序列
python scripts/charts.py trend   --input <ohlc.json>   --out <symbol>_trend.png   --symbol NVDA
# Gamma Exposure 柱形图:需要逐 strike 的 {strike, call_oi, put_oi, gamma, spot}
python scripts/charts.py gex     --input <chain.json>  --out <symbol>_gex.png     --symbol NVDA
# 资金流向 + 筹码标尺:需要 {price_bins, volume_at_price, supports[], resistances[]}
python scripts/charts.py flow    --input <flow.json>   --out <symbol>_flow.png    --symbol NVDA
```

脚本无第三方依赖即可跑(只需 `matplotlib`、`numpy`;缺则 `pip install matplotlib numpy --break-system-packages`)。各子命令的输入 JSON 字段见脚本顶部 docstring。GEX 计算逻辑内置在脚本里,与上面 ⑤ 一致——传原始期权链即可。输出 PNG 应与 PDF 保持同一套 dark-mode / neon-green 科技风,不要再生成白底图表,不要使用灰色小字。

PDF 导出脚本在同目录 `scripts/export_report.py`。它读取 Markdown 报告,解析本地图片链接,按页面宽度嵌入 PNG,并可在报告末尾自动补标准术语解释。默认模板为 `aurora-dark`:深色背景、青绿色高亮、数据 HUD 分区、科技感页眉页脚;正文优先 Google Noto Sans SC 的 regular-text/body 字体族并实例化到 900 字重,标题优先 Noto Serif SC/display 字体。PDF 内所有文字必须纯白、加粗,正文不小于 10pt,二级标题不小于 15pt;标题和正文用字号与字体族区分,不是只换颜色。风格参考 Aura AI Sales Engine 的 dark-mode SaaS / telemetry aesthetic,但不复制其资产。

```bash
python scripts/export_report.py --input output/stock-analysis/NVDA/YYYY-MM-DD_NVDA_technical-analysis.md --out output/stock-analysis/NVDA/YYYY-MM-DD_NVDA_technical-analysis.pdf --append-glossary --update-md --engine auto
```

`--engine auto` 优先使用 ReportLab 做真实 PDF 段落排版(修复中文/英文长句右侧截断),不可用时自动降级到 matplotlib 深色模板。导出后至少验证 PDF 文件存在、大小大于 0、脚本输出的 `images` 数量覆盖报告引用的关键图(趋势/GEX/资金)。如 PDF 依赖或字体不可用,必须说明缺口,不能假装已导出。

## 四、输出契约(必守)

报告正文、PDF、趋势图、GEX 图、资金/筹码图和原始输入 JSON/CSV 必须放在同一个标的目录:

```text
output/stock-analysis/<SYMBOL>/YYYY-MM-DD_<SYMBOL>_technical-analysis.md
output/stock-analysis/<SYMBOL>/YYYY-MM-DD_<SYMBOL>_technical-analysis.pdf
```

**结论先行**,六维各一段:`【维度】判档(关键数值,as-of) — 一句因由`,需要图的维度(④⑤⑥)附对应 PNG,并在 PDF 中清晰嵌入同一批图片。结尾给:

章节标题必须自然、专业,不要写 `0. 结论`、`1. 事实底座`、`2. 卡点框架` 这类机械编号。推荐使用 `核心判断`、`事实底座`、`光互连卡点框架`、`技术面结构`、`社媒热度与 HYPE 阶段`、`情景预案`、`证伪条件`、`技术面快照`、`主要来源`、`术语解释`。PDF 导出器会自动隐藏残留编号,但 Markdown 源文也应避免编号标题。

```text
🧭 <代码> 技术面快照 ｜<as-of>
① 格局：<档> ② 动量：<档> ③ 信号：看多x/看空y(净<方向>)
④ 趋势：<档>（图）⑤ 期权结构：<优秀/一般/弱>，CallWall <价>/PutWall <价>/Flip <价>/PCR <值>（图）
⑥ 资金：<净流入/出>，主力堆积区 <价>，压力 <…>｜支撑 <…>（图）
⑦ 社媒：WSB <热度> / X <热度>，喊单 <方向>，拥挤度 <档>，HYPE <阶段>，监控评分 <x/10>
———
综合:多空合力偏<方向>,关键看 <1-2 个最重要的位/信号>。 ⚠️ 技术面是概率不是承诺。
```

矛盾要显式说清(如"格局多头但动量顶背离 + 现价在 Gamma Flip 上方=易高位黏滞")。

报告最底部必须有 `## 术语解释`。覆盖文中出现的所有专业缩写和交易/财务术语;至少包括:GEX、Gamma、OI、IV、Call Wall、Put Wall、Gamma Flip、GEX PCR、PCR、RSI、MACD、ADX/DI、ROC、ATR、MA20/MA50/MA200、Volume Profile、POC、支撑/压力、WSB、X/Twitter 热度、HYPE 阶段、YOLO、0DTE、FOMO、bag-holder、ATM、稀释、warrant、convertible notes、non-GAAP、CapEx、operating cash flow、hyperscaler、800G/1.6T、CPO、pluggable optics、thesis、as-of。解释必须简短、面向本报告语境,不要写成百科长文。

## 五、红线与诚实层(始终生效)
- **不是投资建议**,是技术面信息整理供参考;真金白银自己 DYOR;Claude 不是持牌投顾。
- **绝不自主下单/交易/撤改单/移动资金/行权**;长桥写工具一律不碰。
- 技术指标是**概率与历史规律,不是必然**;不给"必涨/必跌""一定到某价"的承诺。
- GEX 是基于公开 OI + 标准 dealer 持仓假设的**估算**(真实做市商持仓不可知),必须如此限定;数据不全时如实说近似。
- WSB/X 热度是社媒样本,必须标注 as-of 与样本缺口;不可把 KOL/社区喊单当成已证实事实或交易指令。
- 数字标 as-of + 来源;区分 已证实(行情原值)/ 推断(指标计算)/ 推测(对盘面行为的解读)。
- 不附和用户既有多空倾向;指标不支持就说不支持。

## 六、中文表达规范
术语保留:RSI/MACD/ADX/OI/gamma/GEX/Call Wall/Put Wall 等;首次出现给一句中文(如 Gamma Flip=零伽马翻转位、OI=未平仓量、Volume Profile=成交量分布),并在报告末尾集中放入术语解释。加粗克制,只标真结论/关键位/关键数值。

报告正文落盘前必须按 `stop-ai-slop-zh` 做一次中文表达体检:删套话、拆排比三件套、去名词化,避免"首先/其次/综上"式八股段落。只改表达,不得删指标数值、图表引用、as-of 时间、数据缺口、术语解释或风险声明。
