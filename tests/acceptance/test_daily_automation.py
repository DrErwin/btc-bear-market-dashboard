from __future__ import annotations

import json
import subprocess
from pathlib import Path

from services.ai import provider


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
                                packet["analysis"], ensure_ascii=False
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
    assert captured["timeout"] == 180
    assert captured["body"]["model"] == "glm-5.2"
    assert captured["body"]["thinking"] == {"type": "enabled"}
    assert captured["body"]["reasoning_effort"] == "max"


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
