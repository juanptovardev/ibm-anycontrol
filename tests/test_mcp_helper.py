"""Tests for tools/_mcp.py helper — fake session, no live AnyDesk needed.
Run: python -m unittest discover -s tests
"""
import asyncio
import io
import os
import sys
import unittest
from contextlib import redirect_stderr, redirect_stdout
from pathlib import Path
from unittest import mock

sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "tools"))

from _mcp import call, need_hwnd, report


class FakeContent:
    def __init__(self, text=None):
        self.text = text


class FakeResult:
    def __init__(self, is_error, texts):
        self.isError = is_error
        self.content = [FakeContent(t) for t in texts]


class FakeSession:
    def __init__(self, result):
        self._result = result
        self.calls = []

    async def call_tool(self, name, args):
        self.calls.append((name, args))
        return self._result


class TestCall(unittest.TestCase):
    def test_error_surfaces(self):
        session = FakeSession(FakeResult(True, ["boom", None, "detail"]))
        out = asyncio.run(call(session, "ocr", {"mode": "ocr"}))
        self.assertTrue(out["isError"])
        self.assertEqual(out["text"], "boom\ndetail")
        self.assertEqual(session.calls, [("ocr", {"mode": "ocr"})])

    def test_ok_defaults_empty_args(self):
        session = FakeSession(FakeResult(False, ["ok"]))
        out = asyncio.run(call(session, "health"))
        self.assertFalse(out["isError"])
        self.assertEqual(out["text"], "ok")


class TestReport(unittest.TestCase):
    def test_failure_returns_1(self):
        buf = io.StringIO()
        with redirect_stderr(buf):
            code = report("X", {"isError": True, "text": "err"})
        self.assertEqual(code, 1)
        self.assertIn("FAILED: err", buf.getvalue())

    def test_success_returns_0_and_truncates(self):
        buf = io.StringIO()
        with redirect_stdout(buf):
            code = report("X", {"isError": False, "text": "z" * 50}, limit=10)
        self.assertEqual(code, 0)
        self.assertIn("...[truncado]", buf.getvalue())


class TestNeedHwnd(unittest.TestCase):
    def test_missing_arg_exits_2(self):
        env = {k: v for k, v in os.environ.items()
               if k != "MCP_ANYDESK_HWND"}
        with mock.patch.dict("os.environ", env, clear=True):
            with self.assertRaises(SystemExit) as cm:
                need_hwnd(["prog"])
        self.assertEqual(cm.exception.code, 2)

    def test_arg_wins_over_env(self):
        with mock.patch.dict(
            "os.environ", {"MCP_ANYDESK_HWND": "111"}
        ):
            self.assertEqual(need_hwnd(["prog", "222"]), 222)

    def test_env_fallback(self):
        with mock.patch.dict(
            "os.environ", {"MCP_ANYDESK_HWND": "198526"}
        ):
            self.assertEqual(need_hwnd(["prog"]), 198526)

    def test_invalid_exits_2(self):
        with mock.patch.dict("os.environ", {}, clear=True):
            with self.assertRaises(SystemExit) as cm:
                need_hwnd(["prog", "abc"])
        self.assertEqual(cm.exception.code, 2)


if __name__ == "__main__":
    unittest.main()
