#!/usr/bin/env python3
"""
tests/test_parser_robustness.py - no parser may raise on malformed input.

Every parser here reads device output, and device output is the one input we
cannot control: empty on a failed shell call, truncated on a pipe, or a vendor
sentinel we have never seen. A traceback in a parser becomes a traceback in the
middle of a debloat run, so the contract is "return something sane, never raise".
"""

import importlib
import inspect
import os
import sys
import unittest

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "scripts"))

MODULES = [
    "probe", "attrib", "bench", "doze_boost", "power_audit", "security_audit",
    "diagnose", "device_tracker", "connect", "verify", "monitor", "modes",
    "helpdata", "update_database", "compile_speed", "appops_restrict",
    "rescue", "restore",
]
BAD_INPUTS = ["", "garbage", None, "\x00\x01\x02", "x" * 5000,
              "line\n" * 200, "some avg10=abc", "@@PS\n@@"]


def single_arg_parsers():
    found = []
    for name in MODULES:
        module = importlib.import_module(name)
        for attr, fn in inspect.getmembers(module, inspect.isfunction):
            if not (attr.startswith("parse_") or attr in ("split_sections", "classify", "verdict")):
                continue
            try:
                signature = inspect.signature(fn)
            except (TypeError, ValueError):
                continue
            required = [p for p in signature.parameters.values()
                        if p.default is inspect.Parameter.empty
                        and p.kind in (p.POSITIONAL_ONLY, p.POSITIONAL_OR_KEYWORD)]
            if len(required) == 1:
                found.append((name, attr, fn))
    return found


class TestParsersNeverRaise(unittest.TestCase):

    def test_all_single_arg_parsers_survive_bad_input(self):
        parsers = single_arg_parsers()
        self.assertGreaterEqual(len(parsers), 10, "parser discovery broke")
        failures = []
        for module_name, attr, fn in parsers:
            for bad in BAD_INPUTS:
                try:
                    fn(bad)
                except Exception as exc:  # noqa: BLE001 - that is the assertion
                    failures.append("%s.%s(%r) -> %s: %s"
                                    % (module_name, attr, bad, type(exc).__name__, exc))
        self.assertEqual(failures, [], "\n".join(failures))


class TestSpecificRegressions(unittest.TestCase):

    def test_thermal_zone_with_text_value(self):
        import probe
        block = ["Thermal Status: 1",
                 "  Temperature{mValue=abc, mName=AP, mStatus=1}",
                 "  Temperature{mValue=41.2, mName=CPU, mStatus=1}"]
        self.assertEqual(probe.parse_thermal(block)["hottest"], [("CPU", 41.2)])

    def test_doze_whitelist_none(self):
        import doze_boost
        self.assertEqual(doze_boost.parse_deviceidle_whitelist(None)["all"], [])

    def test_batterystats_none(self):
        import power_audit
        self.assertEqual(power_audit.parse_batterystats(None)["total_wakelocks_count"], 0)

    def test_duration_none(self):
        import power_audit
        self.assertEqual(power_audit.parse_duration_to_ms(None), 0)


if __name__ == "__main__":
    unittest.main()
