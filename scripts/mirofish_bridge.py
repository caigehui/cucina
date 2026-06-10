from __future__ import annotations

import argparse
import json
import re
import shutil
from dataclasses import dataclass
from datetime import date, datetime, timezone
from pathlib import Path
from typing import Iterable, Sequence


SECRET_PATTERN = re.compile(
    r"\b[A-Z0-9_]*(?:API_KEY|TOKEN|SECRET|PASSWORD|PRIVATE_KEY)[A-Z0-9_]*\b",
    re.IGNORECASE,
)


@dataclass(frozen=True)
class SeedPackResult:
    run_dir: Path
    seed_path: Path
    scenario_path: Path
    summary_path: Path


def slugify_topic(topic: str) -> str:
    words = re.findall(r"[A-Za-z0-9]+", topic.lower())
    if not words:
        return "scenario"
    return "-".join(words[:8])


def create_seed_pack(
    *,
    topic: str,
    question: str,
    input_paths: Sequence[Path],
    symbols: Sequence[str],
    horizon: str,
    output_root: Path,
    as_of: str | None = None,
) -> SeedPackResult:
    topic = topic.strip()
    question = question.strip()
    if not topic:
        raise ValueError("topic is required")
    if not question:
        raise ValueError("question is required")

    as_of_date = as_of or date.today().isoformat()
    topic_slug = slugify_topic(topic)
    run_dir = output_root / f"{as_of_date}_{topic_slug}"
    run_dir.mkdir(parents=True, exist_ok=True)

    inputs = _read_inputs(input_paths)
    privacy_warnings = _detect_privacy_warnings(inputs)

    seed_path = run_dir / "seed.md"
    scenario_path = run_dir / "scenario.json"
    summary_path = run_dir / "summary_for_cucina.md"

    seed_path.write_text(
        _render_seed_markdown(
            topic=topic,
            question=question,
            inputs=inputs,
            symbols=symbols,
            horizon=horizon,
            as_of=as_of_date,
            privacy_warnings=privacy_warnings,
        ),
        encoding="utf-8",
    )

    scenario_path.write_text(
        json.dumps(
            {
                "schema_version": 1,
                "generated_at": datetime.now(timezone.utc).isoformat(),
                "as_of": as_of_date,
                "topic": topic,
                "topic_slug": topic_slug,
                "question": question,
                "symbols": [s.upper() for s in symbols],
                "horizon": horizon,
                "privacy_level": "sanitized_by_default",
                "privacy_warnings": privacy_warnings,
                "input_files": [
                    {
                        "name": item["name"],
                        "path": item["path"],
                        "bytes": len(item["content"].encode("utf-8")),
                    }
                    for item in inputs
                ],
                "output_contract": [
                    "facts remain sourced in Cucina",
                    "MiroFish output is simulation inference only",
                    "no unconditional trading instructions",
                    "include triggers and falsification conditions",
                ],
            },
            ensure_ascii=False,
            indent=2,
        ),
        encoding="utf-8",
    )

    summary_path.write_text(
        _render_summary_markdown(topic=topic, question=question, as_of=as_of_date),
        encoding="utf-8",
    )

    return SeedPackResult(
        run_dir=run_dir,
        seed_path=seed_path,
        scenario_path=scenario_path,
        summary_path=summary_path,
    )


def import_report(*, run_dir: Path, report_path: Path, as_of: str | None = None) -> Path:
    if not run_dir.exists():
        raise FileNotFoundError(f"run_dir does not exist: {run_dir}")
    if not report_path.exists():
        raise FileNotFoundError(f"report_path does not exist: {report_path}")

    as_of_date = as_of or date.today().isoformat()
    imported_path = run_dir / "mirofish_report.md"
    shutil.copyfile(report_path, imported_path)

    summary_path = run_dir / "summary_for_cucina.md"
    if summary_path.exists():
        summary = summary_path.read_text(encoding="utf-8")
    else:
        summary = _render_summary_markdown(
            topic=run_dir.name,
            question="MiroFish report imported without local seed metadata.",
            as_of=as_of_date,
        )

    import_note = (
        "\n## MiroFish 报告导入\n\n"
        f"- as-of: {as_of_date}\n"
        "- 报告文件: `mirofish_report.md`\n"
        "- 使用边界: 报告内容只能作为模拟推断/推测,不能作为无条件交易指令。\n"
    )
    summary_path.write_text(summary.rstrip() + "\n" + import_note, encoding="utf-8")

    return imported_path


def _read_inputs(input_paths: Sequence[Path]) -> list[dict[str, str]]:
    inputs: list[dict[str, str]] = []
    for raw_path in input_paths:
        path = Path(raw_path)
        if not path.exists():
            raise FileNotFoundError(f"input file does not exist: {path}")
        content = path.read_text(encoding="utf-8", errors="replace")
        inputs.append(
            {
                "name": path.name,
                "path": str(path),
                "content": content,
            }
        )
    return inputs


def _detect_privacy_warnings(inputs: Iterable[dict[str, str]]) -> list[str]:
    warnings: list[str] = []
    for item in inputs:
        for line_number, line in enumerate(item["content"].splitlines(), start=1):
            match = SECRET_PATTERN.search(line)
            if match:
                warnings.append(
                    f"{item['name']}:{line_number} contains possible secret marker {match.group(0)}"
                )
    return warnings


def _render_seed_markdown(
    *,
    topic: str,
    question: str,
    inputs: Sequence[dict[str, str]],
    symbols: Sequence[str],
    horizon: str,
    as_of: str,
    privacy_warnings: Sequence[str],
) -> str:
    symbol_text = ", ".join(s.upper() for s in symbols) if symbols else "未指定"
    sections = [
        f"# MiroFish Simulation Seed | {topic}",
        "",
        f"- as-of: {as_of}",
        f"- 标的/主题: {symbol_text}",
        f"- 推演窗口: {horizon}",
        "",
        "## 使用边界",
        "",
        "- 本材料仅用于研究、复核和情景推演。",
        "- MiroFish 输出只能作为模拟推断/推测,必须回到 Cucina 中与行情、公告、财报、宏观数据交叉验证。",
        "- 任何输出都不是交易指令,不得写成无条件买入、卖出、止盈、止损或对冲命令。",
        "- 不允许把券商账号、订单、精确成本、精确资产、API Key、token 或私钥上传到外部系统。",
        "",
        "## 投研问题",
        "",
        question,
        "",
        "## 隐私检查",
        "",
    ]

    if privacy_warnings:
        sections.extend(f"- WARNING: {warning}" for warning in privacy_warnings)
    else:
        sections.append("- 未发现明显密钥字段。仍需人工复核输入材料是否已脱敏。")

    sections.extend(
        [
            "",
            "## 输入材料",
            "",
        ]
    )
    if inputs:
        for index, item in enumerate(inputs, start=1):
            sections.extend(
                [
                    f"### {index}. {item['name']}",
                    "",
                    f"- source_path: `{item['path']}`",
                    "",
                    "```text",
                    item["content"].rstrip(),
                    "```",
                    "",
                ]
            )
    else:
        sections.extend(["- 未提供外部输入文件。", ""])

    sections.extend(
        [
            "## 给 MiroFish 的仿真提示词",
            "",
            "请基于上述种子材料构建图谱和多智能体仿真环境,围绕投研问题输出情景报告。",
            "报告必须区分:已证实事实、模拟推断、推测假设、关键触发条件、证伪条件和主要风险。",
            "不要输出无条件交易指令;涉及仓位动作时只写成由用户自行复核和执行的情景预案。",
            "",
        ]
    )
    return "\n".join(sections)


def _render_summary_markdown(*, topic: str, question: str, as_of: str) -> str:
    return "\n".join(
        [
            f"# MiroFish 情景推演摘要 | {topic}",
            "",
            f"- as-of: {as_of}",
            "- seed: `seed.md`",
            "- scenario: `scenario.json`",
            "- report: 尚未导入",
            "",
            "## 0. 使用边界",
            "",
            "本摘要只承接 MiroFish 的模拟推断/推测,不能替代 Cucina 的事实核验,也不是持牌投顾建议或交易指令。",
            "",
            "## 1. 投研问题",
            "",
            question,
            "",
            "## 2. 已证实事实",
            "",
            "- 等待从 Cucina 已验证数据源补充。",
            "",
            "## 3. 模拟推断",
            "",
            "- 等待导入 MiroFish 报告后提炼。",
            "",
            "## 4. 推测假设",
            "",
            "- 等待导入 MiroFish 报告后提炼。",
            "",
            "## 5. 触发条件",
            "",
            "- 等待导入 MiroFish 报告后提炼。",
            "",
            "## 6. 证伪条件",
            "",
            "- 等待导入 MiroFish 报告后提炼。",
            "",
            "## 7. 风险声明",
            "",
            "以上为研究分析与信息整理,不是持牌投顾建议;交易需用户自行核实和决策。",
            "",
        ]
    )


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description="Create and import Cucina/MiroFish simulation bridge files."
    )
    subparsers = parser.add_subparsers(dest="command", required=True)

    seed = subparsers.add_parser("seed", help="create a sanitized MiroFish seed pack")
    seed.add_argument("--topic", required=True)
    seed.add_argument("--question", required=True)
    seed.add_argument("--input", action="append", default=[], dest="inputs")
    seed.add_argument("--symbol", action="append", default=[], dest="symbols")
    seed.add_argument("--horizon", default="1-2 weeks")
    seed.add_argument("--as-of", default=None)
    seed.add_argument("--output-root", default="output/simulations")

    import_cmd = subparsers.add_parser(
        "import-report", help="import a MiroFish markdown report into a run directory"
    )
    import_cmd.add_argument("--run-dir", required=True)
    import_cmd.add_argument("--report", required=True)
    import_cmd.add_argument("--as-of", default=None)

    return parser


def main(argv: Sequence[str] | None = None) -> int:
    parser = build_parser()
    args = parser.parse_args(argv)

    if args.command == "seed":
        result = create_seed_pack(
            topic=args.topic,
            question=args.question,
            input_paths=[Path(p) for p in args.inputs],
            symbols=args.symbols,
            horizon=args.horizon,
            output_root=Path(args.output_root),
            as_of=args.as_of,
        )
        scenario = json.loads(result.scenario_path.read_text(encoding="utf-8"))
        print(f"seed_pack={result.run_dir}")
        if scenario["privacy_warnings"]:
            print("privacy_warnings:")
            for warning in scenario["privacy_warnings"]:
                print(f"- {warning}")
        return 0

    if args.command == "import-report":
        imported = import_report(
            run_dir=Path(args.run_dir),
            report_path=Path(args.report),
            as_of=args.as_of,
        )
        print(f"imported_report={imported}")
        return 0

    parser.error(f"unknown command: {args.command}")
    return 2


if __name__ == "__main__":
    raise SystemExit(main())
