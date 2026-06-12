import subprocess
import sys
import tempfile
import unittest
import importlib.util
from pathlib import Path

from pdfminer.high_level import extract_text


ROOT = Path(__file__).resolve().parents[1]
AGENTS_EXPORTER = ROOT / ".agents" / "skills" / "daily-report" / "scripts" / "export_report.py"
CLAUDE_EXPORTER = ROOT / ".claude" / "skills" / "daily-report" / "scripts" / "export_report.py"


class DailyReportExportTests(unittest.TestCase):
    def test_daily_report_exporter_writes_pdf_with_daily_profile(self):
        self.assertTrue(AGENTS_EXPORTER.exists())
        self.assertTrue(CLAUDE_EXPORTER.exists())
        self.assertEqual(
            AGENTS_EXPORTER.read_text(encoding="utf-8"),
            CLAUDE_EXPORTER.read_text(encoding="utf-8"),
        )

        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            md = root / "美股研报_2026-06-12.md"
            pdf = root / "美股研报_2026-06-12.pdf"
            md.write_text(
                "\n".join(
                    [
                        "# 美股每日研报｜2026-06-12（美西/美东/北京）",
                        "",
                        "## 核心判断",
                        "- **市场温度**：震荡偏谨慎，等待通胀和美债信号确认。",
                        "- **最大矛盾**：AI 主线仍强，但估值和期权拥挤度抬高。",
                        "",
                        "## 社媒情绪",
                        "| 标的 | WSB 证据 | HYPE 阶段 |",
                        "|---|---|---|",
                        "| NVDA | 样本讨论仍集中 | 中期 |",
                        "",
                        "## 风险与证伪",
                        "- 若美债收益率快速上行，风险资产估值承压。",
                    ]
                ),
                encoding="utf-8",
            )

            result = subprocess.run(
                [
                    sys.executable,
                    str(AGENTS_EXPORTER),
                    "--input",
                    str(md),
                    "--out",
                    str(pdf),
                    "--append-glossary",
                    "--update-md",
                    "--engine",
                    "matplotlib",
                ],
                cwd=ROOT,
                text=True,
                capture_output=True,
                check=False,
            )

            self.assertEqual(result.returncode, 0, result.stderr)
            self.assertIn("profile=daily-report", result.stdout)
            self.assertTrue(pdf.exists())
            self.assertGreater(pdf.stat().st_size, 0)
            self.assertIn("## 术语解释", md.read_text(encoding="utf-8"))

    def test_matplotlib_exporter_does_not_render_markdown_table_syntax(self):
        spec = importlib.util.spec_from_file_location("daily_exporter", AGENTS_EXPORTER)
        self.assertIsNotNone(spec)
        module = importlib.util.module_from_spec(spec)
        assert spec and spec.loader
        spec.loader.exec_module(module)

        class FakeRenderer:
            instances = []

            def __init__(self, out):
                self.out = out
                self.text_calls = []
                self.heading_calls = []
                self.pages = 1
                self.images = 0
                FakeRenderer.instances.append(self)

            def add_gap(self, inches):
                pass

            def add_text(self, text, **kwargs):
                self.text_calls.append(text)

            def add_heading(self, level, text):
                self.heading_calls.append((level, text))

            def add_image(self, path, alt):
                self.images += 1

            def close(self):
                pass

        old_renderer = module.MatplotlibRenderer
        module.MatplotlibRenderer = FakeRenderer
        try:
            module.render_matplotlib(
                Path("report.md"),
                "\n".join(
                    [
                        "# 美股每日研报｜2026-06-12",
                        "",
                        "## 社媒情绪",
                        "| 排名 | 标的 | WSB 关注证据 |",
                        "|---:|---|---|",
                        "| 1 | SPCX | IPO 讨论升温 |",
                    ]
                ),
                Path("report.pdf"),
            )
        finally:
            module.MatplotlibRenderer = old_renderer

        rendered_lines = FakeRenderer.instances[0].text_calls
        self.assertNotIn("|---:|---|---|", rendered_lines)
        self.assertNotIn("| 排名 | 标的 | WSB 关注证据 |", rendered_lines)
        self.assertIn("排名: 1；标的: SPCX；WSB 关注证据: IPO 讨论升温", rendered_lines)

    def test_reportlab_keeps_wsb_stock_radar_as_table(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            md = root / "report.md"
            pdf = root / "report.pdf"
            md.write_text(
                "\n".join(
                    [
                        "# 美股每日研报｜2026-06-12",
                        "",
                        "## 社媒情绪",
                        "### WSB 股票雷达",
                        "| 排名 | 标的/主题 | WSB 关注证据 | 喊单方向 | 常见玩法 | 个股拥挤度 | HYPE 阶段 | 风险/反向信号 |",
                        "|---:|---|---|---|---|---|---|---|",
                        "| 1 | SPCX / SpaceX IPO | Daily discussion 多次出现 | 双向分歧偏 FOMO | IPO、tokenized exposure | 极端 | 末期 | X 叙事密集 |",
                    ]
                ),
                encoding="utf-8",
            )

            result = subprocess.run(
                [
                    sys.executable,
                    str(AGENTS_EXPORTER),
                    "--input",
                    str(md),
                    "--out",
                    str(pdf),
                    "--engine",
                    "reportlab",
                ],
                cwd=ROOT,
                text=True,
                capture_output=True,
                check=False,
            )

            self.assertEqual(result.returncode, 0, result.stderr)
            rendered_text = extract_text(str(pdf))
            self.assertIn("WSB 股票雷达", rendered_text)
            self.assertIn("标的/主题", rendered_text)
            self.assertNotIn("排名: 1；标的/主题: SPCX / SpaceX IPO", rendered_text)


if __name__ == "__main__":
    unittest.main()
