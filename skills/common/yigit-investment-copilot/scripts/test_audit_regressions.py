"""Deterministic offline regressions for data integrity and probability semantics."""
import copy
import csv
from datetime import timedelta
import hashlib
import importlib.util
import json
from pathlib import Path
import subprocess
import sys
import tempfile
import unittest
from unittest.mock import patch

ROOT = Path(__file__).resolve().parents[1]


def module(name, relative):
    spec = importlib.util.spec_from_file_location(name, ROOT / relative)
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


history = module("price_history", "modules/market-data-engine/scripts/price_history.py")
forecast = module("forecast_ranges", "modules/probabilistic-market-forecast/scripts/forecast_ranges.py")
technical = module("technical_indicators", "modules/technical-quant-analysis/scripts/technical_indicators.py")
from common import history_issues


class InvestmentChecks(unittest.TestCase):
    def test_discontinuities_never_rewrite_prices(self):
        rows = [{"date": "2020-01-01", "open": 100, "high": 101, "low": 99, "close": 100, "adj_close": 100, "volume": 1000},
                {"date": "2020-01-02", "open": 50, "high": 51, "low": 49, "close": 50, "adj_close": 50, "volume": 2000}]
        original = copy.deepcopy(rows)
        for events in ([], [{"type": "splits", "date": "2020-01-02", "ratio": "2:1"}]):
            flags = history.repair_corporate_actions(rows, events, True)
            self.assertEqual(rows, original)
            self.assertFalse(flags[0]["applied"])

    def test_vendor_adjustment_absence_is_not_fabricated(self):
        result = {"timestamp": [1577836800, 1577923200], "meta": {"gmtoffset": 0},
                  "indicators": {"quote": [{"close": [100, 50]}]}}
        rows, _ = history.parse(result, "1d")
        self.assertEqual([r["adj_close"] for r in rows], ["", ""])
        result["indicators"]["adjclose"] = [{"adjclose": [50, 50]}]
        rows, _ = history.parse(result, "1d")
        self.assertEqual([r["close"] for r in rows], [100, 50])
        self.assertEqual([r["adj_close"] for r in rows], [50, 50])

    def test_cache_identity_age_hash_and_legacy(self):
        with tempfile.TemporaryDirectory() as temp:
            path = Path(temp) / "TEST.csv"
            path.write_text("date,close\n2026-10-07,100\n", encoding="utf-8")
            meta = {"cache_schema": 2, "yahoo_symbol": "TEST.IS", "range": "2y", "interval": "1d", "mode": "chart",
                    "fetched_at": history.iso(history.now_trt()), "last_date": history.now_trt().date().isoformat(),
                    "csv_sha256": hashlib.sha256(path.read_bytes()).hexdigest()}
            sidecar = path.with_suffix(".meta.json")
            def store(data):
                sidecar.write_text(json.dumps(data), encoding="utf-8")
            store(meta)
            self.assertTrue(history.cache_valid(path, "TEST.IS", "2y", "1d", "chart", 24))
            self.assertFalse(history.cache_valid(path, "TEST.IS", "5y", "1d", "chart", 24))
            self.assertFalse(history.cache_valid(path, "TEST.IS", "2y", "1d", "spark", 24))
            for change in ({"cache_schema": 1}, {"fetched_at": history.iso(history.now_trt() - timedelta(days=5))},
                           {"fetched_at": history.iso(history.now_trt() + timedelta(days=1))},
                           {"last_date": "2020-01-01"}, {"csv_sha256": "bad"}):
                store({**meta, **change})
                self.assertFalse(history.cache_valid(path, "TEST.IS", "2y", "1d", "chart", 24))
                self.assertTrue(history_issues(path))
            store({**meta, "corporate_action_flags": [{"applied": False}]})
            self.assertTrue(history_issues(path))
            store(meta)
            with patch.object(history, "fetch_chart", side_effect=AssertionError("network forbidden")):
                self.assertEqual(history.fetch_one("TEST", Path(temp), "2y", "1d", 24)[2], "cached")

    def csv(self, folder):
        path = Path(folder) / "prices.csv"
        path.write_text("date,open,high,low,close,adj_close,volume,complete\n"
                        "2020-01-01,100,100,100,100,50,1000,1\n"
                        "2020-01-02,50,50,50,50,50,2000,1\n"
                        "2020-01-03,55,55,55,55,55,2100,1\n"
                        "2020-01-04,999,999,999,999,999,100,0\n", encoding="utf-8")
        return path

    def test_adjusted_empirical_excludes_partial_bars(self):
        with tempfile.TemporaryDirectory() as temp:
            result = forecast.empirical(self.csv(temp), 1, 55, 60, .2)
            self.assertEqual(result["samples"], 2)
            self.assertEqual(result["price_basis"], "adj_close")
            self.assertAlmostEqual(result["return_quantiles"]["p50"], .05)
            self.assertFalse(result["calibrated"])
            self.assertNotIn("probability_reach_target", result)
            with self.assertRaises(SystemExit):
                forecast.empirical(self.csv(temp), -1, 55, 60, .2)

    def test_dividend_factor_does_not_rewrite_volume(self):
        with tempfile.TemporaryDirectory() as temp:
            rows, _ = technical.load(self.csv(temp))
            self.assertEqual(rows[0]["close"], 50)
            self.assertEqual(rows[0]["volume"], 1000)

    def test_cli_probability_is_terminal_and_finite(self):
        script = ROOT / "modules/probabilistic-market-forecast/scripts/forecast_ranges.py"
        args = [sys.executable, "-B", str(script), "--current-price", "100", "--annualized-vol", "0", "--horizon-days", "30", "--target-price", "110"]
        result = subprocess.run(args, capture_output=True, text=True)
        self.assertEqual(result.returncode, 0, result.stderr)
        data = json.loads(result.stdout)
        self.assertEqual(data["probability_terminal_at_or_above_target"], 0)
        self.assertFalse(data["calibrated"])
        for field, value in (("--annualized-vol", "nan"), ("--target-price", "0")):
            bad = args.copy()
            bad[bad.index(field) + 1] = value
            self.assertNotEqual(subprocess.run(bad, capture_output=True).returncode, 0)


if __name__ == "__main__":
    unittest.main()
