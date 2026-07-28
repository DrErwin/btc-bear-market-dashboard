from __future__ import annotations

import copy
import json
import subprocess
from pathlib import Path

from services.ai import provider
from services.data.packet_display import BY_CANONICAL
from tests.acceptance.analysis_fixture import build_valid_analysis


ROOT = Path(__file__).resolve().parents[2]
WORKFLOW_PATH = ROOT / ".github" / "workflows" / "daily-update.yml"
PACKET_PATH = ROOT / "dashboard" / "public" / "data" / "packet.json"


def test_daily_workflow_runs_at_noon_in_shanghai() -> None:
    workflow = WORKFLOW_PATH.read_text(encoding="utf-8")

    assert "cron: '0 12 * * *'" in workflow
    assert 'timezone: "Asia/Shanghai"' in workflow
    assert "workflow_dispatch:" in workflow


def test_daily_workflow_uses_real_ai_and_pushes_the_complete_result() -> None:
    workflow = WORKFLOW_PATH.read_text(encoding="utf-8")

    assert "AI_API_KEY: ${{ secrets.AI_API_KEY }}" in workflow
    assert "AI_BASE_URL: https://open.bigmodel.cn/api/paas/v4" in workflow
    assert "AI_MODEL: glm-5.2" in workflow
    assert "python services/run_daily.py" in workflow
    assert "python services/run_daily.py --mock-ai" not in workflow
    assert "dashboard/public/data/packet.json" in workflow
    assert "artifacts/run-log.jsonl" in workflow
    assert "git push" in workflow


def test_optional_ai_environment_values_can_be_blank(
    monkeypatch,
) -> None:
    packet = json.loads(PACKET_PATH.read_text(encoding="utf-8"))
    visible_analysis = build_valid_analysis(packet)
    captured: dict[str, object] = {}

    class FakeResponse:
        def __enter__(self):
            return self

        def __exit__(self, *args):
            return False

        def read(self) -> bytes:
            response = {
                "choices": [
                    {
                        "message": {
                                "content": json.dumps(
                                    visible_analysis, ensure_ascii=False
                                )
                        }
                    }
                ]
            }
            return json.dumps(response, ensure_ascii=False).encode("utf-8")

    def fake_urlopen(request, timeout):
        captured["url"] = request.full_url
        captured["timeout"] = timeout
        captured["body"] = json.loads(request.data)
        return FakeResponse()

    monkeypatch.setenv("AI_API_KEY", "test-only-key")
    monkeypatch.setenv("AI_BASE_URL", "")
    monkeypatch.setenv("AI_MODEL", "")
    monkeypatch.setattr(provider, "urlopen", fake_urlopen)

    analysis, reason = provider.call_ai(
        packet["snapshot"],
        data_date=packet["data_date"],
        mock=False,
    )

    assert reason is None
    assert analysis is not None
    assert captured["url"] == (
        "https://open.bigmodel.cn/api/paas/v4/chat/completions"
    )
    assert captured["timeout"] == 300
    assert captured["body"]["model"] == "glm-5.2"
    assert captured["body"]["thinking"] == {"type": "enabled"}
    assert captured["body"]["reasoning_effort"] == "high"
    assert captured["body"]["max_tokens"] == 4096
    user_prompt = captured["body"]["messages"][1]["content"]
    assert "只有触发阈值的指标才能列入支持证据" in user_prompt
    assert "未触发的指标只能列入阻碍、反面证据或待确认条件" in user_prompt
    assert "detailed.supporting 中不得出现任何未触发指标" in user_prompt
    assert "核心或辅助是指标角色，不是类别角色" in user_prompt
    assert "只有一个触发阈值的指标" in user_prompt
    assert "不得说它未触发更深档位" in user_prompt
    assert "即使是否定句或风险提示，也不要复述任何禁止词" in user_prompt
    assert "禁止词表（输入里出现也不能照抄）" in user_prompt
    assert "做多" in user_prompt
    assert "持仓" in user_prompt
    assert "链上花费" in user_prompt
    assert "长期持有信念进入周期高位" in user_prompt
    assert "长期供应净变化零线" in user_prompt


def test_rc_npc_threshold_meaning_matches_its_configured_direction() -> None:
    rc_npc = BY_CANONICAL["realized_cap_relative_npc_30d"]

    assert rc_npc.thresholds[0]["meaning"] == (
        "三十日已实现资本变化由收缩转为扩张。"
    )


def test_invalid_ai_wording_is_rewritten_once_before_fallback(
    monkeypatch,
) -> None:
    packet = json.loads(PACKET_PATH.read_text(encoding="utf-8"))
    visible_analysis = build_valid_analysis(packet)
    invalid = copy.deepcopy(visible_analysis)
    invalid["detailed"]["contrary"] = "建议买入"
    responses = [invalid, visible_analysis]
    requests: list[dict] = []

    class FakeResponse:
        def __init__(self, analysis: dict):
            self.analysis = analysis

        def __enter__(self):
            return self

        def __exit__(self, *args):
            return False

        def read(self) -> bytes:
            response = {
                "choices": [
                    {
                        "message": {
                            "content": json.dumps(
                                self.analysis, ensure_ascii=False
                            )
                        }
                    }
                ]
            }
            return json.dumps(response, ensure_ascii=False).encode("utf-8")

    def fake_urlopen(request, timeout):
        requests.append(json.loads(request.data))
        return FakeResponse(responses.pop(0))

    monkeypatch.setenv("AI_API_KEY", "test-only-key")
    monkeypatch.delenv("AI_BASE_URL", raising=False)
    monkeypatch.delenv("AI_MODEL", raising=False)
    monkeypatch.setattr(provider, "urlopen", fake_urlopen)

    analysis, reason = provider.call_ai(
        packet["snapshot"],
        data_date=packet["data_date"],
        mock=False,
    )

    assert reason is None
    assert analysis == visible_analysis
    assert len(requests) == 2
    assert "上一份输出未通过校验" in requests[1]["messages"][1]["content"]


def test_transient_ai_timeout_is_retried_once(
    monkeypatch,
) -> None:
    packet = json.loads(PACKET_PATH.read_text(encoding="utf-8"))
    visible_analysis = build_valid_analysis(packet)
    attempts = 0

    class FakeResponse:
        def __enter__(self):
            return self

        def __exit__(self, *args):
            return False

        def read(self) -> bytes:
            response = {
                "choices": [
                    {
                        "message": {
                            "content": json.dumps(
                                visible_analysis, ensure_ascii=False
                            )
                        }
                    }
                ]
            }
            return json.dumps(response, ensure_ascii=False).encode("utf-8")

    def fake_urlopen(request, timeout):
        nonlocal attempts
        attempts += 1
        if attempts == 1:
            raise TimeoutError("temporary timeout")
        return FakeResponse()

    monkeypatch.setenv("AI_API_KEY", "test-only-key")
    monkeypatch.delenv("AI_BASE_URL", raising=False)
    monkeypatch.delenv("AI_MODEL", raising=False)
    monkeypatch.setattr(provider, "urlopen", fake_urlopen)

    analysis, reason = provider.call_ai(
        packet["snapshot"],
        data_date=packet["data_date"],
        mock=False,
    )

    assert reason is None
    assert analysis == visible_analysis
    assert attempts == 2


def test_daily_audit_log_is_not_ignored_by_git() -> None:
    result = subprocess.run(
        [
            "git",
            "check-ignore",
            "--no-index",
            "artifacts/run-log.jsonl",
        ],
        cwd=ROOT,
        capture_output=True,
        text=True,
        check=False,
    )

    assert result.returncode == 1, result.stdout or result.stderr
