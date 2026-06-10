# MiroFish 情景仿真旁路集成

MiroFish 在 Cucina 中的定位是“研究仿真旁路”:Cucina 先把已验证或用户提供的材料整理成脱敏 seed 包,用户再把 seed 投喂给独立运行的 MiroFish,最后将 MiroFish 生成的报告导回 Cucina 输出目录。MiroFish 输出只能作为模拟推断/推测,不能替代行情、公告、财报、SEC 文件、宏观数据或长桥只读数据。

## 边界

- 不把 MiroFish 源码 vendor 到本仓库。
- 不让 MiroFish 读取券商账户、长桥持仓或任何交易系统。
- 不让 MiroFish 下单、撤单、改单、创建提醒、修改自选列表或移动资金。
- 不默认上传精确账户资产、精确成本、精确持仓数量、订单、流水、API Key、token、cookie 或私钥。
- 不把 MiroFish 输出写成必涨、必跌、必到某价或无条件买卖指令。

## 输出目录

所有仿真材料写入:

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

`seed.md` 是投喂 MiroFish 的种子材料。`scenario.json` 是机器可读元数据。`mirofish_report.md` 是从 MiroFish 导回的报告。`summary_for_cucina.md` 是可嵌入研报或持仓预案的摘要骨架。

## 生成 seed 包

先把公开材料或已脱敏材料保存为一个本地输入文件,例如:

```text
output/tmp/nvda_seed.md
```

再运行:

```powershell
rtk powershell -NoProfile -Command "python scripts/mirofish_bridge.py seed --topic 'NVDA earnings simulation' --question '若毛利率下修,AI 供应链叙事如何变化?' --symbol NVDA --input output/tmp/nvda_seed.md --horizon '2 weeks'"
```

命令会输出 seed 包目录,并生成 `seed.md`、`scenario.json`、`summary_for_cucina.md`。

如果输入材料出现 `API_KEY`、`TOKEN`、`SECRET`、`PASSWORD`、`PRIVATE_KEY` 等明显密钥字段,脚本会在 `scenario.json` 中写入 `privacy_warnings`。这只是提示,不是可靠脱敏器;用户仍需人工复核。

## 在 MiroFish 中运行

1. 独立启动 MiroFish,推荐使用其上游 README 提供的源码或 Docker 方式。
2. 将 `seed.md` 作为种子材料上传或粘贴到 MiroFish。
3. 用 `seed.md` 末尾的仿真提示词启动图谱构建、模拟和报告生成。
4. 导出 MiroFish 生成的 Markdown 报告。

MiroFish 上游默认端口是前端 `3000`、后端 API `5001`。如果本机已有服务占用这些端口,先在 MiroFish 独立项目里调整,不要改 Cucina 的投研目录约定。

## 导入 MiroFish 报告

拿到 MiroFish 报告后运行:

```powershell
rtk powershell -NoProfile -Command "python scripts/mirofish_bridge.py import-report --run-dir output/simulations/2026-06-10_nvda-earnings-simulation --report C:\path\to\mirofish_report.md --as-of 2026-06-10"
```

导入后:

- 报告复制为 `mirofish_report.md`。
- `summary_for_cucina.md` 会追加导入记录。
- 后续研报或持仓预案只能引用其中的模拟推断、推测假设、触发条件和证伪条件。

## 可进入研报的写法

推荐写法:

```text
MiroFish 情景推演显示,在“毛利率下修 + 市场仍相信长期 AI capex”情景下,市场叙事可能从单季业绩转向订单能见度。该结论属于模拟推断,需要用公司指引、客户 capex、期权结构和资金流继续验证。
```

禁止写法:

```text
MiroFish 预测 NVDA 会涨,建议立即买入。
```

结尾必须保留风险声明:

```text
以上为研究分析与信息整理,不是持牌投顾建议;交易需用户自行核实和决策。
```
