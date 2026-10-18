# Project 4 — Troubleshooting

## banking-api MCP not reachable in Phase 1

- Confirm `python mcp_servers/banking_api/server.py` is running in a second terminal (leave it running).
- `curl -s -o /dev/null -w "%{http_code}" -H "X-API-Key: $BANKING_MCP_API_KEY" http://localhost:8080/sse` should return non-000, not 401.

## Sub-agent outputs disagree on the data model

- This is expected to happen occasionally — that's what the Phase 2 coordination pass is for.
- Re-prompt the `code-writer` sub-agent explicitly: "Use the exact field names {screened, match_list, confidence} agreed in docs/sanctions_screening_design.md."

## `tests/test_sanctions_check.py` fails to import `sanctions_check`

- Run pytest from the same directory as `sanctions_check.py` (repo root / `workspace/`), or add the root to `PYTHONPATH`.

## `/security-review` not found

- Confirm bootstrap copied `.claude/commands/security-review.md`. If you customised `.claude/` manually, re-run bootstrap or copy `starter_files/security-review-command.md` to `.claude/commands/security-review.md` yourself.

## Bandit hook not firing on `sanctions_check.py`

- Restart `claude` after editing `.claude/settings.json`.
- `chmod +x scripts/hooks/*.sh`
- PostToolUse matcher must include `Write|Edit|MultiEdit`.

## GitHub MCP 401/403 in Phase 4

- Regenerate PAT with `repo` + `workflow` scopes.
- Use `${GITHUB_PERSONAL_ACCESS_TOKEN}` in `.mcp.json` — never hardcode.

## CI workflow never triggers

- Workflow must be on the default branch or a feature branch with an open PR to `main`.
- Check the `paths:` filter includes `sanctions_check.py` / `.py` changes.
- `OPENROUTER_API_KEY` secret must exist in repo Settings → Actions.

## compliance-scoring score 0

- Headless `claude` failed — check the Actions log for auth errors.
- Verify `ANTHROPIC_API_KEY=""` in the workflow env block.

## `validate_p4.py` fails

Run from the project root:
```bash
python starter_files/validate_p4.py
```
Default checks `workspace/`.
