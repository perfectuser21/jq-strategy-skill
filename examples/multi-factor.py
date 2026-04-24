# coding: utf-8
"""
策略：多因子打分选股
在沪深 300 里用"低 PE + 低 PB + 高 ROE + 高净利率"四因子等权打分，每月初调仓持有前 10 只。
推荐回测区间：2019-01-01 至 2024-01-01
推荐初始资金：100 万
"""

def initialize(context):
    set_benchmark('000300.XSHG')
    set_option('use_real_price', True)
    set_order_cost(OrderCost(
        open_tax=0, close_tax=0.001,
        open_commission=0.0003, close_commission=0.0003,
        close_today_commission=0, min_commission=5
    ), type='stock')

    g.stocknum = 10
    g.universe_index = '000300.XSHG'

    run_monthly(trade, monthday=1, time='open')


def check_stocks(context):
    pool = get_index_stocks(g.universe_index)

    q = query(
        valuation.code,
        valuation.pe_ratio,
        valuation.pb_ratio,
        indicator.roe,
        indicator.net_profit_margin,
    ).filter(
        valuation.code.in_(pool),
        valuation.pe_ratio > 0,
        valuation.pb_ratio > 0,
    )
    df = get_fundamentals(q).set_index('code')
    if df.empty:
        return []

    df['score'] = 0.0
    df['score'] += df['pe_ratio'].rank(ascending=True)
    df['score'] += df['pb_ratio'].rank(ascending=True)
    df['score'] += df['roe'].rank(ascending=False)
    df['score'] += df['net_profit_margin'].rank(ascending=False)

    buylist = df.sort_values('score').index.tolist()
    buylist = filter_paused(buylist)
    buylist = filter_st(buylist)
    return buylist[:g.stocknum]


def trade(context):
    buylist = check_stocks(context)
    if not buylist:
        return

    for stock in list(context.portfolio.positions.keys()):
        if stock not in buylist:
            order_target_value(stock, 0)

    target_value = context.portfolio.total_value / len(buylist)
    for stock in buylist:
        order_target_value(stock, target_value)


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
