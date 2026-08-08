from __future__ import annotations

import json
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch

from core.state import StateStore


class StateStoreTest(unittest.TestCase):
    def test_state_store_save_creates_state_json(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            state_path = Path(tmp) / "state.json"
            store = StateStore(state_path)

            result = store.save({"runtime": {"mode": "demo"}})

            self.assertTrue(result)
            self.assertEqual(store.load()["runtime"]["mode"], "demo")
            self.assertTrue(state_path.exists())

    def test_state_store_save_uses_unique_temp_without_fixed_state_tmp(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            state_path = root / "state.json"
            store = StateStore(state_path)

            self.assertTrue(store.save({"version": 1}))
            self.assertTrue(store.save({"version": 2}))

            self.assertEqual(json.loads(state_path.read_text(encoding="utf-8"))["version"], 2)
            self.assertFalse((root / "state.tmp").exists())
            self.assertEqual(list(root.glob("*.tmp")), [])

    def test_state_store_save_permission_error_writes_recovery_snapshot(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            state_path = root / "state.json"
            store = StateStore(state_path)

            with patch.object(Path, "replace", side_effect=PermissionError("locked")):
                result = store.save({"runtime": {"mode": "demo"}})

            recovery_files = list(root.glob("state.recovery.*.json"))
            self.assertFalse(result)
            self.assertEqual(len(recovery_files), 1)
            self.assertEqual(
                json.loads(recovery_files[0].read_text(encoding="utf-8"))["runtime"]["mode"],
                "demo",
            )
            self.assertEqual(list(root.glob("*.tmp")), [])

    def test_state_store_save_strict_reraises_permission_error_after_recovery(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            store = StateStore(root / "state.json")

            with (
                patch.object(Path, "replace", side_effect=PermissionError("locked")),
                self.assertRaises(PermissionError),
            ):
                store.save({"runtime": {"mode": "live"}}, strict=True)

            self.assertEqual(len(list(root.glob("state.recovery.*.json"))), 1)

    def test_state_store_load_permission_error_returns_empty_state(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            state_path = Path(tmp) / "state.json"
            state_path.write_text("{}", encoding="utf-8")
            store = StateStore(state_path)

            with patch.object(Path, "read_text", side_effect=PermissionError("locked")):
                self.assertEqual(store.load(), {})


if __name__ == "__main__":
    unittest.main()
