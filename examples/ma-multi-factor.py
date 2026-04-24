# coding: utf-8
"""
策略：均线金叉择时 + 多因子选股轮动

逻辑：
  1. 每日用沪深 300 做大盘择时：5 日线上穿 20 日线开仓，下穿清仓
  2. 持仓期间，每 5 个交易日按"低 PE + 高 ROE + 小市值 + 高动量"四因子打分选前 5 只
  3. 单股浮亏超 5% 自动止损清该股

推荐回测区间：2019-01-01 ~ 2024-12-31
推荐初始资金：50 万
基准：沪深 300 (000300.XSHG)

使用：登录 joinquant.com → 策略 → 新建 → 粘贴本文件 → 设日期/资金 → 跑回测
"""


# ========== 初始化 ==========

def initialize(context):
    set_benchmark('000300.XSHG')
    set_option('use_real_price', True)
    set_option('order_volume_ratio', 1)
    set_order_cost(OrderCost(
        open_tax=0, close_tax=0.001,
        open_commission=0.0003, close_commission=0.0003,
        close_today_commission=0, min_commission=5
    ), type='stock')
    set_slippage(FixedSlippage(0.002))

    # 全局参数必须挂 g；context 不接受自定义属性
    g.timing_index = '000300.XSHG'
    g.stocks_num = 5
    g.refresh_rate = 5      # 每 N 个交易日调仓
    g.stop_loss = -0.05     # 单股止损线
    g.ma_short = 5
    g.ma_long = 20
    g.days = 0
    g.in_trade = False

    run_daily(trade, time='open')


# ========== 择时信号 ==========

def get_timing_signal(context):
    """返回 'buy' / 'sell' / 'hold'"""
    df = get_price(
        g.timing_index,
        end_date=context.previous_date,
        count=g.ma_long + 2,
        frequency='daily',
        fields=['close']
    )
    ma_short_today = df['close'].iloc[-g.ma_short:].mean()
    ma_long_today = df['close'].iloc[-g.ma_long:].mean()
    ma_short_prev = df['close'].iloc[-g.ma_short - 1:-1].mean()
    ma_long_prev = df['close'].iloc[-g.ma_long - 1:-1].mean()

    if ma_short_prev <= ma_long_prev and ma_short_today > ma_long_today:
        return 'buy'
    if ma_short_prev >= ma_long_prev and ma_short_today < ma_long_today:
        return 'sell'
    return 'hold'


# ========== 多因子选股 ==========

def select_stocks(context):
    q = query(
        valuation.code,
        valuation.market_cap,
        valuation.pe_ratio,
        indicator.roe,
    ).filter(
        valuation.pe_ratio > 0,
        valuation.pe_ratio < 40,
        indicator.roe > 5,
        valuation.market_cap.between(20, 200),
    )
    df = get_fundamentals(q)
    if df.empty:
        return []

    # 过滤停牌 / ST
    codes = filter_paused(df['code'].tolist())
    codes = filter_st(codes)
    df = df[df['code'].isin(codes)].reset_index(drop=True)
    if df.empty:
        return []

    # 20 日动量：批量取价比逐只 for 循环快几十倍
    price_df = get_price(
        df['code'].tolist(),
        end_date=context.previous_date,
        count=21,
        frequency='daily',
        fields=['close'],
        panel=False,
    )
    momentum_map = {}
    for code, grp in price_df.groupby('code'):
        closes = grp['close'].dropna()
        if len(closes) >= 21:
            momentum_map[code] = closes.iloc[-1] / closes.iloc[0] - 1
        else:
            momentum_map[code] = 0.0
    df['momentum'] = df['code'].map(momentum_map).fillna(0.0)

    # 四因子等权 rank 打分，分数越小越好
    df['score'] = (
        df['pe_ratio'].rank(ascending=True)
        + df['roe'].rank(ascending=False)
        + df['market_cap'].rank(ascending=True)
        + df['momentum'].rank(ascending=False)
    )
    return df.sort_values('score').head(g.stocks_num)['code'].tolist()


# ========== 风控：单股止损 ==========

def check_stop_loss(context):
    for stock, pos in list(context.portfolio.positions.items()):
        if pos.total_amount == 0 or pos.avg_cost <= 0:
            continue
        ret = (pos.price - pos.avg_cost) / pos.avg_cost
        if ret < g.stop_loss:
            order_target_value(stock, 0)
            log.info(f'止损清仓 {stock}, 浮亏 {ret:.2%}')


# ========== 主调仓 ==========

def trade(context):
    check_stop_loss(context)
    g.days += 1

    signal = get_timing_signal(context)

    # 死叉：强制清仓
    if signal == 'sell':
        for stock in list(context.portfolio.positions.keys()):
            order_target_value(stock, 0)
        g.in_trade = False
        log.info('死叉清仓')
        return

    # 金叉：立刻建仓
    if signal == 'buy' and not g.in_trade:
        buylist = select_stocks(context)
        if buylist:
            rebalance(context, buylist)
            g.in_trade = True
            log.info(f'金叉建仓 {buylist}')
        return

    # 持仓期间按频率换股
    if g.in_trade and g.days % g.refresh_rate == 0:
        buylist = select_stocks(context)
        if buylist:
            rebalance(context, buylist)


def rebalance(context, buylist):
    """按等权目标权重调仓：卖出不在列表的，目标股拉到等权"""
    target_weight = 1.0 / len(buylist)
    for stock in list(context.portfolio.positions.keys()):
        if stock not in buylist:
            order_target_percent(stock, 0)
    for stock in buylist:
        order_target_percent(stock, target_weight)


# ========== 通用过滤器 ==========

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
