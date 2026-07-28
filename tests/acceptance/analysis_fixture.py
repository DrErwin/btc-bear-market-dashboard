from __future__ import annotations


def build_valid_analysis(packet: dict) -> dict:
    """Return a compact analysis aligned with the checked-in current snapshot."""

    return {
        "analysis_date": packet["data_date"],
        "stage": "熊市下行期",
        "consistency": "中等",
        "summary": (
            "供应利润空间正在收窄，矿工收入也已经开始承压；"
            "不过整体估值还没有进入明显压力区。"
        ),
        "pressure_summary": "链上亏损卖出和卖方力量减弱同时出现，说明当前市场压力偏重。",
        "compact": {
            "support": {
                "title": "当前市场状态",
                "text": "供应利润空间正在收窄，矿工收入已经开始承压。",
            },
            "obstacle": {
                "title": "还没有进入更深阶段",
                "text": "整体估值还没有进入明显压力区。",
            },
            "next": {
                "title": "接下来观察",
                "text": "观察整体估值是否继续下降，以及矿工压力是否进一步加深。",
            },
        },
        "categories": [
            {"id": "valuation", "status": "未确认", "note": "尚无指标触发。"},
            {"id": "supply", "status": "部分确认", "note": "RUP 已触发。"},
            {"id": "capital", "status": "部分确认", "note": "aSOPR 已触发。"},
            {"id": "holders", "status": "部分确认", "note": "Seller 已触发。"},
            {"id": "miners", "status": "部分确认", "note": "Puell 已触发。"},
            {"id": "anchors", "status": "部分确认", "note": "两个指标已触发。"},
        ],
        "detailed": {
            "supporting": "RUP 显示供应利润空间正在收窄。",
            "contrary": "MVRV、AVIV 与 RC-NPC 均未触发。",
            "next_stage": "继续观察整体估值是否进入压力区。",
        },
    }
