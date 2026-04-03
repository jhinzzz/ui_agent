import json
import sys
import uuid
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, Optional

import config.config as config
from common.logs import log


def _now_iso() -> str:
    return datetime.now().isoformat(timespec="seconds")


class RunReporter:
    def __init__(
        self,
        goal: str,
        platform: str,
        env_name: str,
        output_script_path: str,
        json_output: bool = False,
        vision_enabled: bool = False,
        max_steps: int = 0,
        base_dir: Optional[str] = None,
    ):
        self.run_id = f"{datetime.now().strftime('%Y%m%d_%H%M%S')}_{str(uuid.uuid4())[:8]}"
        self._json_output = json_output
        self._base_dir = Path(base_dir or config.RUN_REPORT_BASE_DIR) / self.run_id
        self._screenshots_dir = self._base_dir / "screenshots"
        self._steps_file = self._base_dir / "steps.jsonl"
        self._summary_file = self._base_dir / "summary.json"
        self._artifacts_file = self._base_dir / "artifacts.json"
        self._finished = False

        self._base_dir.mkdir(parents=True, exist_ok=True)

        self._artifacts: Dict[str, Any] = {
            "generated_script": {"path": str(output_script_path)},
            "steps_file": {"path": str(self._steps_file)},
            "summary_file": {"path": str(self._summary_file)},
            "screenshots": [],
            "videos": [],
        }
        self._summary: Dict[str, Any] = {
            "run_id": self.run_id,
            "goal": goal,
            "platform": platform,
            "env": env_name,
            "vision_enabled": vision_enabled,
            "max_steps": max_steps,
            "output_script_path": str(output_script_path),
            "status": "running",
            "exit_code": None,
            "steps_executed": 0,
            "last_error": "",
            "started_at": _now_iso(),
            "finished_at": None,
            "artifacts_path": str(self._artifacts_file),
        }
        self._write_json(self._artifacts_file, self._artifacts)
        self._write_json(self._summary_file, self._summary)

    @property
    def run_dir(self) -> Path:
        return self._base_dir

    def emit_event(self, event: str, **payload: Any) -> None:
        record = {
            "timestamp": _now_iso(),
            "run_id": self.run_id,
            "event": event,
            **payload,
        }
        try:
            with self._steps_file.open("a", encoding="utf-8") as f:
                f.write(json.dumps(record, ensure_ascii=False) + "\n")
            if self._json_output:
                print(json.dumps(record, ensure_ascii=False), file=sys.stdout, flush=True)
        except Exception as e:
            log.warning(f"⚠️ [Warning] 写入运行事件失败: {e}")

    def save_screenshot(
        self, img_bytes: bytes, step_index: int, name: Optional[str] = None
    ) -> str:
        if not img_bytes:
            return ""

        self._screenshots_dir.mkdir(parents=True, exist_ok=True)
        file_name = name or f"step_{step_index:03d}.png"
        screenshot_path = self._screenshots_dir / file_name
        try:
            screenshot_path.write_bytes(img_bytes)
            artifact = {
                "path": str(screenshot_path),
                "step": step_index,
                "name": file_name,
            }
            self._artifacts["screenshots"].append(artifact)
            self._write_json(self._artifacts_file, self._artifacts)
            self.emit_event(
                "artifact_saved",
                artifact_type="screenshot",
                step=step_index,
                path=str(screenshot_path),
            )
            return str(screenshot_path)
        except Exception as e:
            log.warning(f"⚠️ [Warning] 保存运行截图失败: {e}")
            return ""

    def finalize(
        self,
        status: str,
        exit_code: int,
        steps_executed: int,
        last_error: str = "",
    ) -> None:
        if self._finished:
            return

        self._summary.update(
            {
                "status": status,
                "exit_code": exit_code,
                "steps_executed": steps_executed,
                "last_error": last_error,
                "finished_at": _now_iso(),
            }
        )
        self._write_json(self._summary_file, self._summary)
        self._write_json(self._artifacts_file, self._artifacts)
        self.emit_event(
            "run_finished",
            status=status,
            exit_code=exit_code,
            steps_executed=steps_executed,
            last_error=last_error,
        )
        self._finished = True

    @staticmethod
    def _write_json(file_path: Path, data: Dict[str, Any]) -> None:
        tmp_path = file_path.with_suffix(file_path.suffix + ".tmp")
        tmp_path.write_text(
            json.dumps(data, ensure_ascii=False, indent=2), encoding="utf-8"
        )
        tmp_path.replace(file_path)
