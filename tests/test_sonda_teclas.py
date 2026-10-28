"""Parseo de acordes de sonda_teclas: 'shift+f4' -> ['shift', 'f4']."""
import sys
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "tools"))

import sonda_teclas


class TestSplitTeclas(unittest.TestCase):
    def test_acorde_doble(self):
        self.assertEqual(sonda_teclas.split_teclas("shift+f4"), ["shift", "f4"])

    def test_acorde_triple(self):
        self.assertEqual(sonda_teclas.split_teclas("ctrl+shift+down"),
                         ["ctrl", "shift", "down"])

    def test_tecla_simple(self):
        self.assertEqual(sonda_teclas.split_teclas("f10"), ["f10"])

    def test_enter_sigue_siendo_tecla_simple(self):
        self.assertEqual(sonda_teclas.split_teclas("enter"), ["enter"])


if __name__ == "__main__":
    unittest.main()
