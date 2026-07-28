"""Orchestrate raw series -> the 16-indicator catalogue + thresholds + bars.

The derivation order and threshold logic are migrated verbatim from
``prototype-indicator-timeline/build_data.py::main`` so published numbers match
the validated prototype. The output is an intermediate, unserialised
representation (dict[date, float] series); ``packet.py`` shapes it for the
dashboard and ``run_daily`` writes it.
"""

from __future__ import annotations

import math
from collections.abc import Mapping
from dataclasses import dataclass, field
from datetime import date

from . import derive


# --- Dashboard six-category taxonomy (English ids, fixed order) ------------
CATEGORY_ORDER = ("valuation", "supply", "capital", "holders", "miners", "anchors")

CATEGORY_NAMES = {
    "valuation": "市场估值与成本基础",
    "supply": "未实现盈亏与供应盈亏结构",
    "capital": "已实现盈亏与链上资本流",
    "holders": "持有者行为与投降",
    "miners": "矿工经济压力与矿工成本",
    "anchors": "长期成本锚与持币信念",
}

# metric_id -> (category_id, is_core). Exactly the 16 the dashboard shows.
INDICATOR_CATALOG: dict[str, tuple[str, bool]] = {
    "mvrv": ("valuation", True),
    "aviv": ("valuation", True),
    "sth_mvrv_price": ("valuation", False),
    "psip": ("supply", False),
    "sipl": ("supply", False),
    "relative_unrealized_profit": ("supply", False),
    "relative_unrealized_loss_zscore_4y": ("supply", False),
    "realized_cap_relative_npc_30d": ("capital", False),
    "asopr": ("capital", False),
    "hodler_npc_30d": ("holders", True),
    "spent_value_ge155d_share": ("holders", True),
    "seller_exhaustion": ("holders", False),
    "puell_multiple": ("miners", True),
    "thermocap_multiple_zscore": ("miners", False),
    "cvdd_proximity": ("anchors", False),
    "reserve_risk_zscore": ("anchors", False),
}


@dataclass
class LineSpec:
    id: str
    label: str
    axis: str  # "indicator" | "price"
    series: dict[date, float]
    mode: str | None = None  # "net" | "split" | None


@dataclass
class IndicatorSpec:
    id: str
    label: str
    category: str
    core: bool
    unit: str
    description: str
    formula: str
    source: str
    method: str
    caveat: str
    primary: dict[date, float]
    references: list[dict]  # [{"value": float, "label": str}]
    direction: str  # "below" | "above"
    primary_line_label: str | None = None
    primary_line_mode: str | None = None
    extra_lines: list[LineSpec] = field(default_factory=list)
    check: dict | None = None


@dataclass
class BarSpec:
    id: str
    label: str
    unit: str
    description: str
    source: str
    method: str
    caveat: str
    series: dict[date, float]  # only the days with a meaningful value


@dataclass
class ComputedData:
    indicators: list[IndicatorSpec]
    price: dict[date, float]
    bars: dict[str, BarSpec]
    data_date: date
    source_metadata: dict
    thresholds_log: list[str]


def _reference(value: float, label: str) -> dict:
    return {"value": float(f"{value:.10g}"), "label": label}


def compute_indicators(
    raw: dict[str, dict[date, float]],
    obm_total: dict[date, float],
    obm_long: dict[date, float],
    source_metadata: Mapping[str, object] | None = None,
) -> ComputedData:
    """Recompute every dashboard indicator + threshold from raw base series."""

    log: list[str] = []

    mvrv = derive.aligned_ratio(raw["market_cap"], raw["realized_cap"])
    aviv = derive.derive_aviv(raw)
    puell = derive.derive_puell(raw)
    rc_30d = derive.lag_change(raw["realized_cap"], 30, True)
    sth_mvrv = derive.derive_sth_mvrv(raw)
    hodler_npc = derive.lag_change(raw["hodled_or_lost_supply"], 30, False)
    hodler_npc_share = derive.aligned_ratio(hodler_npc, raw["supply"])
    # HODLer NPC has different meanings in bull and bear markets. Retain only
    # MVRV<1 days so the displayed line stays in the market-wide loss regime.
    hodler_npc_undervalued = {
        day: hodler_npc_share[day]
        for day in hodler_npc_share
        if day in mvrv and mvrv[day] < 1.0
    }
    hodler_deep_10 = derive.past_cycle_quantile(hodler_npc_undervalued, 0.10)
    hodler_deep_5 = derive.past_cycle_quantile(hodler_npc_undervalued, 0.05)
    long_spent_share = derive.aligned_ratio(obm_long, obm_total)
    # Old-coin spending is dual-natured (tops=distribution, bottoms=capitulation).
    # Gate to MVRV<1 so spikes mark capitulation. Confirmation line, not a trigger.
    spent_share_undervalued = {
        day: long_spent_share[day]
        for day in long_spent_share
        if day in mvrv and mvrv[day] < 1.0
    }
    spent_share_loss_q90 = derive.past_cycle_quantile(spent_share_undervalued, 0.90)
    psip = derive.aligned_ratio(raw["supply_in_profit"], raw["supply"])
    supply_loss_share = derive.aligned_ratio(raw["supply_in_loss"], raw["supply"])
    sipl_gap = derive.aligned_difference(psip, supply_loss_share)
    rup = derive.aligned_ratio(raw["unrealized_profit"], raw["market_cap"])
    rup_zscore = derive.rolling_zscore(rup)
    # RUL has no published Bitview stock series; derive via NUPL = RUP - RUL with
    # NUPL = 1 - 1/MVRV. Clipped at 0 to absorb rounding noise.
    nupl = {day: 1.0 - 1.0 / value for day, value in mvrv.items() if value}
    rul = {day: max(0.0, rup[day] - nupl[day]) for day in rup.keys() & nupl.keys()}
    rul_zscore = derive.rolling_zscore(rul)
    cvdd, cvdd_proximity = derive.derive_cvdd(raw)
    sth_net = derive.normalised_net(raw["sth_realized_profit_sum_24h"], raw["sth_realized_loss_sum_24h"], raw["market_cap"])
    net_realized = derive.normalised_net(raw["realized_profit_sum_24h"], raw["realized_loss_sum_24h"], raw["market_cap"])
    seller_exhaustion = derive.derive_seller_exhaustion(raw, psip)
    thermocap_multiple = derive.aligned_ratio(raw["market_cap"], raw["subsidy_cumulative_usd"])

    # --- No-lookahead reference thresholds ---
    honest_targets = {
        "sth_net_q05": (sth_net, 0.05),
        "net_realized_q05": (net_realized, 0.05),
        "reserve_risk_q10": (raw["reserve_risk"], 0.1),
        "seller_exhaustion_q10": (seller_exhaustion, 0.1),
        "thermocap_q10": (thermocap_multiple, 0.1),
    }
    honest: dict[str, float] = {}
    log.append("threshold migration (full-sample -> past-cycle, lookahead removed):")
    for key, (series, probability) in honest_targets.items():
        old_value = derive.quantile(series, probability)
        honest[key] = derive.past_cycle_quantile(series, probability)
        log.append(f"  {key:<26} {old_value:>14.6g} -> {honest[key]:>14.6g}")

    # --- STH-MVRV tactical-price levels (three statistical methods) ---
    sth_rp = derive.aligned_ratio(raw["sth_realized_cap"], raw["sth_supply"])
    sth_stats = derive.past_cycle_stats(sth_mvrv)
    _sigma = sth_stats["pstdev"]
    _mad_sigma = 1.4826 * sth_stats["mad"]
    sth_levels = {
        "q5": derive.past_cycle_quantile(sth_mvrv, 0.05),
        "mean_1_5": sth_stats["mean"] - 1.5 * _sigma,
        "median_1_5": sth_stats["median"] - 1.5 * _mad_sigma,
    }
    sth_ladders = {key: derive.ladder(level, sth_rp) for key, level in sth_levels.items()}
    log.append("STH-MVRV tactical-price levels (window [2018, 2022-bottom], no lookahead):")
    for _key in ("q5", "mean_1_5", "median_1_5"):
        log.append(f"  {_key:<12} MVRV={sth_levels[_key]:.5f}")

    # --- Reserve Risk log z-score (cross-cycle normalization) ---
    rr = raw["reserve_risk"]
    log_rr = {day: math.log(value) for day, value in rr.items() if value > 0}
    rr_zscore = derive.rolling_zscore(log_rr)
    rr_z_q10 = derive.past_cycle_quantile(rr_zscore, 0.10)
    rr_z_q05 = derive.past_cycle_quantile(rr_zscore, 0.05)
    _latest_rr_z = rr_zscore[max(rr_zscore)]
    log.append(f"Reserve Risk log z-score: current z={_latest_rr_z:.3f} q10={rr_z_q10:.3f} q05={rr_z_q05:.3f}")

    # --- Thermocap Multiple log z-score (relative-cycle view) ---
    log_tc = {day: math.log(value) for day, value in thermocap_multiple.items() if value > 0}
    tc_zscore = derive.rolling_zscore(log_tc)
    tc_z_q10 = derive.past_cycle_quantile(tc_zscore, 0.10)
    tc_z_q05 = derive.past_cycle_quantile(tc_zscore, 0.05)
    _latest_tc_z = tc_zscore[max(tc_zscore)]
    log.append(f"Thermocap log z-score: current z={_latest_tc_z:.3f} q10={tc_z_q10:.3f} q05={tc_z_q05:.3f}")

    # --- aSOPR trailing-SMA secondary lines (causal) ---
    asopr_3d = derive.rolling_mean(raw["asopr_24h"], 3)
    asopr_7d = derive.rolling_mean(raw["asopr_24h"], 7)

    def spec(metric_id: str, **kwargs) -> IndicatorSpec:
        category, core = INDICATOR_CATALOG[metric_id]
        return IndicatorSpec(id=metric_id, category=category, core=core, **kwargs)

    indicators = [
        spec(
            "mvrv", label="MVRV", unit="ratio",
            description="市场价值相对全市场已实现成本基础。",
            formula="Market Cap / Realized Cap",
            source="BRK / Bitview 基础日线", method="自行计算",
            caveat="", primary=mvrv,
            references=[_reference(1.0, "成本平衡线"), _reference(0.8, "深度低估观察线")],
            direction="below", check=derive.compare(mvrv, raw["mvrv"]),
        ),
        spec(
            "aviv", label="AVIV", unit="ratio",
            description="活跃价值相对投资者成本基础。",
            formula="(Market Cap × Liveliness) / (Realized Cap - Thermocap)",
            source="BRK / Bitview 四条基础日线", method="自行计算（ARK × Glassnode 原始定义）",
            caveat="Bitview 成品 aviv_ratio 使用不同分子，本原型不拿它作同公式误差检查。",
            primary=aviv,
            references=[_reference(0.65, "低估观察线"), _reference(0.55, "深度低估参考")],
            direction="below",
        ),
        spec(
            "sth_mvrv_price", label="STH-MVRV 战术价位（三法合并）", unit="ratio",
            description="STH-MVRV 三套统计抄底档合并：5%分位 / 1.5σ / 1.5·MAD；价位阶梯 = 档位 × STH-RP（Price = STH-MVRV × STH-RP）。",
            formula="Q5 / (mean−1.5σ) / (median−1.5·1.4826·MAD)，各 × STH-RP；阈值在无前视窗口 [2018,2022底] 上算",
            source="BRK / Bitview 基础日线", method="自行计算（无前视）",
            caveat="三法对照：5%分位最浅、1.5σ居中偏浅、1.5·MAD最深。references[0]=5%分位为触发线。阈值无前视。",
            primary=sth_mvrv,
            references=[
                _reference(sth_levels["q5"], "5%分位（无前视）"),
                _reference(sth_levels["mean_1_5"], "1.5σ（无前视）"),
                _reference(sth_levels["median_1_5"], "1.5·MAD（无前视）"),
            ],
            direction="below",
            extra_lines=[
                LineSpec("q5_price", "5%分位 × STH-RP", "price", sth_ladders["q5"]),
                LineSpec("mean_1_5_price", "1.5σ × STH-RP", "price", sth_ladders["mean_1_5"]),
                LineSpec("median_1_5_price", "1.5·MAD × STH-RP", "price", sth_ladders["median_1_5"]),
            ],
        ),
        spec(
            "psip", label="Percent Supply in Profit", unit="percent",
            description="当前价格高于创建时价格的供应占比。",
            formula="Supply in Profit / Total Supply",
            source="BRK / Bitview 基础日线", method="自行计算",
            caveat="", primary=psip,
            references=[_reference(0.5, "盈亏供应平衡"), _reference(0.4, "广泛浮亏参考")],
            direction="below", check=derive.compare(psip, raw["supply_in_profit_share_ratio"]),
        ),
        spec(
            "sipl", label="Supply in Profit / Loss", unit="percent",
            description="盈利供应、亏损供应，以及盈利占比减亏损占比的差值。",
            formula="Profit Share = Supply in Profit / Supply; Loss Share = Supply in Loss / Supply; Gap = Profit Share - Loss Share",
            source="BRK / Bitview 基础日线", method="自行计算",
            caveat="与 PSIP 是同一底层供应盈亏事实的三线表达；差值大于零表示盈利供应占比更高。",
            primary=psip,
            references=[_reference(0.5, "盈利/亏损占比平衡")],
            direction="below",
            extra_lines=[
                LineSpec("loss_share", "Supply in Loss", "indicator", supply_loss_share),
                LineSpec("profit_loss_gap", "盈利% − 亏损%", "indicator", sipl_gap),
            ],
        ),
        spec(
            "relative_unrealized_profit", label="Relative Unrealized Profit", unit="percent",
            description="全网未实现盈利占市场价值的比例。",
            formula="Unrealized Profit / Market Cap",
            source="BRK / Bitview 基础日线", method="自行计算",
            caveat="", primary=rup,
            references=[_reference(0.4, "低未实现盈利参考"), _reference(0.3, "深低值观察线")],
            direction="below", check=derive.compare(rup, raw["unrealized_profit_to_mcap_ratio"]),
        ),
        spec(
            "relative_unrealized_loss_zscore_4y", label="RUL 4年滚动 z-score", unit="zscore",
            description="Relative Unrealized Loss 相对过去1460日均值的标准差位置（底部 spike → 正向 z）。",
            formula="(RUL - rolling mean 1460d) / rolling population std 1460d",
            source="由本原型基于 RUL（推导值）计算", method="自行计算",
            caveat="RUL 强右偏（+1.67），单σ偏松；历史大底 z≈+2.8~+2.9、COVID≈+2.0。明确版本化的4年滚动总体标准差。",
            primary=rul_zscore,
            references=[_reference(2.0, "高于均值2σ（投降区）"), _reference(2.5, "高于均值2.5σ（深度投降）")],
            direction="above",
        ),
        spec(
            "realized_cap_relative_npc_30d", label="Realized Cap Relative NPC · 30d", unit="percent",
            description="已实现市值相对30日前的变化。",
            formula="RC(t) / RC(t-30d) - 1",
            source="BRK / Bitview Realized Cap", method="自行计算",
            caveat="", primary=rc_30d,
            references=[_reference(0.0, "资本扩张/收缩分界")],
            direction="above", check=derive.compare(rc_30d, raw["realized_cap_delta_1m_rate_ratio"]),
        ),
        spec(
            "asopr", label="aSOPR", unit="ratio",
            description="排除寿命不足一小时输出后的已花费盈亏倍数。",
            formula="Adjusted spent value at spend / value at creation",
            source="BRK / Bitview", method="公开成品日线",
            caveat="完整复算需要逐UTXO花费成本，本原型直接使用透明开源计算链的成品日线。原始日线为投降尖峰信号（触发线挂原始）；3d/7d为滞后均值（rolling_mean，无前视），仅作制度/趋势可读性辅助——会削平并滞后尖峰，不作触发。",
            primary=raw["asopr_24h"],
            references=[_reference(1.0, "已实现盈亏平衡")],
            direction="below",
            extra_lines=[
                LineSpec("sma_3d", "3日滞后均值（趋势辅助）", "indicator", asopr_3d),
                LineSpec("sma_7d", "7日滞后均值（趋势辅助）", "indicator", asopr_7d),
            ],
        ),
        spec(
            "hodler_npc_30d", label="HODLer 投降卖出尖峰 · 占供应%", unit="percent",
            description="只显示全网低估期（MVRV<1）的 HODLer NPC：负值是长期不动供应减少，正值是低估期积累。",
            formula="[HODLedOrLostSupply(t) − HODLedOrLostSupply(t−30d)] / Supply; retain only MVRV<1",
            source="BRK / Bitview 基础日线", method="自行计算（% of supply）",
            caveat="只保留低估期，不显示牛市派发；负值表示卖出、正值表示积累。深卖阈值=过去周期[2018,2022底]该低估期线的5/10%分位（无前视）。原BTC口径=Glassnode LTH-NetPositionChange。",
            primary=hodler_npc_undervalued,
            primary_line_label="低估期 HODLer NPC（MVRV<1）",
            references=[
                _reference(hodler_deep_10, "深卖阈值·10%分位（无前视）"),
                _reference(hodler_deep_5, "深卖阈值·5%分位（无前视）"),
                _reference(0.0, "积累/卖出分界"),
            ],
            direction="below",
        ),
        spec(
            "spent_value_ge155d_share", label=">=155d 花费价值占比", unit="percent",
            description="只显示全网低估期（MVRV<1）的币龄至少155天花费价值占比，用作老币投降的确认线。",
            formula="Spent Value >=155d / Total Spent Value; retain only MVRV<1",
            source="Open Bitcoin Metrics v0.1.0", method="自行计算",
            caveat="公开数据不能逐笔判断老币是否以亏损卖出；MVRV<1 仅代表全网处于整体亏损状态。故本线不显示顶部的获利派发，只作为低估期投降确认，不作独立触发。",
            primary=spent_share_undervalued,
            primary_line_label="低估期老币花费（MVRV<1）",
            references=[_reference(spent_share_loss_q90, "过去低估期90%分位（无前视）")],
            direction="above",
        ),
        spec(
            "seller_exhaustion", label="Seller Exhaustion Constant", unit="small",
            description="低盈利供应与低波动共同出现的卖方耗竭状态。",
            formula="PSIP × BRK 30d Price Volatility",
            source="BRK / Bitview 基础日线", method="自行计算",
            caveat="", primary=seller_exhaustion,
            references=[_reference(honest["seller_exhaustion_q10"], "过去周期10%分位（无前视）")],
            direction="below", check=derive.compare(seller_exhaustion, raw["seller_exhaustion"]),
        ),
        spec(
            "puell_multiple", label="Puell Multiple", unit="ratio",
            description="每日矿工补贴美元收入相对其一年均值。",
            formula="Subsidy USD / 365d Average Subsidy USD（BRK 按块计算后下采样）",
            source="BRK / Bitview", method="公开成品日线；另做日度复算核对",
            caveat="本原型按日线复算与BRK按块计算后下采样存在可见口径差，因此主图采用BRK成品值，误差卡保留差异。",
            primary=raw["puell_multiple"],
            references=[_reference(1.0, "低收入区上界"), _reference(0.5, "历史深压参考")],
            direction="below", check=derive.compare(puell, raw["puell_multiple"]),
        ),
        spec(
            "thermocap_multiple_zscore", label="Thermocap Multiple · 周期归一化 z", unit="zscore",
            description="Thermocap Multiple 经 log + 4年滚动 z-score，消除底部缓升、提供相对自身周期的过热/过冷视角。",
            formula="z[ log(Thermocap Multiple), trailing 1460d ]；阈值 = z 的过去周期分位（无前视）",
            source="BRK / Bitview", method="自行计算（无前视）",
            caveat="Thermocap = MarketCap / 累积矿工补贴。结构性下移轻微：顶部周期振荡、底部反因减半放缓分母而缓升。z-score 在此消除底部缓升并提供相对自身4年周期的过热/过冷视角（绝对阈值底部5-7/顶部50-74仍有效）。",
            primary=tc_zscore,
            references=[
                _reference(tc_z_q10, "z·过去周期10%分位（先触发）"),
                _reference(tc_z_q05, "z·过去周期5%分位（深部）"),
                _reference(0.0, "自身4年均值（中性）"),
            ],
            direction="below",
        ),
        spec(
            "cvdd_proximity", label="CVDD 接近程度", unit="ratio",
            description="BTC价格相对固定600万常数CVDD价格地板的接近程度；数值越大，代表越接近。",
            formula="1 / abs(Price / [cumsum(CDD × Price) / (MarketAgeDays × 6,000,000)] - 1)",
            source="BRK / Bitview Price 与 CDD 基础日线", method="自行计算（Willy Woo 2019 固定常数版）",
            caveat="以相对距离的倒数表达，故越大越接近；价格恰好等于CVDD时倒数无定义，不写入该日。供应归一化CVDD是另一版本；本视图不混用。",
            primary=cvdd_proximity,
            references=[_reference(2.0, "距CVDD 50%（等价旧刻度0.5）")],
            direction="above",
            extra_lines=[LineSpec("cvdd", "CVDD 价格地板", "price", cvdd)],
        ),
        spec(
            "reserve_risk_zscore", label="Reserve Risk · 周期", unit="zscore",
            description="Reserve Risk 经 log + 4年滚动 z-score，消除分母 HODL Bank 累积导致的结构性下移，使各轮周期顶/底可比。",
            formula="z[ log(Reserve Risk), trailing 1460d ]；阈值 = z 的过去周期分位（无前视）",
            source="BRK / Bitview", method="自行计算（无前视）",
            caveat="Reserve Risk = Price / HODL Bank，分母为单调累积量，致绝对值每轮约 ×0.4 下移，固定绝对阈值（如 0.002）在本轮永久失效。本指标对 log(RR) 取 trailing 4 年 z-score 衡量相对本周期的高低，跨周期可比。原始绝对值见 Reserve Risk 指标，切勿套 0.002。",
            primary=rr_zscore,
            references=[
                _reference(rr_z_q10, "z·过去周期10%分位（先触发）"),
                _reference(rr_z_q05, "z·过去周期5%分位（深部）"),
                _reference(0.0, "自身4年均值（中性）"),
            ],
            direction="below",
        ),
    ]

    # Stable display order: by category, then catalogue order.
    category_rank = {name: index for index, name in enumerate(CATEGORY_ORDER)}
    catalogue_order = {metric_id: index for index, metric_id in enumerate(INDICATOR_CATALOG)}
    indicators.sort(key=lambda item: (category_rank[item.category], catalogue_order[item.id]))

    price = {day: value for day, value in raw["price"].items() if value > 0}

    bars = {
        "hodler_npc_30d": BarSpec(
            id="hodler_npc_30d",
            label="HODLer 投降卖出尖峰（占供应 %）",
            unit="%",
            description="全网低估期（MVRV<1）长期不动供应的 30 日净变化占供应比例。负值=投降卖出，正值=低估期积累。",
            source="BRK / Bitview HODLedOrLostSupply + Supply",
            method="[HODLedOrLostSupply(t) − HODLedOrLostSupply(t−30d)] / Supply；仅保留 MVRV<1 日",
            caveat="仅保留 MVRV<1 低估期，不显示牛市派发。原 BTC 口径=Glassnode LTH-Net Position Change。",
            series=hodler_npc_undervalued,
        ),
        "spent_value_ge155d_share": BarSpec(
            id="spent_value_ge155d_share",
            label=">=155d 花费价值占比",
            unit="%",
            description="全网低估期（MVRV<1）币龄≥155天的花费价值占总花费价值比例，老币投降确认线。",
            source="Open Bitcoin Metrics v0.1.0",
            method="Spent Value >=155d / Total Spent Value；仅保留 MVRV<1 日",
            caveat="公开数据不能逐笔判断老币是否亏损卖出；MVRV<1 仅代表全网整体亏损。仅作低估期投降确认，不作独立触发。",
            series=spent_share_undervalued,
        ),
    }

    data_date = max(price)
    return ComputedData(
        indicators=indicators,
        price=price,
        bars=bars,
        data_date=data_date,
        source_metadata=dict(source_metadata) if source_metadata else {},
        thresholds_log=log,
    )
