# coding: utf-8
"""
策略：均线金叉死叉（单标的择时）
5 日均线上穿 20 日均线买入 510300（沪深 300 ETF），下穿卖出。
推荐回测区间：2018-01-01 至 2024-01-01
推荐初始资金：10 万
"""

def initialize(context):
    set_benchmark('510300.XSHG')
    set_option('use_real_price', True)
    set_order_cost(OrderCost(
        open_tax=0, close_tax=0,
        open_commission=0.0003, close_commission=0.0003,
        close_today_commission=0, min_commission=5
    ), type='fund')

    g.security = '510300.XSHG'
    g.short_window = 5
    g.long_window = 20

    run_daily(trade, time='open')


def trade(context):
    df = get_price(
        g.security,
        count=g.long_window + 5,
        end_date=context.current_dt,
        frequency='daily',
        fields=['close']
    )
    close = df['close'].values

    ma_short_today = close[-g.short_window:].mean()
    ma_long_today = close[-g.long_window:].mean()
    ma_short_prev = close[-g.short_window - 1:-1].mean()
    ma_long_prev = close[-g.long_window - 1:-1].mean()

    has_position = g.security in context.portfolio.positions \
        and context.portfolio.positions[g.security].total_amount > 0

    if ma_short_prev <= ma_long_prev and ma_short_today > ma_long_today and not has_position:
        order_target_value(g.security, context.portfolio.total_value)
        log.info(f'金叉买入 {g.security}')

    elif ma_short_prev >= ma_long_prev and ma_short_today < ma_long_today and has_position:
        order_target_value(g.security, 0)
        log.info(f'死叉卖出 {g.security}')
