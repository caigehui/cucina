---
name: mirofish-simulation
description: 用 MiroFish 做美股研究情景仿真、事件推演、多智能体模拟、模拟报告导入或 seed 包准备时使用。适用于用户提到 MiroFish、情景推演、仿真、沙盘、多智能体预测、把研报投喂给 MiroFish、导入 MiroFish 报告等请求。
---

# MiroFish 情景仿真

本 skill 只把 MiroFish 作为 Cucina 的研究仿真旁路。MiroFish 输出不能当成行情事实、财报事实、价格目标或交易指令。

## 硬边界

- 不下单、不撤单、不改单、不移动资金、不创建提醒、不改自选列表。
- 不让 MiroFish 读取券商账户、长桥账户或任何交易系统。
- 默认不上传精确账户资产、精确成本、精确持仓数量、订单、流水、API Key、token、cookie 或私钥。
- MiroFish 输出只能归类为“模拟推断/推测”,必须回到 Cucina 中与长桥、官方公告、SEC/IR、宏观数据、新闻和技术面交叉验证。
- 涉及仓位动作时,只能写成“若...则可考虑...”的情景预案,不能写成无条件买/卖/止损/止盈指令。

## 工作流

1. 明确投研问题、标的、推演窗口和 seed 材料来源。
2. 优先使用公开材料或脱敏摘要;如果用户给了真实持仓,先改写成暴露描述,不要写入精确资产、成本或数量。
3. 用本项目脚本生成 seed 包:

```powershell
python scripts/mirofish_bridge.py seed --topic '<topic>' --question '<question>' --symbol <SYMBOL> --input <sanitized-input.md> --horizon '<window>'
```

4. 让用户在独立 MiroFish 服务中运行模拟。不要把 MiroFish 源码复制进 Cucina。
5. 用户提供或导出报告后,导入到同一个仿真目录:

```powershell
python scripts/mirofish_bridge.py import-report --run-dir <output/simulations/...> --report <mirofish-report.md>
```

6. 从 `summary_for_cucina.md` 继续整理摘要,必须分清事实、模拟推断、推测、触发条件和证伪条件。

## 输出位置

```text
output/simulations/<YYYY-MM-DD>_<topic-slug>/
```

标准文件:

```text
seed.md
scenario.json
mirofish_report.md
summary_for_cucina.md
```

## 输出格式

```text
【MiroFish 情景推演】<主题>
- seed/as-of:
- 输入材料:
- 模拟推断:
- 推测假设:
- 关键触发条件:
- 证伪条件:
- 需要回到 Cucina 验证的数据:
```

结尾必须保留:

```text
以上为研究分析与信息整理,不是持牌投顾建议;交易需用户自行核实和决策。
```
