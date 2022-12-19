# -*- coding: utf-8 -*-
"""
author: zengbin93
email: zeng_bin8888@163.com
create_dt: 2022/10/31 22:27
describe: 专用于信号检查的策略
"""
import talib as ta
import numpy as np
import pandas as pd
from collections import OrderedDict
from typing import List
from loguru import logger
from czsc import CZSC, signals, RawBar, Direction
from czsc.data import TsDataCache, get_symbols
from czsc.utils import get_sub_elements, single_linear, fast_slow_cross
from czsc.objects import Freq, Operate, Signal, Factor, Event, BI
from czsc.traders import CzscAdvancedTrader


# 定义信号函数
# ----------------------------------------------------------------------------------------------------------------------
def macd_bs2_v2(cat: CzscAdvancedTrader, freq: str):
    """MACD金叉死叉判断第二买卖点

    原理：最近一次交叉为死叉，DEA大于0，且前面三次死叉都在零轴下方，那么二买即将出现；二卖反之。

    完全分类：
        Signal('15分钟_MACD_BS2V2_二卖_任意_任意_0'),
        Signal('15分钟_MACD_BS2V2_二买_任意_任意_0')
    :return:
    """
    s = OrderedDict()
    cache_key = f"{freq}MACD"
    cache = cat.cache[cache_key]
    assert cache and cache['update_dt'] == cat.end_dt
    cross = cache['cross']
    macd = cache['macd']
    up = [x for x in cross if x['类型'] == "金叉"]
    dn = [x for x in cross if x['类型'] == "死叉"]

    v1 = "其他"

    b2_con1 = len(cross) > 3 and cross[-1]['类型'] == '死叉' and cross[-1]['慢线'] > 0
    b2_con2 = len(dn) > 3 and dn[-3]['慢线'] < 0 and dn[-2]['慢线'] < 0 and dn[-3]['慢线'] < 0
    b2_con3 = len(macd) > 10 and macd[-1] > macd[-2]
    if b2_con1 and b2_con2 and b2_con3:
        v1 = "二买"

    s2_con1 = len(cross) > 3 and cross[-1]['类型'] == '金叉' and cross[-1]['慢线'] < 0
    s2_con2 = len(up) > 3 and up[-3]['慢线'] > 0 and up[-2]['慢线'] > 0 and up[-3]['慢线'] > 0
    s2_con3 = len(macd) > 10 and macd[-1] < macd[-2]
    if s2_con1 and s2_con2 and s2_con3:
        v1 = "二卖"

    signal = Signal(k1=freq, k2="MACD", k3="BS2V2", v1=v1)
    s[signal.key] = signal.value
    return s


def tas_macd_first_bs_V221216(c: CZSC, di: int = 1):
    """MACD金叉死叉判断第一买卖点

    **信号逻辑：**

    1. 最近一次交叉为死叉，且前面两次死叉都在零轴下方，价格创新低，那么一买即将出现；一卖反之。
    2. 或 最近一次交叉为金叉，且前面三次死叉都在零轴下方，价格创新低，那么一买即将出现；一卖反之。

    **信号列表：**

    - Signal('15分钟_D1MACD_BS1A_一卖_金叉_任意_0')
    - Signal('15分钟_D1MACD_BS1A_一卖_死叉_任意_0')
    - Signal('15分钟_D1MACD_BS1A_一买_死叉_任意_0')
    - Signal('15分钟_D1MACD_BS1A_一买_金叉_任意_0')

    :param c: CZSC对象
    :param di: 倒数第i根K线
    :return: 信号识别结果
    """
    k1, k2, k3 = f"{c.freq.value}_D{di}MACD_BS1A".split('_')
    bars = get_sub_elements(c.bars_raw, di=di, n=350)[50:]

    v1 = "其他"
    v2 = "任意"
    if len(bars) >= 100:
        dif = [x.cache['MACD']['dif'] for x in bars]
        dea = [x.cache['MACD']['dea'] for x in bars]
        macd = [x.cache['MACD']['macd'] for x in bars]
        n_bars = bars[-10:]
        m_bars = bars[-100: -10]
        high_n = max([x.high for x in n_bars])
        low_n = min([x.low for x in n_bars])
        high_m = max([x.high for x in m_bars])
        low_m = min([x.low for x in m_bars])

        cross = fast_slow_cross(dif, dea)
        up = [x for x in cross if x['类型'] == "金叉" and x['距离'] > 5]
        dn = [x for x in cross if x['类型'] == "死叉" and x['距离'] > 5]

        b1_con1a = len(cross) > 3 and cross[-1]['类型'] == '死叉' and cross[-1]['慢线'] < 0
        b1_con1b = len(cross) > 3 and cross[-1]['类型'] == '金叉' and dn[-1]['慢线'] < 0
        b1_con2 = len(dn) > 3 and dn[-2]['慢线'] < 0 and dn[-3]['慢线'] < 0
        b1_con3 = len(macd) > 10 and macd[-1] > macd[-2]
        if low_n < low_m and (b1_con1a or b1_con1b) and b1_con2 and b1_con3:
            v1 = "一买"

        s1_con1a = len(cross) > 3 and cross[-1]['类型'] == '金叉' and cross[-1]['慢线'] > 0
        s1_con1b = len(cross) > 3 and cross[-1]['类型'] == '死叉' and up[-1]['慢线'] > 0
        s1_con2 = len(dn) > 3 and up[-2]['慢线'] > 0 and up[-3]['慢线'] > 0
        s1_con3 = len(macd) > 10 and macd[-1] < macd[-2]
        if high_n > high_m and (s1_con1a or s1_con1b) and s1_con2 and s1_con3:
            v1 = "一卖"

        v2 = cross[-1]['类型']

    s = OrderedDict()
    signal = Signal(k1=k1, k2=k2, k3=k3, v1=v1, v2=v2)
    s[signal.key] = signal.value
    return s


# 定义择时交易策略，策略函数名称必须是 trader_strategy
# ----------------------------------------------------------------------------------------------------------------------
def trader_strategy(symbol):
    """择时策略"""

    def get_signals(cat: CzscAdvancedTrader) -> OrderedDict:
        s = OrderedDict({"symbol": cat.symbol, "dt": cat.end_dt, "close": cat.latest_price})
        signals.update_macd_cache(cat.kas['15分钟'])

        s.update(tas_macd_first_bs_V221216(cat.kas['15分钟'], di=1))
        return s

    tactic = {
        "base_freq": '15分钟',
        "freqs": ['60分钟', '日线'],
        "get_signals": get_signals,
    }
    return tactic


# 定义命令行接口【信号检查】的特定参数
# ----------------------------------------------------------------------------------------------------------------------

# 初始化 Tushare 数据缓存
dc = TsDataCache(r"D:\ts_data")

# 信号检查参数设置【可选】
# check_params = {
#     "symbol": "000001.SZ#E",    # 交易品种，格式为 {ts_code}#{asset}
#     "sdt": "20180101",          # 开始时间
#     "edt": "20220101",          # 结束时间
# }


check_params = {
    "symbol": "300001.SZ#E",  # 交易品种，格式为 {ts_code}#{asset}
    "sdt": "20150101",  # 开始时间
    "edt": "20220101",  # 结束时间
}