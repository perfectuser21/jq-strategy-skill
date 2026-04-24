# jq-strategy

聚宽（JoinQuant）量化策略代码生成器 · Claude Code Skill

用自然语言描述一个策略，Claude 生成可直接粘贴到 [joinquant.com](https://www.joinquant.com/) 回测的完整 Python 代码。

---

## 这个 skill 解决什么问题

聚宽是国内最流行的 A 股量化研究平台之一，但它的 API 有几十个专属对象（`get_fundamentals` / `query` / `valuation` / `run_daily`），新手往往有策略想法却卡在 API 上。

装上这个 skill 后，你对 Claude 说：

> 写个策略，在沪深 300 里选 PE 最低的 5 只，每月初调仓

Claude 就会输出一份完整的聚宽策略文件（含手续费、过滤 ST/停牌、中文注释），你复制粘贴到 joinquant.com 的策略编辑器就能跑回测。

---

## 安装（二选一）

### 方式 1：一键安装

```bash
curl -sL https://raw.githubusercontent.com/perfectuser21/jq-strategy-skill/main/install.sh | bash
```

### 方式 2：git clone

```bash
git clone https://github.com/perfectuser21/jq-strategy-skill.git \
  ~/.claude/skills/jq-strategy
```

安装后重启 Claude Code 即可，skill 会自动被识别。

---

## 使用方式

直接在 Claude Code 里用自然语言描述策略，任一下列方式都能触发：

```
写个策略，选市值 20-30 亿，每 5 天调仓持有最小的 3 只
```

```
/jq-strategy 破净股 + ROE>15，月度调仓持 10 只
```

```
帮我写个均线策略，510300 5 日线上穿 20 日线买入，死叉清仓
```

Claude 会输出：

1. 完整的 `.py` 策略代码
2. 参数摘要表
3. 推荐回测区间 / 初始资金
4. 使用指引（登录 joinquant.com → 新建策略 → 粘贴 → 跑回测）

---

## 已覆盖的策略类型

| 类型 | 典型场景 | 示例 |
|-----|---------|-----|
| 选股轮动 | 按基本面定期选 N 只 | 小市值、低估值、高 ROE、红利 |
| 择时信号 | 技术指标触发买卖 | 均线金叉、MACD、RSI |
| 多因子打分 | 多指标加权排名 | 价值 + 质量 + 成长 综合选股 |
| ETF 轮动 | 几只 ETF 切换 | 股债轮动、风格轮动 |

每类都有现成骨架（`reference/templates.md`）和完整示例（`examples/`），Claude 按描述填空。

---

## 目录结构

```
jq-strategy/
├── SKILL.md                         # 主指令（Claude 加载）
├── reference/
│   ├── api-cheatsheet.md            # 聚宽 API 速查表
│   └── templates.md                 # 4 类策略骨架
├── examples/
│   ├── small-cap.py                 # 小市值选股
│   ├── ma-cross.py                  # 均线择时
│   └── multi-factor.py              # 多因子打分
├── install.sh
├── README.md
└── LICENSE
```

---

## 前置要求

- [Claude Code](https://claude.com/claude-code) 已安装
- joinquant.com 账号（免费即可回测，数据需升级套餐）

本 skill **只生成聚宽格式的代码**，代码必须在聚宽平台上跑。如果你要本地可跑的回测代码（backtrader / rqalpha / Qlib），等后续版本。

---

## 边界

- **只支持聚宽平台**：代码用的是聚宽专属 API，在本地 Python 环境跑不起来
- **只覆盖 A 股 / 国内 ETF / 场内基金**：聚宽不支持美股、加密货币、港股
- **静态策略为主**：复杂的事件驱动、高频、跨市场套利不在 skill 骨架覆盖范围

---

## 贡献

发现 Claude 生成的代码有问题、想加新的策略类型或 API 用法，欢迎 PR。改动主要集中在：

- `SKILL.md` —— 翻译规则、输出规范
- `reference/templates.md` —— 新增策略骨架
- `reference/api-cheatsheet.md` —— API 扩充
- `examples/` —— 新增完整示例

---

## License

MIT
