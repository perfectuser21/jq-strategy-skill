# coding: utf-8
"""
策略：小市值选股
选市值 20-30 亿的股票，买入市值最小的 3 只，每 5 个交易日调仓
推荐回测区间：2020-01-01 至 2024-01-01
推荐初始资金：100 万
"""

def initialize(context):
    set_benchmark('000300.XSHG')
    set_option('use_real_price', True)
    set_option('order_volume_ratio', 1)
    set_order_cost(OrderCost(
        open_tax=0, close_tax=0.001,
        open_commission=0.0003, close_commission=0.0003,
        close_today_commission=0, min_commission=5
    ), type='stock')

    g.stocknum = 3
    g.refresh_rate = 5
    g.days = 0

    run_daily(trade, 'every_bar')


def check_stocks(context):
    q = query(
        valuation.code,
        valuation.market_cap
    ).filter(
        valuation.market_cap.between(20, 30)
    ).order_by(
        valuation.market_cap.asc()
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
            cash_per_stock = context.portfolio.cash / len(stock_list)
            for stock in stock_list:
                if len(context.portfolio.positions) < g.stocknum:
                    order_value(stock, cash_per_stock)
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
