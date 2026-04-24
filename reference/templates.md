# 聚宽策略骨架模板

4 类常见策略的完整骨架，填空式使用。

---

## 模板 1：选股轮动型（stock_rotation）

**适用场景**：按基本面/估值筛选 N 只股票，定期调仓。典型：小市值、低估值、高 ROE、红利。

```python
# coding: utf-8
"""
策略：{{策略名}}
{{策略描述}}
"""

def initialize(context):
    set_benchmark('000300.XSHG')
    set_option('use_real_price', True)
    set_order_cost(OrderCost(
        open_tax=0, close_tax=0.001,
        open_commission=0.0003, close_commission=0.0003,
        close_today_commission=0, min_commission=5
    ), type='stock')

    g.stocknum = {{持仓数量, 默认 3}}
    g.refresh_rate = {{调仓天数, 默认 5}}
    g.days = 0

    run_daily(trade, 'every_bar')


def check_stocks(context):
    q = query(
        valuation.code,
        {{返回字段}}
    ).filter(
        {{过滤条件, 如 valuation.market_cap.between(20, 30)}}
    ).order_by(
        {{排序, 如 valuation.market_cap.asc()}}
    )
    df = get_fundamentals(q)
    buylist = list(df['code'])
    buylist = filter_paused(buylist)
    buylist = filter_st(buylist)
    return buylist[:g.stocknum]


def trade(context):
    if g.days % g.refresh_rate == 0:
        for stock in list(context.portfolio.positions.keys()):
            order_target_value(stock, 0)

        stock_list = check_stocks(context)
        if stock_list:
            cash = context.portfolio.cash / len(stock_list)
            for stock in stock_list:
                if len(context.portfolio.positions) < g.stocknum:
                    order_value(stock, cash)
        g.days = 1
    else:
        g.days += 1


def filter_paused(stock_list):
    current_data = get_current_data()
    return [s for s in stock_list if not current_data[s].paused]

def filter_st(stock_list):
    current_data = get_current_data()
    return [s for s in stock_list
            if not current_data[s].is_st
            and 'ST' not in current_data[s].name
            and '*' not in current_data[s].name
            and '退' not in current_data[s].name]
```

---

## 模板 2：择时信号型（timing）

**适用场景**：单只 / 少数几只标的，用技术指标触发买卖。典型：均线金叉死叉、MACD、RSI。

```python
# coding: utf-8
"""
策略：{{策略名}}
{{策略描述, 如 5 日线上穿 20 日线买入, 下穿卖出}}
"""
import talib
import numpy as np

def initialize(context):
    set_benchmark('000300.XSHG')
    set_option('use_real_price', True)
    set_order_cost(OrderCost(
        open_tax=0, close_tax=0.001,
        open_commission=0.0003, close_commission=0.0003,
        close_today_commission=0, min_commission=5
    ), type='stock')

    g.security = '{{标的代码, 如 510300.XSHG}}'
    g.short_window = {{短均线天数, 默认 5}}
    g.long_window = {{长均线天数, 默认 20}}

    run_daily(trade, time='open')


def trade(context):
    # 取历史收盘价
    df = get_price(g.security, count=g.long_window + 5,
                    end_date=context.current_dt,
                    frequency='daily', fields=['close'])
    close = df['close'].values

    ma_short = close[-g.short_window:].mean()
    ma_long = close[-g.long_window:].mean()
    ma_short_prev = close[-g.short_window-1:-1].mean()
    ma_long_prev = close[-g.long_window-1:-1].mean()

    has_position = g.security in context.portfolio.positions

    # 金叉买入
    if ma_short_prev <= ma_long_prev and ma_short > ma_long and not has_position:
        order_target_value(g.security, context.portfolio.cash)
        log.info(f'金叉买入 {g.security}')

    # 死叉卖出
    elif ma_short_prev >= ma_long_prev and ma_short < ma_long and has_position:
        order_target_value(g.security, 0)
        log.info(f'死叉卖出 {g.security}')
```

---

## 模板 3：多因子打分型（multi_factor）

**适用场景**：用多个指标给股票打分，综合得分选 top N。典型：低 PE + 高 ROE + 低波动 综合打分。

```python
# coding: utf-8
"""
策略：{{策略名}}
{{策略描述, 如 低 PE + 高 ROE + 低负债率, 等权打分选前 5}}
"""

def initialize(context):
    set_benchmark('000300.XSHG')
    set_option('use_real_price', True)
    set_order_cost(OrderCost(
        open_tax=0, close_tax=0.001,
        open_commission=0.0003, close_commission=0.0003,
        close_today_commission=0, min_commission=5
    ), type='stock')

    g.stocknum = {{持仓数, 默认 5}}
    g.universe = '{{股票池, 如 000300.XSHG}}'

    # 每月第一个交易日调仓
    run_monthly(trade, monthday=1, time='open')


def check_stocks(context):
    pool = get_index_stocks(g.universe)

    q = query(
        valuation.code,
        valuation.pe_ratio,
        valuation.pb_ratio,
        indicator.roe,
        indicator.net_profit_margin,
    ).filter(
        valuation.code.in_(pool),
        valuation.pe_ratio > 0,
    )
    df = get_fundamentals(q).set_index('code')

    # 排序打分（每项 rank，小的得分高）
    df['score'] = 0
    df['score'] += df['pe_ratio'].rank(ascending=True)   # PE 小的好
    df['score'] += df['pb_ratio'].rank(ascending=True)   # PB 小的好
    df['score'] += df['roe'].rank(ascending=False)       # ROE 大的好
    df['score'] += df['net_profit_margin'].rank(ascending=False)

    buylist = df.sort_values('score').index.tolist()
    buylist = filter_paused(buylist)
    buylist = filter_st(buylist)
    return buylist[:g.stocknum]


def trade(context):
    buylist = check_stocks(context)

    # 卖出不在新列表的
    for stock in list(context.portfolio.positions.keys()):
        if stock not in buylist:
            order_target_value(stock, 0)

    # 买入新的
    if buylist:
        cash = context.portfolio.total_value / len(buylist)
        for stock in buylist:
            order_target_value(stock, cash)


def filter_paused(stock_list):
    current_data = get_current_data()
    return [s for s in stock_list if not current_data[s].paused]

def filter_st(stock_list):
    current_data = get_current_data()
    return [s for s in stock_list
            if not current_data[s].is_st
            and 'ST' not in current_data[s].name
            and '*' not in current_data[s].name]
```

---

## 模板 4：ETF 轮动型（etf_rotation）

**适用场景**：几只 ETF 之间切换，按动量/收益率选最强的。典型：大盘 ETF vs 小盘 ETF vs 债券 ETF 轮动。

```python
# coding: utf-8
"""
策略：{{策略名}}
{{策略描述, 如 在几只 ETF 里每月选过去 N 天涨幅最大的持有}}
"""

def initialize(context):
    set_benchmark('510300.XSHG')
    set_option('use_real_price', True)
    set_order_cost(OrderCost(
        open_tax=0, close_tax=0,
        open_commission=0.0003, close_commission=0.0003,
        close_today_commission=0, min_commission=5
    ), type='fund')

    g.etf_pool = [
        '{{ETF1, 如 510300.XSHG}}',   # 沪深 300
        '{{ETF2, 如 510500.XSHG}}',   # 中证 500
        '{{ETF3, 如 511010.XSHG}}',   # 国债 ETF
    ]
    g.momentum_days = {{动量天数, 默认 20}}
    g.stocknum = {{持仓数, 默认 1}}

    run_monthly(trade, monthday=1, time='open')


def trade(context):
    # 计算每只 ETF 过去 N 天涨幅
    momentum = {}
    for etf in g.etf_pool:
        df = get_price(etf, count=g.momentum_days + 1,
                        end_date=context.current_dt,
                        frequency='daily', fields=['close'])
        momentum[etf] = df['close'].iloc[-1] / df['close'].iloc[0] - 1

    # 排序选前 N
    ranked = sorted(momentum.items(), key=lambda x: x[1], reverse=True)
    buylist = [etf for etf, _ in ranked[:g.stocknum] if momentum[etf] > 0]

    # 卖出不在列表的
    for stock in list(context.portfolio.positions.keys()):
        if stock not in buylist:
            order_target_value(stock, 0)

    # 买入新的
    if buylist:
        cash = context.portfolio.total_value / len(buylist)
        for etf in buylist:
            order_target_value(etf, cash)
```

---

## 🎯 填充规则

遇到模板里的 `{{xxx}}` 占位符：

1. **能从用户描述里直接提取的** → 直接填
2. **用户没说的** → 填默认值
3. **需要推断的**（如"小市值"意味着取市值最小的） → 按映射表来

**所有模板默认加 `filter_paused` 和 `filter_st`**，这是纪律，不能省。
