import subprocess
import sys
import tempfile
import unittest
from pathlib import Path


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


if __name__ == "__main__":
    unittest.main()
