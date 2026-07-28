from __future__ import annotations


def build_valid_analysis(packet: dict) -> dict:
    """Return a compact analysis aligned with the checked-in current snapshot."""

    return {
        "analysis_date": packet["data_date"],
        "stage": "深度压力期",
        "consistency": "中等",
        "summary": (
            "RUP 已触发利润压缩线，长期持有信念进入周期高位；"
            "核心估值仍未确认。"
        ),
        "compact": {
            "support": {
                "title": "已触发证据",
                "text": "RUP 已触发利润压缩线。",
            },
            "obstacle": {
                "title": "核心估值未确认",
                "text": "MVRV 尚未触发成本平衡线。",
            },
            "next": {
                "title": "等待核心确认",
                "text": "等待核心估值与持有者指标进入观察区。",
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
            "supporting": "RUP 已触发利润压缩线。",
            "contrary": "MVRV、AVIV 与 RC-NPC 均未触发。",
            "next_stage": "等待核心估值进入观察区。",
        },
    }
