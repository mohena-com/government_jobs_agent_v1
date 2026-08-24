import json
from pathlib import Path

from src.social.qwen_renderer import render_qwen_plan


def test_qwen_renderer_creates_images_without_qa_text(tmp_path):
    plan = {
        "jobs": [{
            "job_index": 1,
            "presentation_ready": True,
            "locked_facts": {"organisation": "RVUNL"},
            "slide_plan": {"slides": [{
                "number": 1,
                "type": "title",
                "headline": "RVUNL Recruitment 2026-27",
                "subtitle": "Government Jobs",
                "bullets": ["2,005 vacancies", "Status: PASS"],
                "facts_used": [],
            }]},
        }]
    }
    src = tmp_path / "plan.json"
    src.write_text(json.dumps(plan), encoding="utf-8")
    assets = render_qwen_plan(src, tmp_path / "out")
    assert len(assets) == 1
    assert assets[0].exists()
