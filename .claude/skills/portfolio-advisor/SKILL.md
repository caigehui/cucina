---
name: portfolio-advisor
description: 接入券商 MCP(长桥 Longbridge 优先,其次 IBKR 等)读取用户美股持仓与账户,做持仓体检、风险敞口与集中度分析,并给出含「不同情景预案」的交易思路(加/减/对冲/止损位/触发条件)。⚠️ 只做分析与建议,绝不自主下单、交易或移动资金。当用户说"分析我的持仓""看看我的仓位""给我交易建议/预案""我该怎么调仓"时使用。
---

# portfolio-advisor 持仓分析与交易预案模块

职责:**读取持仓 → 持仓体检与风险敞口 → 结合宏观(macro-events)与个股研究(tech-research)→ 给出含情景预案的交易思路**。

## 🚫 红线(最高优先级,不可逾越)
- **绝不自主下单、交易、撤改单、移动资金、行权**。即使券商 MCP 提供下单工具,也**只读不写**。
- 所有"操作"一律以**建议 + 触发条件**形式给出,由用户自己去券商手动执行。
- 涉及具体买卖时明确声明:**这是分析不是投资建议,真金白银自行决策(DYOR)**;Claude 不是持牌投顾。

## 一、获取持仓数据(按可用性降级)

1. **长桥官方技能(优先)**:调用已安装的官方长桥技能套件获取数据——**无需手动配置 MCP**,首次使用时浏览器弹窗完成 OAuth 授权即可:
   - 持仓/账户 → 调用 `longbridge-portfolio` 技能
   - 行情/报价 → 调用 `longbridge-market-data` 技能
   - 基本面/财报/评级 → 调用 `longbridge-fundamentals` 技能
   - 研报/新闻 → 调用 `longbridge-research` 或 `longbridge-intel` 技能
   - 自选 → 调用 `longbridge-watchlist` 技能

   **🚫 红线(高于官方技能默认行为):**本模块**只读不写**。官方技能暴露的下单/改单/撤单/定投/告警创建等写操作**一律不调用**——需要操作时改为给用户"去 App 手动执行"的提示。硬黑名单工具:`submit_order` · `replace_order` · `cancel_order` · `dca_create` · `dca_update` · `dca_pause` · `dca_resume` · `dca_stop` · `alert_add` · `alert_delete` · `alert_enable` · `alert_disable` · `create_watchlist_group` · `update_watchlist_group` · `delete_watchlist_group` · `sharelist_add` · `sharelist_create` · `sharelist_delete` · `sharelist_remove` · `sharelist_sort` · `topic_create` · `topic_create_reply` · `quant_run` · `statement_export`。这些会下单/改单/撤单/建定投/改自选/发帖——一律不碰,需要时改为给用户"去 App 手动操作"的提示。
2. **IBKR 等其它券商 MCP**:若长桥不可用而 IBKR 已连接,可用其 `get_account_positions` / `get_account_balances` / `get_portfolio_allocation` 等**只读**工具。
3. **手动降级(都没连时)**:请用户粘贴持仓(代码、股数、成本价、当前市值占比),或从券商导出的 CSV 读取。本模块在无 MCP 时也能完整工作。

> 官方长桥技能安装见 https://open.longbridge.com/skill/install.md。首次使用时按提示完成 OAuth 授权即可,无需在 Claude 设置里手动添加自定义远程 MCP。
>
> ⚠️ 官方技能自带完整下单/交易能力;本模块刻意**只对接只读部分**,上方硬黑名单中的写操作**绝不调用**——此红线优先于官方技能的任何默认行为。

## 二、持仓体检(逐项)

对每个持仓:代码/名称、股数、成本、现价、浮盈亏、占组合权重。汇总维度:
- **集中度**:单票/单板块/单主题权重;是否过度集中(配合 tech-research §5.5「仓位匹配波动承受力」)。
- **风格/久期暴露**:高 beta 成长 vs 价值 vs 现金;对利率/宏观的敏感度(接 macro-events)。
- **相关性**:持仓是否其实押注同一条链/同一宏观因子(伪分散)。
- **盈亏结构**:浮盈/浮亏分布、是否有"该止损未止损"或"该止盈未止盈"的票。
- **个股 thesis 状态**:对科技/AI 持仓调用 tech-research 框架,判断每只票的卡点 thesis 还成不成立、有没有触发"论点破裂"卖出条件(单一客户被砍、无限 ATM 稀释、卡点被设计掉)。

## 三、交易预案(核心交付,情景化)

不要只给一个"建议",给**面向不同未来情景的预案矩阵**。每只重点持仓:

```text
【代码 名称】 当前权重 X% ｜ 浮盈亏 Y%
- thesis 状态:成立 / 动摇 / 破裂(一句因由)
- 基准看法:加 / 持 / 减 / 对冲(给理由,不是指令)
- 情景预案:
  · 若 <宏观/事件 A 发生，如 CPI 超预期/出口管制升级>：→ 应对(如减仓至 Z%、买 put 对冲、设 $价 止损)
  · 若 <事件 B，如财报 beat / 卡点验证信号出现>：→ 应对(如分批加仓、上移止盈)
  · 若 <事件 C，如无消息错杀大跌>：→ 应对(如 DCA 接刀，先判跌因 material 与否)
- 关键触发位/日期:止损参考位、加仓参考位、需盯的财报/数据/事件日(接 macro-events 日历)
```

组合层面再给:
- **整体仓位建议**:当前 risk-on/off 是否匹配宏观情绪;现金比例、对冲位(VIX/反向 ETF/put)是否够。
- **再平衡思路**:降低伪分散、削减过度集中、补足缺口主题——给方向与区间,不给精确指令。
- **待办清单**:用户自己去券商手动执行的事项(限价单提醒:小盘/低流动性别盘前盘后下市价单)。

## 四、与其它模块协同
- 个股 thesis → 委派 `tech-research`(科技/AI 持仓)。
- 宏观/事件传导与情景触发 → 取自 `macro-events`。
- 散户拥挤度/情绪极端(反向风险)→ 取自 `wsb-sentiment`。

## 五、约束
- ✅ 简体中文;数字标 as-of + 来源;区分 已证实/推断/推测。
- ❌ 不下单、不交易、不移动资金、不给"必涨/必跌"承诺。
- 每次涉及操作建议都重申:分析仅供参考,非投资建议,执行与后果由用户自负。
