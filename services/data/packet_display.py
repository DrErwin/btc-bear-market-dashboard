"""Stable display identity for the 16 dashboard indicators.

The numbers (current value, threshold values, series) come from the real
``compute_indicators`` pipeline and change daily. The *human-readable* layer —
label, description, source/method wording, per-threshold meaning — is stable, so
it lives here as a one-time editorial asset keyed by the pipeline's canonical id.

Display labels intentionally match the v0.1.0 acceptance fixtures
("STH-MVRV 战术价位", "RUL · 4年 z-score", ...) so the existing UI and
acceptance expectations stay valid; only the underlying values become real.

``display_scale`` = 100 for share/profit metrics stored internally as 0..1
ratios but shown to readers as percent; 1 otherwise. Scaling is applied to
current_value display, threshold values, and series points together so the
chart axis and the snapshot card never disagree.
"""

from __future__ import annotations

from typing import Literal


# category id -> (short, name)
CATEGORIES: dict[str, tuple[str, str]] = {
    "valuation": ("估值与成本", "市场估值与成本基础"),
    "supply": ("供应盈亏", "未实现盈亏与供应盈亏结构"),
    "capital": ("链上资本流", "已实现盈亏与链上资本流"),
    "holders": ("持有者行为", "持有者行为与投降"),
    "miners": ("矿工压力", "矿工经济压力与矿工成本"),
    "anchors": ("长期成本锚", "长期成本锚与持币信念"),
}


UnitKind = Literal["ratio", "percent", "zscore", "small", "price"]


class IndicatorDisplay:
    __slots__ = (
        "canonical_id", "display_id", "label", "role", "unit_kind",
        "unit_label", "display_scale", "description", "formula", "source",
        "method", "caveat", "thresholds",
    )

    def __init__(
        self,
        canonical_id: str,
        display_id: str,
        label: str,
        role: str,
        unit_kind: UnitKind,
        unit_label: str,
        description: str,
        formula: str,
        source: str,
        method: str,
        caveat: str,
        thresholds: list[dict],  # [{"label": str, "meaning": str}] in references order
    ) -> None:
        self.canonical_id = canonical_id
        self.display_id = display_id
        self.label = label
        self.role = role
        self.unit_kind = unit_kind
        self.unit_label = unit_label
        self.display_scale = 100.0 if unit_kind == "percent" else 1.0
        self.description = description
        self.formula = formula
        self.source = source
        self.method = method
        self.caveat = caveat
        self.thresholds = thresholds


# Ordered by category, then the catalogue order services/data/metrics.py emits.
INDICATORS: list[IndicatorDisplay] = [
    IndicatorDisplay(
        "mvrv", "mvrv", "MVRV", "核心", "ratio", "比率",
        description="比较市场总价值与链上已实现成本，观察全市场的未实现盈亏位置。",
        formula="Market Cap / Realized Cap",
        source="BRK / Bitview 基础日线", method="自行计算",
        caveat="不能单独证明最低点已经出现；与 AVIV 属同一核心估值维度，不重复计作独立证据。",
        thresholds=[
            {"label": "成本平衡线", "meaning": "市场价值低于全市场已实现成本基础。"},
            {"label": "深度低估线", "meaning": "进入更深的估值压力区。"},
        ],
    ),
    IndicatorDisplay(
        "aviv", "aviv", "AVIV", "核心", "ratio", "比率",
        description="从活跃投资者成本角度观察市场估值压力与成本位置。",
        formula="(Market Cap × Liveliness) / (Realized Cap - Thermocap)",
        source="BRK / Bitview 四条基础日线", method="自行计算（ARK × Glassnode 原始定义）",
        caveat="Bitview 成品 aviv_ratio 使用不同分子，本看板不拿它作同公式误差检查。",
        thresholds=[
            {"label": "低估观察线", "meaning": "活跃投资者成本压力增加。"},
            {"label": "深度低估参考", "meaning": "进入核心估值压力区。"},
        ],
    ),
    IndicatorDisplay(
        "sth_mvrv_price", "sth-mvrv", "STH-MVRV 战术价位", "辅助", "ratio", "比率",
        description="STH-MVRV 三套统计档位（5%分位 / 1.5σ / 1.5·MAD）作为短期持有者视角的估值档，价位阶梯 = 档位 × STH-RP。",
        formula="Q5 / (mean−1.5σ) / (median−1.5·1.4826·MAD)；阈值在无前视窗口 [2018,2022底] 上算",
        source="BRK / Bitview 基础日线", method="自行计算（无前视）",
        caveat="三法对照：5%分位最浅、1.5σ居中偏浅、1.5·MAD最深。用于补充价格位置，不独立抬高整体阶段。",
        thresholds=[
            {"label": "5%分位（无前视）", "meaning": "最浅档：STH-MVRV 低于过去周期 5% 分位。"},
            {"label": "1.5σ（无前视）", "meaning": "居中档：低于过去周期均值 1.5 个总体标准差。"},
            {"label": "1.5·MAD（无前视）", "meaning": "最深档：低于过去周期中位数 1.5 个 MADσ。"},
        ],
    ),
    IndicatorDisplay(
        "psip", "psip", "PSIP", "辅助", "percent", "%",
        description="观察当前处于盈利状态的比特币供应比例。",
        formula="Supply in Profit / Total Supply",
        source="BRK / Bitview 基础日线", method="自行计算",
        caveat="与亏损供应指标存在结构性关联，不重复计作独立证据。",
        thresholds=[
            {"label": "盈亏供应平衡", "meaning": "盈利供应占比降至约一半。"},
            {"label": "广泛浮亏参考", "meaning": "盈利供应进入较低区间。"},
        ],
    ),
    IndicatorDisplay(
        "sipl", "sipl", "SIPL", "辅助", "percent", "%",
        description="比较盈利供应与亏损供应的结构差异（盈利占比 − 亏损占比）。",
        formula="Gap = Supply-in-Profit/Supply − Supply-in-Loss/Supply",
        source="BRK / Bitview 基础日线", method="自行计算",
        caveat="与 PSIP 是同一底层供应盈亏事实的另一表达；差值大于零表示盈利供应占比更高。",
        thresholds=[
            {"label": "盈利/亏损占比平衡", "meaning": "盈利与亏损供应占比相当。"},
        ],
    ),
    IndicatorDisplay(
        "relative_unrealized_profit", "rup", "Relative Unrealized Profit", "辅助", "percent", "%",
        description="观察未实现利润相对市场规模的压缩程度。",
        formula="Unrealized Profit / Market Cap",
        source="BRK / Bitview 基础日线", method="自行计算",
        caveat="只说明利润空间压缩，不等同于全面投降。",
        thresholds=[
            {"label": "利润压缩线", "meaning": "未实现利润空间收窄。"},
            {"label": "深度压缩线", "meaning": "利润空间进入较深压力区。"},
        ],
    ),
    IndicatorDisplay(
        "relative_unrealized_loss_zscore_4y", "rul-z", "RUL · 4年 z-score", "辅助", "zscore", "z",
        description="将未实现亏损放进滚动四年尺度中比较；底部投降向上 spike。",
        formula="(RUL − rolling mean 1460d) / rolling population std 1460d",
        source="基于 RUL（恒等式推导）计算", method="滚动四年总体标准差",
        caveat="RUL 强右偏，单σ偏松；历史大底 z≈+2.8~+2.9。滚动窗口与缺失值处理会影响跨周期比较。",
        thresholds=[
            {"label": "压力观察线", "meaning": "进入滚动四年尺度的压力区域。"},
            {"label": "深度压力线", "meaning": "进入更深的周期压力区。"},
        ],
    ),
    IndicatorDisplay(
        "realized_cap_relative_npc_30d", "rc-npc", "Realized Cap Relative NPC · 30d", "辅助", "percent", "%",
        description="观察已实现资本在三十日尺度上的相对变化。",
        formula="RC(t) / RC(t−30d) − 1",
        source="BRK / Bitview Realized Cap", method="三十日变化口径",
        caveat="负值不能直接解释为阶段已完成。",
        thresholds=[
            {"label": "资本扩张/收缩分界", "meaning": "三十日已实现资本变化由扩转缩。"},
        ],
    ),
    IndicatorDisplay(
        "asopr", "asopr", "aSOPR", "辅助", "ratio", "比率",
        description="观察链上花费行为整体是在实现盈利还是亏损。",
        formula="Adjusted Spent Output Profit Ratio",
        source="BRK / Bitview", method="公开成品日线（透明开源计算链）",
        caveat="短期波动较大，只用于交叉检查；3d/7d 滞后均值仅作趋势辅助，不触发。",
        thresholds=[
            {"label": "盈亏平衡线", "meaning": "花费行为整体低于盈亏平衡。"},
        ],
    ),
    IndicatorDisplay(
        "hodler_npc_30d", "hodler", "HODLer NPC · 30d", "核心", "percent", "%",
        description="只显示全网低估期（MVRV<1）长期不动供应的 30 日净变化占供应比例：负值=投降卖出，正值=低估期积累。",
        formula="[HODLedOrLostSupply(t) − HODLedOrLostSupply(t−30d)] / Supply；仅保留 MVRV<1",
        source="BRK / Bitview 基础日线", method="自行计算（% of supply）",
        caveat="只保留低估期，不显示牛市派发；深卖阈值=过去周期低估期线 5/10% 分位（无前视）。",
        thresholds=[
            {"label": "深卖阈值·10%分位（无前视）", "meaning": "低估期卖出强度进入过去周期 10% 分位。"},
            {"label": "深卖阈值·5%分位（无前视）", "meaning": "低估期卖出强度进入更深 5% 分位。"},
            {"label": "积累/卖出分界", "meaning": "零线：长期供应由净卖出转为净积累。"},
        ],
    ),
    IndicatorDisplay(
        "spent_value_ge155d_share", "spent155", "≥155d 花费价值占比", "核心", "percent", "%",
        description="只显示全网低估期（MVRV<1）币龄≥155 天的花费价值占比，老币投降确认线。",
        formula="Spent Value >=155d / Total Spent Value；仅保留 MVRV<1",
        source="Open Bitcoin Metrics v0.1.0", method="≥155d 年龄分层",
        caveat="公开数据不能逐笔判断老币是否亏损卖出；MVRV<1 仅代表全网整体亏损。仅作低估期投降确认，不作独立触发。",
        thresholds=[
            {"label": "过去低估期90%分位（无前视）", "meaning": "老币花费占比进入过去低估期 90% 分位。"},
        ],
    ),
    IndicatorDisplay(
        "seller_exhaustion", "seller", "Seller Exhaustion Constant", "辅助", "small", "指数",
        description="结合波动与供应行为，观察卖方压力是否接近耗竭。",
        formula="PSIP × BRK 30d Price Volatility",
        source="BRK / Bitview 基础日线", method="自行计算",
        caveat="用于辅助解释，不能代替核心持有者证据；阈值=过去周期 10% 分位（无前视）。",
        thresholds=[
            {"label": "过去周期10%分位（无前视）", "meaning": "卖方压力接近过去周期 10% 分位的耗竭区。"},
        ],
    ),
    IndicatorDisplay(
        "puell_multiple", "puell", "Puell Multiple", "核心", "ratio", "倍数",
        description="比较矿工当期收入与一年均值，观察矿工经济压力。",
        formula="Daily Subsidy USD / 365-day Average Subsidy USD",
        source="BRK / Bitview", method="公开成品日线；另做日度复算核对",
        caveat="矿工压力是独立核心证据，但不等同于价格最低点；按块计算与按日线复算存在口径差。",
        thresholds=[
            {"label": "低收入区上界", "meaning": "矿工收入低于一年均值。"},
            {"label": "历史深压参考", "meaning": "矿工经济压力进一步加深。"},
        ],
    ),
    IndicatorDisplay(
        "thermocap_multiple_zscore", "thermo", "Thermocap Multiple · 周期 z", "辅助", "zscore", "z",
        description="用周期归一化方式观察市场价值相对累计矿工收入的位置。",
        formula="z[ log(Market Cap / Subsidy Cumulative USD), trailing 1460d ]",
        source="BRK / Bitview", method="log + 滚动四年 z-score（无前视）",
        caveat="归一化方法是相对自身周期的过热/过冷视角；绝对阈值底部 5-7 / 顶部 50-74 仍有效。",
        thresholds=[
            {"label": "z·过去周期10%分位（先触发）", "meaning": "进入周期归一化的低位区。"},
            {"label": "z·过去周期5%分位（深部）", "meaning": "进入更深的周期低位区。"},
            {"label": "自身4年均值（中性）", "meaning": "等于自身滚动四年均值。", "role": "neutral"},
        ],
    ),
    IndicatorDisplay(
        "cvdd_proximity", "cvdd", "CVDD 接近程度", "辅助", "ratio", "指数",
        description="观察价格与长期累计销毁币天成本锚（固定 600 万常数版）的接近程度，越大越接近。",
        formula="1 / abs(Price / CVDD_floor − 1)",
        source="BRK / Bitview Price 与 CDD", method="自行计算（Willy Woo 2019 固定常数版）",
        caveat="以相对距离的倒数表达；价格恰好等于 CVDD 时无定义。供应归一化 CVDD 是另一版本，不混用。",
        thresholds=[
            {"label": "距CVDD 50%", "meaning": "价格距 CVDD 地板约 50%。"},
        ],
    ),
    IndicatorDisplay(
        "reserve_risk_zscore", "reserve", "Reserve Risk · 周期 z", "辅助", "zscore", "z",
        description="长期持有信念与价格激励关系的周期归一化视图。",
        formula="z[ log(Reserve Risk), trailing 1460d ]；阈值 = z 的过去周期分位（无前视）",
        source="BRK / Bitview", method="log + 滚动四年 z-score（无前视）",
        caveat="Reserve Risk 分母为单调累积量，绝对值每轮下移、固定阈值永久失效；切勿套 0.002。",
        thresholds=[
            {"label": "z·过去周期10%分位（先触发）", "meaning": "长期持有信念进入周期高位。"},
            {"label": "z·过去周期5%分位（深部）", "meaning": "长期持有信念处于更深的周期高位。"},
            {"label": "自身4年均值（中性）", "meaning": "等于自身滚动四年均值。", "role": "neutral"},
        ],
    ),
]


BY_CANONICAL: dict[str, IndicatorDisplay] = {item.canonical_id: item for item in INDICATORS}
BY_DISPLAY: dict[str, IndicatorDisplay] = {item.display_id: item for item in INDICATORS}
