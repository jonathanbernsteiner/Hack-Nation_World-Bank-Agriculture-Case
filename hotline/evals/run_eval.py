"""Run an eval set through the pipeline and score it (spec section 9).

    cd hotline && uv run python evals/run_eval.py dev [--limit N] [--max-cost USD] [--yes]

Loads evals/<set>/*.json, runs hotline.pipeline.run.run_call on each call (live Anthropic calls,
needs ANTHROPIC_API_KEY), scores with score.py and writes results/<set>/<prompt_sha>.json plus a
markdown summary next to it. The summary and the error table carry no transcript, gold or
prediction strings, so they are safe to show the prompt author for unseen sets.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import sys
from datetime import date
from pathlib import Path

EVALS_DIR = Path(__file__).resolve().parent
sys.path.insert(0, str(EVALS_DIR))
PROMPTS_DIR = EVALS_DIR.parent / "hotline" / "prompts"
EST_COST_PER_CALL_USD = 0.60  # translate + extract on Opus 5.5, one short call; a rough ceiling
DEFAULT_MAX_COST_USD = 8.0  # one full set of 10 at the rough estimate, with headroom
TOTAL_COST_CAP_USD = 60.0  # spec section 9 cost cap, all rounds together
SHA_LEN = 12
TOOL_TO_IDENTIFIED_BY = {
    "identify_farmer": "pin",
    "find_farmer_by_location": "location",
    "register_farmer": "registration",
}


def prompt_sha(prompts_dir: Path = PROMPTS_DIR) -> str:
    """Hash of every prompt file the pipeline reads, so a result is tied to one prompt state."""
    digest = hashlib.sha256()
    for path in sorted(prompts_dir.glob("*.md")):
        digest.update(path.name.encode())
        digest.update(path.read_bytes())
    return digest.hexdigest()[:SHA_LEN]


def load_set(set_name: str, limit: int | None = None, base: Path = EVALS_DIR) -> list[dict]:
    folder = base / set_name
    files = sorted(folder.glob("*.json"))
    if not files:
        raise FileNotFoundError(f"no calls found in {folder}")
    calls = [json.loads(p.read_text(encoding="utf-8")) for p in files]
    return calls[:limit] if limit else calls


def identified_by(conversation: dict) -> str | None:
    for turn in conversation.get("transcript") or []:
        for call in turn.get("tool_calls") or []:
            if call.get("tool_name") in TOOL_TO_IDENTIFIED_BY:
                return TOOL_TO_IDENTIFIED_BY[call["tool_name"]]
    return None


def check_cost(n_calls: int, max_cost: float, spent_before: float) -> float:
    estimate = n_calls * EST_COST_PER_CALL_USD
    if estimate > max_cost:
        raise SystemExit(f"estimated cost ${estimate:.2f} for {n_calls} calls exceeds --max-cost ${max_cost:.2f}")
    if spent_before + estimate > TOTAL_COST_CAP_USD:
        raise SystemExit(f"estimate ${estimate:.2f} plus ${spent_before:.2f} already spent passes the ${TOTAL_COST_CAP_USD:.0f} cap")
    return estimate


def run_one(call: dict) -> dict:
    from hotline.pipeline.run import run_call
    from hotline.pipeline.transcript import scrub_tool_results, to_lines

    import score

    conversation = call["conversation"]
    try:
        result = run_call(
            to_lines(conversation),
            date.fromisoformat(call["call_date"]),
            tool_results=scrub_tool_results(conversation),
            identified_by=identified_by(conversation),
        )
        consent, entries, lines_en = result.consent, list(result.entries), result.lines_en
        error = None
    except Exception as exc:  # one bad call must not stop the run; it scores as all wrong
        consent, entries, lines_en, error = None, [], [], type(exc).__name__
    call_score = score.score_call(call, consent, entries, lines_en)
    return {"id": call["id"], "error": error, "score": call_score, "consent": consent, "entries": entries}


def render_summary(set_name: str, sha: str, summary: dict, per_call: list[dict]) -> str:
    p = summary["pass"]
    lines = [
        f"# Eval {set_name} @ {sha}",
        "",
        f"- Calls: {summary['calls']}",
        f"- Field accuracy: {summary['field_accuracy']:.3f} ({summary['fields_correct']}/{summary['fields_total']}), need 0.95: {'ok' if p['field_accuracy'] else 'FAIL'}",
        f"- Phantom sales: {summary['phantom_sales']}, need 0: {'ok' if p['zero_phantom_sales'] else 'FAIL'}",
        f"- Quote validity: {summary['quote_validity']:.3f} ({summary['quotes_valid']}/{summary['quotes_total']}), need 0.95: {'ok' if p['quote_validity'] else 'FAIL'}",
        f"- Overall: {'PASS' if summary['passed'] else 'FAIL'}",
        "",
        "## Errors by dimension",
        "",
        "| kind | field | error type | count |",
        "|---|---|---|---|",
    ]
    lines += [
        f"| {r['kind']} | {r['field']} | {r['error_type']} | {r['count']} |"
        for r in summary["error_table"]["by_dimension"]
    ]
    lines += ["", "## Calls with errors", ""]
    for row in per_call:
        n = len(row["errors"])
        if n or row["pipeline_error"]:
            lines.append(f"- {row['id']}: {n} wrong fields, phantom sales {row['phantom_sales']}"
                         + (f", pipeline error {row['pipeline_error']}" if row["pipeline_error"] else ""))
    return "\n".join(lines) + "\n"


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    ap.add_argument("set_name", help="folder under evals/, e.g. dev")
    ap.add_argument("--limit", type=int, default=None, help="run only the first N calls")
    ap.add_argument("--max-cost", type=float, default=DEFAULT_MAX_COST_USD, help="refuse if the estimate is higher (USD)")
    ap.add_argument("--yes", action="store_true", help="skip the confirmation prompt")
    args = ap.parse_args(argv)

    import score

    calls = load_set(args.set_name, args.limit)
    sha = prompt_sha()
    out_dir = EVALS_DIR / "results" / args.set_name
    ledger = EVALS_DIR / "results" / "spent.json"
    spent = json.loads(ledger.read_text())["usd"] if ledger.exists() else 0.0
    estimate = check_cost(len(calls), args.max_cost, spent)
    if not args.yes and input(f"{len(calls)} live calls, about ${estimate:.2f}. Continue? [y/N] ").lower() != "y":
        return 1

    rows = [run_one(c) for c in calls]
    scores = [r["score"] for r in rows]
    summary = score.summarise(scores)
    per_call = [
        {"id": r["id"], "pipeline_error": r["error"], "phantom_sales": r["score"].phantom_sales,
         "errors": [list(e) for e in r["score"].errors]}
        for r in rows
    ]
    out_dir.mkdir(parents=True, exist_ok=True)
    (out_dir / f"{sha}.json").write_text(
        json.dumps({"set": args.set_name, "prompt_sha": sha, "summary": summary, "calls": per_call}, indent=2) + "\n"
    )
    (out_dir / f"{sha}.md").write_text(render_summary(args.set_name, sha, summary, per_call))
    ledger.parent.mkdir(parents=True, exist_ok=True)
    ledger.write_text(json.dumps({"usd": round(spent + estimate, 2)}) + "\n")
    print((out_dir / f"{sha}.md").read_text())
    return 0 if summary["passed"] else 2


if __name__ == "__main__":
    raise SystemExit(main())
