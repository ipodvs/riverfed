"""One-shot promotion pass — turn flagged candidates in log.md into pages.

Reads wiki/log.md for every "candidate", "patterns crystallizing", or
"watch for" item, then hands the whole wiki to Claude Code with the
explicit goal of:

- Creating concept pages (wiki/concepts/<slug>.md) for cross-cutting themes
  with enough sources of evidence (the model's `promote_after` knob —
  3 for the karpathy-wiki model).
- Creating entity pages for tools/people with multi-source coverage
  (`promote_after` 2) but no entity page yet.
- Updating index.md and topic pages to reference the new pages.
- Appending a single log.md entry describing what got promoted.

This is meant to be run *occasionally* (after several ingests have
accumulated a backlog). For routine new-transcript ingest, use
ingest.py — its prompt now handles the same promotion logic on a
per-source basis.
"""

from __future__ import annotations

import argparse
import subprocess
import sys
from pathlib import Path

# Make sure stdout can handle UTF-8 (Claude's stream contains arrows etc.).
for _stream in (sys.stdout, sys.stderr):
    try:
        _stream.reconfigure(encoding="utf-8", errors="replace")  # type: ignore[attr-defined]
    except Exception:
        pass

sys.path.insert(0, str(Path(__file__).resolve().parent))
from _wikis import PROJECT_DIR, Vault, display_path, resolve_vault  # noqa: E402
import agent_runner  # noqa: E402
from model_registry import KnowledgeModel, load_model_for_vault  # noqa: E402

OBSIDIAN_PASS = Path(__file__).resolve().parent / "obsidian_pass.py"

NO_WINDOW = getattr(subprocess, "CREATE_NO_WINDOW", 0) if sys.platform == "win32" else 0


# The promotion prompt template lives with the vault's knowledge model
# (models/<id>/promote-prompt.md) — placeholders {wiki_rel}, {output_rel},
# {wiki_slug} + the model's promote_after knobs, so the prompt states the
# ACTUAL promotion thresholds instead of folklore.


def run_promotion(vault: Vault, model: KnowledgeModel,
                  provider: str = agent_runner.DEFAULT_PROVIDER) -> int:
    if not agent_runner.resolve_agent_bin(provider):
        sys.stderr.write(f"Error: {provider} CLI not found on PATH\n")
        return 2

    prompt = model.promote_prompt().format(
        wiki_rel=display_path(vault.root),
        output_rel=display_path(vault.output),
        wiki_slug=vault.slug,
        **model.prompt_format_args(),
    )

    def _echo(line: str) -> None:
        print(f"  {line}")
        sys.stdout.flush()

    print(f"Running backlog promotion pass via "
          f"{agent_runner.CMD_LABELS[provider]} ...")
    res = agent_runner.run(
        prompt,
        cwd=PROJECT_DIR,
        timeout=3600,
        add_dirs=[vault.root, vault.output],
        allowed_tools="Read,Write,Edit,Glob,Grep,Bash,TodoWrite",
        on_line=_echo,
        provider=provider,
    )
    if res.timed_out:
        sys.stderr.write(f"Error: promotion pass {res.error}\n")
        return 1
    rc = res.returncode
    print(f"\nPromotion pass exit {rc} in {res.elapsed_seconds:.1f}s")

    if OBSIDIAN_PASS.exists():
        print("\nRunning obsidian_pass.py...")
        subprocess.run(
            [sys.executable, str(OBSIDIAN_PASS), "--wiki", vault.slug],
            stdin=subprocess.DEVNULL,
            cwd=str(PROJECT_DIR), timeout=120,
            creationflags=NO_WINDOW,
        )
    return rc


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(
        description="Promote flagged log.md candidates into wiki pages.")
    parser.add_argument("--wiki", default="wiki",
                        help="Knowledge-base slug ('wiki' = the original vault).")
    parser.add_argument("--provider", default="auto",
                        choices=["auto", *agent_runner.PROVIDERS],
                        help=agent_runner.provider_arg_help(
                            "run the promotion on"))
    args = parser.parse_args(argv)

    vault = resolve_vault(args.wiki)
    if vault is None or not vault.exists():
        sys.stderr.write(f"Knowledge base '{args.wiki}' not found.\n")
        return 1
    try:
        model = load_model_for_vault(vault)
    except (FileNotFoundError, ValueError) as exc:
        sys.stderr.write(f"ERROR: {exc}\n")
        return 1
    provider, pstatus = agent_runner.resolve_provider(args.provider)
    if provider is None:
        sys.stderr.write(f"ERROR: {agent_runner.unavailable_message(pstatus)}\n")
        return 2
    vault.output.mkdir(parents=True, exist_ok=True)
    return run_promotion(vault, model, provider)


if __name__ == "__main__":
    sys.exit(main())
