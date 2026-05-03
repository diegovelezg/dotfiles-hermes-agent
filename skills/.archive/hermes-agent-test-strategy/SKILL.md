---
name: hermes-agent-test-strategy
description: Efficient way to run Hermes Agent tests after updating — avoids CI-parity timeouts
category: devops
---

# Hermes Agent Test Strategy

## Problem
Running `pytest tests/ -q` directly **times out** even with 300s timeout. The full suite (~15k tests) takes too long for a quick smoke test.

## Recommended Approach

### Quick verification after update (3 batches, ~75s total)

```bash
cd ~/.hermes/hermes-agent
source venv/bin/activate

# Batch 1: core infrastructure (265 tests, ~3s)
pytest tests/test_hermes_state.py tests/test_hermes_constants.py \
  tests/test_hermes_logging.py tests/test_base_url_hostname.py \
  tests/test_ipv4_preference.py -q --tb=short

# Batch 2: CLI integration (54 tests, ~3s)
pytest tests/test_cli_skin_integration.py tests/test_account_usage.py \
  tests/test_batch_runner_checkpoint.py tests/test_ctx_halving_fix.py -q --tb=short

# Batch 3: model/evidence (62 tests, ~3s)
pytest tests/test_minimax_model_validation.py tests/test_empty_model_fallback.py \
  tests/test_evidence_store.py tests/test_cli_file_drop.py -q --tb=short
```

### Full suite with early stop (preferred for CI)
```bash
pytest tests/ -q \
  --ignore=tests/test_mini_swe_runner.py \
  --ignore=tests/test_mcp_serve.py \
  --ignore=tests/test_minisweagent_path.py \
  -x --tb=line
```
This runs ~14k tests, stops at first failure, completes in ~70s.

### Known pre-existing failures (NOT caused by rebase)
These tests fail on `origin/main` and are unrelated to any local changes:
- `tests/agent/test_minimax_provider.py::TestMinimaxSwitchModelCredentialGuard::test_switch_to_minimax_does_not_resolve_anthropic_token` — `_fallback_chain` attribute mismatch with current codebase
- `tests/gateway/test_agent_cache.py::TestAgentCacheIdleResume::test_close_vs_release_full_teardown_difference` — LRU idle eviction timing/locking issue in suite

## Anti-patterns
- `pytest tests/ -q` with no flags — times out at 300s
- Running `scripts/run_tests.sh` for quick smoke tests (it's full CI-parity, slow)
- Calling `pytest` directly without activating venv — wrong Python version

## Why this works
- Hermes venv at `~/.hermes/hermes-agent/venv`
- Core tests (hermes_state, constants, logging) are fastest and catch most issues
- `-x` in full suite stops before time-consuming test modules like `test_mcp_serve.py`
