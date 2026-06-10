# MiroFish 旁路集成设计

## 背景

Cucina 是个人美股投研工作台,职责是读取只读数据、交叉验证事实、生成研报和情景预案。MiroFish 是独立的多智能体仿真/预测系统,上游 README 将其描述为通过种子材料构建图谱、生成智能体、运行模拟并输出预测报告的引擎。两者可以互补,但职责边界必须保持清晰:

- Cucina 负责事实采集、来源标注、持仓/宏观/个股分析和最终投研表达。
- MiroFish 负责围绕一个明确问题做情景仿真,其输出只作为“模拟推断/推测”输入 Cucina。
- MiroFish 不读取券商账户,不调用长桥写工具,不生成无条件交易指令。

上游 MiroFish 需要独立运行环境:Node.js 18+、Python 3.11-3.12、uv、LLM API Key 和 Zep Cloud Key;默认前端端口为 3000,后端 API 端口为 5001。其许可为 AGPL-3.0,因此第一版不把 MiroFish 源码复制进 Cucina,只通过独立服务、容器或手工导出的报告进行旁路集成。

## 目标

第一版集成要让用户可以从 Cucina 中准备一份可投喂 MiroFish 的“脱敏种子包”,并把 MiroFish 生成的报告导回 Cucina 的本地输出目录,形成可审计的情景推演材料。

交付范围:

1. 新增 `scripts/mirofish_bridge.py`,提供两个本地命令:
   - `seed`: 根据主题、问题、输入材料和标的生成 MiroFish seed 包。
   - `import-report`: 将 MiroFish 报告导入同一仿真目录,并生成 Cucina 摘要骨架。
2. 新增 `tests/test_mirofish_bridge.py`,覆盖 seed 包生成、路径命名、报告导入和边界声明。
3. 新增 `docs/mirofish-integration.md`,说明部署边界、推荐工作流、隐私规则和输出目录。
4. 新增本地 skill `mirofish-simulation`,并同步 `.agents/skills/` 与 `.claude/skills/`。
5. 更新 `README.md` 与 `AGENTS.md`,加入 MiroFish 路由和 `output/simulations/` 目录约定。

## 非目标

- 不在本仓库 vendor MiroFish 源码。
- 不自动启动 Docker 或长期后台服务。
- 不把 MiroFish 接入长桥账户或任何交易/提醒/自选列表写工具。
- 不把 MiroFish 输出当成价格预测结论或买卖指令。
- 不把精确账户资产、成本、订单、券商流水等敏感信息默认发送给 MiroFish/Zep/LLM。

## 架构

第一版采用“文件桥接”而不是“强 API 耦合”:

```text
Cucina skills / user inputs
        |
        v
scripts/mirofish_bridge.py seed
        |
        v
output/simulations/<YYYY-MM-DD>_<slug>/
        |-- seed.md
        |-- scenario.json
        |-- summary_for_cucina.md
        |
        v
MiroFish 独立服务/网页/容器
        |
        v
scripts/mirofish_bridge.py import-report
        |
        v
output/simulations/<YYYY-MM-DD>_<slug>/mirofish_report.md
```

`seed.md` 是给 MiroFish 的输入材料,包含边界声明、投研问题、标的/主题、输入材料和推荐仿真提示词。`scenario.json` 是机器可读元数据,记录 as-of、主题、问题、输入文件路径、输出契约和隐私等级。`summary_for_cucina.md` 是导回 Cucina 后可继续编辑的摘要骨架,明确分层为事实、模拟推断、推测、触发条件和证伪条件。

## 数据与隐私规则

默认只传脱敏材料。允许写入 seed 的内容包括:

- 公开新闻、公司公告、SEC/IR 摘要、宏观事件、技术结构、期权结构摘要。
- 脱敏组合暴露,例如“AI 供应链高 beta 暴露偏高”“单票集中度较高”。
- 用户明确提供且允许用于仿真的文本材料。

默认禁止写入 seed 的内容包括:

- 券商账号、订单号、流水、精确资产、精确成本、精确持仓数量。
- API Key、OAuth token、cookie、私钥。
- 任何会导致 MiroFish 代替用户执行交易或写入券商系统的指令。

脚本不会主动连接券商或 MiroFish,只生成/归档本地文件。任何外部上传动作由用户在 MiroFish 独立界面或服务中手工完成。

## 输出契约

所有 MiroFish 集成输出统一放在:

```text
output/simulations/<YYYY-MM-DD>_<topic-slug>/
```

标准文件:

```text
seed.md
scenario.json
mirofish_report.md
summary_for_cucina.md
raw_response.json
```

其中 `raw_response.json` 仅在未来 API 自动化版本中使用。第一版脚本不创建空的 `raw_response.json`,避免伪造上游返回。

## 错误处理

- 输入文件不存在:命令失败并返回非零退出码。
- 输出目录已存在:默认复用目录并覆盖脚本生成的 `seed.md`、`scenario.json`、`summary_for_cucina.md`;不会删除用户额外文件。
- 导入报告路径不存在:命令失败并返回非零退出码。
- 缺少 topic/question:命令失败并提示必填参数。
- 内容里出现明显密钥字段:脚本生成 seed 时标记 `privacy_warnings`,但不尝试可靠脱敏;用户必须自行复核。

## 验证

最小验证命令:

```powershell
rtk powershell -NoProfile -Command "python -m unittest tests.test_mirofish_bridge -v"
rtk powershell -NoProfile -Command "python scripts/mirofish_bridge.py --help"
```

验收标准:

- 单元测试通过。
- `seed` 命令能生成 `seed.md`、`scenario.json`、`summary_for_cucina.md`。
- `import-report` 命令能复制报告到 `mirofish_report.md`,并更新摘要骨架中的报告引用。
- `.agents/skills/mirofish-simulation/SKILL.md` 与 `.claude/skills/mirofish-simulation/SKILL.md` 内容一致。
- README 和 AGENTS 均说明 MiroFish 是研究仿真旁路,不是交易执行模块。
