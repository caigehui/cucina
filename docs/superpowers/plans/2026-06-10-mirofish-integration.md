# MiroFish Integration Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Build the first Cucina-to-MiroFish file bridge for sanitized seed-pack creation, report import, and documented local workflow.

**Architecture:** Cucina remains the research orchestrator. `scripts/mirofish_bridge.py` creates auditable files under `output/simulations/<date>_<slug>/`, and local skills/docs explain that MiroFish output is simulation inference only.

**Tech Stack:** Python 3.11 standard library, `unittest`, Markdown project docs, local Codex/Claude skills.

---

## File Structure

- Create `scripts/mirofish_bridge.py`: standard-library CLI with `seed` and `import-report` subcommands.
- Create `tests/test_mirofish_bridge.py`: unittest coverage for slug generation, seed-pack creation, privacy warnings, and report import.
- Create `docs/mirofish-integration.md`: user-facing operating guide.
- Create `.agents/skills/mirofish-simulation/SKILL.md`: Cucina local skill for MiroFish scenario simulation.
- Create `.claude/skills/mirofish-simulation/SKILL.md`: byte-for-byte mirror of the `.agents` skill.
- Modify `README.md`: add MiroFish workflow and `output/simulations/`.
- Modify `AGENTS.md`: add skill route, output contract, and no-trading/privacy constraints.

### Task 1: CLI Test Skeleton

**Files:**
- Create: `tests/test_mirofish_bridge.py`
- Create later: `scripts/mirofish_bridge.py`

- [ ] **Step 1: Write failing tests**

```python
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
```

- [ ] **Step 2: Run test to verify it fails**

Run: `python -m unittest tests.test_mirofish_bridge -v`

Expected: FAIL or ERROR because `scripts.mirofish_bridge` does not exist.

### Task 2: Minimal CLI Implementation

**Files:**
- Create: `scripts/mirofish_bridge.py`

- [ ] **Step 1: Implement the tested public API**

Implement `slugify_topic`, `create_seed_pack`, and `import_report` with `pathlib`, `json`, `argparse`, `dataclasses`, `datetime`, `re`, and `shutil`. The code must:

- create output directories,
- write `seed.md`,
- write `scenario.json`,
- write or update `summary_for_cucina.md`,
- detect obvious secret-like strings with patterns for `API_KEY`, `TOKEN`, `SECRET`, `PASSWORD`, and `PRIVATE_KEY`,
- expose `seed` and `import-report` subcommands.

- [ ] **Step 2: Run focused tests**

Run: `python -m unittest tests.test_mirofish_bridge -v`

Expected: all 4 tests pass.

- [ ] **Step 3: Run CLI help**

Run: `python scripts/mirofish_bridge.py --help`

Expected: exit 0 and show `seed` plus `import-report` subcommands.

### Task 3: Documentation and Skill Routing

**Files:**
- Create: `docs/mirofish-integration.md`
- Create: `.agents/skills/mirofish-simulation/SKILL.md`
- Create: `.claude/skills/mirofish-simulation/SKILL.md`
- Modify: `README.md`
- Modify: `AGENTS.md`

- [ ] **Step 1: Write operating guide**

Document the recommended commands:

```powershell
python scripts/mirofish_bridge.py seed --topic 'NVDA earnings simulation' --question '若毛利率下修,AI 供应链叙事如何变化?' --symbol NVDA --input output/tmp/nvda_seed.md
python scripts/mirofish_bridge.py import-report --run-dir output/simulations/2026-06-10_nvda-earnings-simulation --report C:\path\to\mirofish_report.md
```

- [ ] **Step 2: Add local skill**

The skill must require read-only research framing, sanitized seed material, `output/simulations/`, and final risk disclaimer.

- [ ] **Step 3: Mirror local skill**

Copy the exact `.agents` skill content to `.claude`.

- [ ] **Step 4: Update README and AGENTS**

Add MiroFish as a scenario simulation route and document `output/simulations/`.

### Task 4: Final Verification and Commit

**Files:**
- All changed files.

- [ ] **Step 1: Run unit tests**

Run: `python -m unittest tests.test_mirofish_bridge -v`

Expected: `Ran 4 tests` and `OK`.

- [ ] **Step 2: Run CLI help**

Run: `python scripts/mirofish_bridge.py --help`

Expected: exit 0, with `seed` and `import-report`.

- [ ] **Step 3: Verify mirrored skills**

Run: `git diff --no-index .agents/skills/mirofish-simulation/SKILL.md .claude/skills/mirofish-simulation/SKILL.md`

Expected: exit 0 and no diff.

- [ ] **Step 4: Check docs for placeholders**

Run: `rg "T[B]D|T[O]DO|implement[ ]later|fill[ ]in" docs README.md AGENTS.md .agents/skills/mirofish-simulation .claude/skills/mirofish-simulation`

Expected: no matches.

- [ ] **Step 5: Stage only task files and commit**

Run:

```powershell
git status --short
git add scripts/mirofish_bridge.py tests/test_mirofish_bridge.py docs/mirofish-integration.md docs/superpowers/plans/2026-06-10-mirofish-integration.md README.md AGENTS.md .agents/skills/mirofish-simulation/SKILL.md .claude/skills/mirofish-simulation/SKILL.md
git commit -m "feat: add mirofish simulation bridge"
```
