from __future__ import annotations

import json
import os
from pathlib import Path
import time
from typing import Any, Dict


class StateStore:
    def __init__(self, path: str | Path) -> None:
        self.path = Path(path)

    def load(self) -> Dict[str, Any]:
        if not self.path.exists():
            return {}
        try:
            return json.loads(self.path.read_text(encoding="utf-8"))
        except (json.JSONDecodeError, PermissionError):
            return {}

    def save(self, state: Dict[str, Any], *, strict: bool = False) -> bool:
        self.path.parent.mkdir(parents=True, exist_ok=True)
        payload = json.dumps(state, indent=2)
        temp_path = self._unique_temp_path()
        try:
            temp_path.write_text(payload, encoding="utf-8")
            self._replace_with_retry(temp_path)
            return True
        except PermissionError:
            recovery_path = self._write_recovery_snapshot(payload)
            self._cleanup_temp(temp_path)
            if strict:
                raise
            print(
                f"[STATE_SAVE_WARNING] state_path={self.path} recovery_path={recovery_path}",
                flush=True,
            )
            return False

    def _replace_with_retry(self, temp_path: Path) -> None:
        delays = (0.05, 0.1, 0.2, 0.2, 0.2)
        last_error: PermissionError | None = None
        for index, delay in enumerate(delays):
            try:
                temp_path.replace(self.path)
                return
            except PermissionError as exc:
                last_error = exc
                if index < len(delays) - 1:
                    time.sleep(delay)
        if last_error is not None:
            raise last_error

    def _unique_temp_path(self) -> Path:
        return self.path.with_name(
            f"{self.path.stem}.{os.getpid()}.{time.time_ns()}.tmp"
        )

    def _write_recovery_snapshot(self, payload: str) -> Path:
        recovery_path = self.path.with_name(
            f"{self.path.stem}.recovery.{time.time_ns()}.json"
        )
        recovery_path.write_text(payload, encoding="utf-8")
        return recovery_path

    @staticmethod
    def _cleanup_temp(temp_path: Path) -> None:
        try:
            temp_path.unlink(missing_ok=True)
        except OSError:
            pass
