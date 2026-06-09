---
name: technical-analysis
description: 个股技术面分析模块——对单只美股给出「格局/动量/信号/趋势/期权结构/资金」六维结构化判读,数据优先取长桥 Longbridge MCP 只读行情(K线/盘口/期权链),并用 Python(matplotlib)出 PNG 图表:趋势证据图、Gamma Exposure 柱形图(标 Call Wall/Put Wall、GEX PCR)、资金流向与主力筹码标尺(压力位/支撑位)。当用户说"看看 XXXX 的技术面/技术分析""现在是多头还是空头格局""画个 GEX/期权结构图""这只票的压力位支撑位在哪""动量/趋势强不强"时使用。⚠️ 只做分析,绝不下单/交易。始终简体中文。
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

## 三、出图(Python / matplotlib → PNG)

图表脚本在同目录 `scripts/charts.py`。流程:**长桥取数 → 整理成脚本要的 JSON/CSV → 调脚本生成 PNG → 用 present_files 给用户(或嵌进研报)**。

```bash
# 趋势证据图:需要 OHLC + 日期序列
python scripts/charts.py trend   --input <ohlc.json>   --out <symbol>_trend.png   --symbol NVDA
# Gamma Exposure 柱形图:需要逐 strike 的 {strike, call_oi, put_oi, gamma, spot}
python scripts/charts.py gex     --input <chain.json>  --out <symbol>_gex.png     --symbol NVDA
# 资金流向 + 筹码标尺:需要 {price_bins, volume_at_price, supports[], resistances[]}
python scripts/charts.py flow    --input <flow.json>   --out <symbol>_flow.png    --symbol NVDA
```

脚本无第三方依赖即可跑(只需 `matplotlib`、`numpy`;缺则 `pip install matplotlib numpy --break-system-packages`)。各子命令的输入 JSON 字段见脚本顶部 docstring。GEX 计算逻辑内置在脚本里,与上面 ⑤ 一致——传原始期权链即可。

## 四、输出契约(必守)

**结论先行**,六维各一段:`【维度】判档(关键数值,as-of) — 一句因由`,需要图的维度(④⑤⑥)附对应 PNG。结尾给:

```text
🧭 <代码> 技术面快照 ｜<as-of>
① 格局：<档> ② 动量：<档> ③ 信号：看多x/看空y(净<方向>)
④ 趋势：<档>（图）⑤ 期权结构：<优秀/一般/弱>，CallWall <价>/PutWall <价>/Flip <价>/PCR <值>（图）
⑥ 资金：<净流入/出>，主力堆积区 <价>，压力 <…>｜支撑 <…>（图）
———
综合:多空合力偏<方向>,关键看 <1-2 个最重要的位/信号>。 ⚠️ 技术面是概率不是承诺。
```

矛盾要显式说清(如"格局多头但动量顶背离 + 现价在 Gamma Flip 上方=易高位黏滞")。

## 五、红线与诚实层(始终生效)
- **不是投资建议**,是技术面信息整理供参考;真金白银自己 DYOR;Claude 不是持牌投顾。
- **绝不自主下单/交易/撤改单/移动资金/行权**;长桥写工具一律不碰。
- 技术指标是**概率与历史规律,不是必然**;不给"必涨/必跌""一定到某价"的承诺。
- GEX 是基于公开 OI + 标准 dealer 持仓假设的**估算**(真实做市商持仓不可知),必须如此限定;数据不全时如实说近似。
- 数字标 as-of + 来源;区分 已证实(行情原值)/ 推断(指标计算)/ 推测(对盘面行为的解读)。
- 不附和用户既有多空倾向;指标不支持就说不支持。

## 六、中文表达规范
术语保留:RSI/MACD/ADX/OI/gamma/GEX/Call Wall/Put Wall 等;首次出现给一句中文(如 Gamma Flip=零伽马翻转位、OI=未平仓量、Volume Profile=成交量分布)。加粗克制,只标真结论/关键位/关键数值。
