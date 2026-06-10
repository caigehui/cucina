import json
import tempfile
import unittest
from pathlib import Path

from scripts.mirofish_bridge import create_seed_pack, import_report, slugify_topic


class MiroFishBridgeTests(unittest.TestCase):
    def test_slugify_topic_keeps_symbols_and_ascii_words(self):
        self.assertEqual(slugify_topic("NVDA 财报 情景推演!"), "nvda")

    def test_create_seed_pack_writes_contract_files(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            source = root / "source.md"
            source.write_text("公开新闻摘要: NVDA 数据中心需求仍强。", encoding="utf-8")

            result = create_seed_pack(
                topic="NVDA earnings simulation",
                question="若毛利率下修,AI 供应链叙事如何变化?",
                input_paths=[source],
                symbols=["NVDA"],
                horizon="2 weeks",
                output_root=root / "output",
                as_of="2026-06-10",
            )

            self.assertTrue((result.run_dir / "seed.md").exists())
            self.assertTrue((result.run_dir / "scenario.json").exists())
            self.assertTrue((result.run_dir / "summary_for_cucina.md").exists())
            seed = (result.run_dir / "seed.md").read_text(encoding="utf-8")
            self.assertIn("模拟推断", seed)
            self.assertIn("不是交易指令", seed)
            self.assertIn("NVDA", seed)
            scenario = json.loads((result.run_dir / "scenario.json").read_text(encoding="utf-8"))
            self.assertEqual(scenario["topic"], "NVDA earnings simulation")
            self.assertEqual(scenario["as_of"], "2026-06-10")
            self.assertEqual(scenario["privacy_level"], "sanitized_by_default")

    def test_create_seed_pack_marks_key_like_content(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            source = root / "source.md"
            source.write_text("LLM_API_KEY=secret-value", encoding="utf-8")

            result = create_seed_pack(
                topic="Key leak check",
                question="检查隐私提示",
                input_paths=[source],
                symbols=[],
                horizon="1 week",
                output_root=root / "output",
                as_of="2026-06-10",
            )

            scenario = json.loads((result.run_dir / "scenario.json").read_text(encoding="utf-8"))
            self.assertTrue(scenario["privacy_warnings"])
            self.assertIn("LLM_API_KEY", scenario["privacy_warnings"][0])

    def test_import_report_copies_markdown_and_updates_summary(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            run_dir = root / "output" / "2026-06-10_nvda"
            run_dir.mkdir(parents=True)
            (run_dir / "summary_for_cucina.md").write_text("# 摘要\n", encoding="utf-8")
            report = root / "report.md"
            report.write_text("# MiroFish 报告\n\n模拟结果。", encoding="utf-8")

            imported = import_report(run_dir=run_dir, report_path=report, as_of="2026-06-10")

            self.assertEqual(imported.name, "mirofish_report.md")
            self.assertIn("模拟结果", imported.read_text(encoding="utf-8"))
            summary = (run_dir / "summary_for_cucina.md").read_text(encoding="utf-8")
            self.assertIn("mirofish_report.md", summary)
            self.assertIn("2026-06-10", summary)


if __name__ == "__main__":
    unittest.main()
