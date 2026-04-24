---
name: jq-strategy
description: |
  聚宽（JoinQuant）量化策略代码生成器 —— 把用户的自然语言策略描述翻译成可直接粘贴到 joinquant.com 网页回测的完整 Python 策略文件。
  只要用户在谈论选股规则、买卖条件、调仓频率、回测一个投资想法，哪怕没明确说"聚宽"或"写代码"，也应该立即触发本 skill —— 因为把模糊的策略想法变成可回测代码是这个 skill 的核心价值，而用户往往不知道有这个工具可用。
  触发场景包括但不限于：描述一个选股规则（"选市值最小的 N 只"、"破净股"、"高 ROE"）、描述一个买卖信号（"5 日线上穿 20 日线"、"MACD 金叉"）、提到要做回测、要验证一个投资想法、要写量化策略、问怎么把想法变成代码。
  触发词：/jq-strategy、写个策略、写个聚宽策略、生成聚宽代码、帮我写量化代码、策略回测代码、把这个策略写出来、小市值策略、均线策略、多因子策略、破净策略、红利策略、帮我回测、这个想法能不能回测、聚宽代码。
version: 1.1.0
created: 2026-04-24
updated: 2026-04-24
changelog:
  - 1.0.0: 初版 - 支持选股/择时/多因子/ETF 轮动四类策略
  - 1.1.0: 按 skill-creator 规范重构 - API 速查挪到 reference/、补齐 3 个 examples、加公网分发文件
---

# 聚宽策略代码生成器

把用户的自然语言描述翻译成**可直接在 joinquant.com 回测**的聚宽 Python 策略。

用户拿到代码 → 登录 joinquant.com → 策略 → 新建 → 粘贴 → 设日期 → 跑回测。

---

## 为什么需要这个 skill

用户往往只有模糊的投资想法（"我想试试选市值小的股票"），而聚宽的 API 有几十个函数和专有对象（`get_fundamentals` / `query` / `valuation` / `run_daily` 等），直接上手门槛不低。本 skill 负责这层翻译，让用户专注在**策略逻辑**而不是 API 细节上。

---

## 🎯 工作流程

### 1. 解析需求

从用户描述里抽出 5 个要素。缺失的要素填默认值 —— **不要反问**，Auto 模式偏执行：

| 要素 | 默认值 | 说明 |
|------|--------|------|
| 标的池 | 全 A 股 | 也可指定指数成分（沪深 300 / 中证 500）或几只 ETF |
| 选股规则 | —— | 必须从描述里提取；如完全没线索，按"市值最小"兜底 |
| 择时规则 | 开盘时 | `run_daily(trade, 'open')` |
| 调仓频率 | 每 5 交易日 | 可改每日 / 每周 / 每月 / 信号触发 |
| 持仓数量 | 3 只 | |

### 2. 选骨架

根据需求类型挑一个模板（完整模板见 `reference/templates.md`，有 4 类）：

- **选股轮动**（定期按基本面选 N 只）→ 大多数选股类策略
- **择时信号**（技术指标触发买卖）→ 单标的 + 均线/MACD/RSI
- **多因子打分**（多指标综合打分选 top N）→ 低 PE + 高 ROE 组合
- **ETF 轮动**（几只 ETF 间切换）→ 动量轮动

### 3. 填充代码

三个必须写对的部分：

1. **`initialize(context)`** —— 基准、手续费、全局变量、调用频率
2. **选股/择时函数** —— 核心策略逻辑
3. **`trade(context)`** —— 调仓执行（卖旧 → 买新）

**纪律**：所有选股策略都必须加 `filter_paused` + `filter_st`。停牌和 ST 股在聚宽回测里会产生假成交，必须过滤掉。这不是可选项。

具体 API 用法见 `reference/api-cheatsheet.md`。

### 4. 输出

按以下顺序给用户：

1. 完整 `.py` 代码块（可复制）
2. **保存到** `~/perfect21/investment/strategies/<策略名>.py`（目录不存在先创建）
3. 参数摘要表（让用户一眼看懂这段代码在做什么）
4. 回测设置建议（起止日期 / 初始资金 / 基准）
5. 一行使用说明：登录 joinquant.com → 策略 → 新建 → 粘贴 → 跑回测

---

## 🧩 自然语言 → 聚宽语法映射

这是最核心的翻译表。用户描述中出现下列词时按映射来：

| 用户说 | 翻译成 |
|--------|--------|
| "小市值" / "市值最小的" | `.order_by(valuation.market_cap.asc())` + 取前 N |
| "市值 X 到 Y 亿" | `valuation.market_cap.between(X, Y)` |
| "低 PE" / "低估值" | `valuation.pe_ratio < 20` + `valuation.pe_ratio > 0`（排除亏损）|
| "破净" | `valuation.pb_ratio < 1` |
| "高 ROE" | `indicator.roe > 15` |
| "成长股" | `indicator.inc_revenue_year_on_year > 20` |
| "高分红" / "红利" | `valuation.dividend_yield_ratio > 3` |
| "沪深 300" | `get_index_stocks('000300.XSHG')` |
| "中证 500" | `get_index_stocks('000905.XSHG')` |
| "均线金叉" | 短 MA 上穿长 MA（需 `get_price` 算）|
| "每日" / "每根 bar" | `run_daily(trade, 'every_bar')` |
| "每周调仓" | `run_weekly(trade, weekday=1)` |
| "每月调仓" | `run_monthly(trade, monthday=1)` |
| "每 N 天调仓" | 用 `g.days` 计数器（见 `examples/small-cap.py`）|
| "开盘买入" | `time='open'` |
| "收盘买入" | `time='close'` |
| "止损 X%" | `run_daily` 里查持仓收益率 < -X% 就清仓 |

---

## 📏 输出规范

1. **完整可粘贴** —— 不省略导入、过滤器、默认配置。用户要能复制进去就跑。
2. **顶部写文档字符串** —— 策略说明 + 推荐回测区间 + 推荐资金
3. **保存到 `~/perfect21/investment/strategies/<名字>.py`** —— 名字用 kebab-case（如 `small-cap.py`、`ma-cross-510300.py`）
4. **参数表放代码后**，Markdown 表格形式
5. **诚实边界** —— 如果用户想要的东西聚宽不支持（实时 tick、外部 API 调用、非 A 股标的），直接告诉用户，不要硬编出跑不起来的代码

---

## 🧪 工作示例

**用户输入**：选市值 20-30 亿，每 5 天换仓，买最小的 3 只

**skill 的处理**：
- 类型：选股轮动
- 模板：`template_stock_rotation`
- 要素：全 A 股池 / 市值 20-30 亿 / 每 5 交易日 / 持 3 只 / 市值升序
- 参考 `examples/small-cap.py`（这就是这个输入对应的标准产出）

其他场景的完整示例：

- **均线择时**：`examples/ma-cross.py` —— 5 日线上穿 20 日线买 510300，死叉清仓
- **多因子打分**：`examples/multi-factor.py` —— 沪深 300 里 低 PE + 高 ROE + 低负债率综合打分，月度调仓持 10 只

---

## 📂 文件指引

- **`reference/api-cheatsheet.md`** —— 聚宽所有核心 API 速查（`initialize` / `get_fundamentals` / `query` / 交易函数 / 过滤器 / 行情数据）。写代码时遇到不确定的 API 就去查。
- **`reference/templates.md`** —— 4 类策略完整骨架，填空式使用。新需求先从这里挑一个骨架再填内容。
- **`examples/`** —— 3 个完整工作案例，可直接复用或改写。

---

## 🚫 不要做的事

- 不要在 SKILL.md 或聊天里给用户整份 API 文档 —— 用户要的是能跑的代码，不是教程
- 不要给本地可跑的 backtrader / rqalpha 代码 —— 那是另一个 skill 的事，聚宽代码只能在聚宽网页跑
- 不要反问"你想要什么基准 / 手续费 / 资金"等细节 —— 填默认值，用户不满意自己改
- 不要在代码里引用聚宽外的本地文件、外部 API —— 聚宽沙箱不允许
