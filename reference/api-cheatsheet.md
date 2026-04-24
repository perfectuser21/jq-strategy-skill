# 聚宽 API 速查

写代码时查这份。所有函数都是聚宽平台专属，只能在 joinquant.com 的策略编辑器或研究 Notebook 里使用。

---

## 初始化 & 全局配置

```python
def initialize(context):
    set_benchmark('000300.XSHG')        # 基准，默认沪深 300
    set_option('use_real_price', True)  # 真实价格复权
    set_option('order_volume_ratio', 1)
    set_order_cost(OrderCost(
        open_tax=0, close_tax=0.001,
        open_commission=0.0003, close_commission=0.0003,
        close_today_commission=0, min_commission=5
    ), type='stock')

    # 全局变量挂在 g 上（context 不能放自定义属性）
    g.stocknum = 3
    g.refresh_rate = 5
    g.days = 0

    # 运行频率（三选一）
    run_daily(trade, 'every_bar')        # 每日，'open' / 'close' / 'every_bar'
    run_weekly(trade, weekday=1)         # 每周一
    run_monthly(trade, monthday=1)       # 每月第一个交易日
```

---

## 选股查询：`get_fundamentals(query)`

聚宽的核心选股接口。类 SQLAlchemy 语法。

### 四张核心表

| 表 | 字段（举例） |
|----|-------------|
| `valuation` | `market_cap`(亿元总市值) / `circulating_market_cap` / `pe_ratio` / `pb_ratio` / `ps_ratio` / `turnover_ratio` / `dividend_yield_ratio` |
| `indicator` | `eps` / `roe` / `roa` / `net_profit_margin` / `gross_profit_margin` / `inc_revenue_year_on_year`（营收同比）|
| `balance` | `total_assets` / `total_liability` / `total_owner_equities` |
| `income` | `total_operating_revenue` / `net_profit` / `operating_profit` |
| `cash_flow` | `net_operate_cash_flow` |

### 典型查询

```python
# 市值 20-30 亿 + PE<30 + ROE>10，按市值升序
q = query(
    valuation.code,
    valuation.market_cap,
    valuation.pe_ratio,
    indicator.roe,
).filter(
    valuation.market_cap.between(20, 30),
    valuation.pe_ratio < 30,
    valuation.pe_ratio > 0,      # 排除亏损
    indicator.roe > 10,
).order_by(
    valuation.market_cap.asc()
)
df = get_fundamentals(q)
stocks = list(df['code'])
```

### 指数成分股内筛选

```python
pool = get_index_stocks('000300.XSHG')  # 沪深 300
q = query(valuation.code, valuation.pe_ratio).filter(
    valuation.code.in_(pool),
    valuation.pe_ratio > 0,
)
```

---

## 交易函数

| 函数 | 语义 |
|------|------|
| `order(security, amount)` | 按股数下单（正买负卖）|
| `order_value(security, value)` | 按**金额**下单 |
| `order_target(security, amount)` | 调整到**目标股数** |
| `order_target_value(security, value)` | 调整到**目标金额**（0 = 清仓）|

### 典型调仓模式

```python
# 全部清仓
for stock in list(context.portfolio.positions.keys()):
    order_target_value(stock, 0)

# 等权买入
cash_per_stock = context.portfolio.cash / len(buy_list)
for stock in buy_list:
    order_value(stock, cash_per_stock)

# 维持目标仓位（不清仓再买，而是直接调到目标）
target_weight = 1.0 / len(buy_list)
total = context.portfolio.total_value
for stock in buy_list:
    order_target_value(stock, total * target_weight)
```

---

## 通用过滤器（默认都加在选股流程里）

停牌和 ST 股在聚宽回测里会产生假成交 —— 必须过滤。涨跌停可选，但新买入一般要过滤掉当日涨停的标的。

```python
def filter_paused(stock_list):
    """过滤停牌"""
    current_data = get_current_data()
    return [s for s in stock_list if not current_data[s].paused]

def filter_st(stock_list):
    """过滤 ST / *ST / 退市"""
    current_data = get_current_data()
    return [s for s in stock_list
            if not current_data[s].is_st
            and 'ST' not in current_data[s].name
            and '*' not in current_data[s].name
            and '退' not in current_data[s].name]

def filter_limitup(stock_list, context):
    """过滤涨停（已持仓的留着）"""
    current_data = get_current_data()
    return [s for s in stock_list
            if s in context.portfolio.positions.keys()
            or current_data[s].last_price < current_data[s].high_limit]

def filter_limitdown(stock_list, context):
    """过滤跌停（已持仓的留着）"""
    current_data = get_current_data()
    return [s for s in stock_list
            if s in context.portfolio.positions.keys()
            or current_data[s].last_price > current_data[s].low_limit]

def filter_new(stock_list, context, days=250):
    """过滤次新股（上市不足 N 个交易日）"""
    from datetime import timedelta
    today = context.current_dt
    return [s for s in stock_list
            if today - get_security_info(s).start_date.replace(tzinfo=None) > timedelta(days=days)]
```

---

## 行情数据

```python
# 历史 K 线（最常用）
df = get_price(
    '000001.XSHE',
    count=20,
    end_date=context.current_dt,
    frequency='daily',
    fields=['open', 'close', 'high', 'low', 'volume']
)

# 多股票一起取
df = get_price(
    ['000001.XSHE', '600000.XSHG'],
    count=20,
    end_date=context.current_dt,
    frequency='daily',
    fields=['close']
)

# 当前价（盘中）
current_data = get_current_data()
price = current_data['000001.XSHE'].last_price
high_limit = current_data['000001.XSHE'].high_limit   # 涨停价
low_limit = current_data['000001.XSHE'].low_limit     # 跌停价
is_paused = current_data['000001.XSHE'].paused

# 股票池
stocks = get_index_stocks('000300.XSHG')              # 沪深 300 成分
stocks = get_index_stocks('000905.XSHG')              # 中证 500
stocks = get_all_securities(types=['stock']).index.tolist()   # 全 A
stocks = get_all_securities(types=['etf']).index.tolist()     # 全部 ETF
```

---

## context 对象 & portfolio

```python
context.current_dt                    # 当前时间（datetime）
context.previous_date                 # 前一个交易日

context.portfolio.total_value         # 总资产
context.portfolio.cash                # 可用现金
context.portfolio.positions           # {stock: position} dict
context.portfolio.positions_value     # 持仓总市值

pos = context.portfolio.positions['000001.XSHE']
pos.total_amount                      # 持仓股数
pos.closeable_amount                  # 可平仓股数（T+1）
pos.avg_cost                          # 平均成本
pos.price                             # 当前价
```

---

## 日志

```python
log.info(f'调仓买入 {stock}')
log.warning(f'持仓 {stock} 亏损超 10%，止损')
log.error(f'出错了')
```

---

## 聚宽专属股票代码格式

- `600000.XSHG` —— 上交所主板
- `000001.XSHE` —— 深交所主板
- `300001.XSHE` —— 深交所创业板
- `688001.XSHG` —— 上交所科创板

ETF 同前缀：`510300.XSHG`（沪深 300 ETF）、`510500.XSHG`（中证 500 ETF）、`511010.XSHG`（国债 ETF）。

---

## 常见坑

1. **数据穿越**：`get_fundamentals(query)` 默认用的是**调用当天**的数据，聚宽回测里没问题（引擎控制了可见数据），但实盘要注意。
2. **T+1**：`pos.closeable_amount` ≠ `pos.total_amount`，当日买入的当日不能卖。
3. **全局变量必须挂 g**：`context` 对象不接受自定义属性。
4. **指数成分股会变**：回测时 `get_index_stocks` 取的是**当前时点**的成分股，长期回测有未来函数风险 —— 严格回测要用时间序列版的接口或交叉验证。
5. **ST 股可能有跳变**：名称变化后过滤器能识别，但回测早期名字还没改的情况要注意。
