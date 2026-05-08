# diego-research: Implementation Notes

## Constraints discovered through testing

### delegate_task recursion is forbidden
`delegate_task` cannot call `delegate_task`. Any recursive pattern (spin-offs, nested agents)
**must** use `execute_code` as the execution vehicle — it has no 600s timeout.

Workaround: implement spin-off loop in FASE 9 using `execute_code` to run the mini-research
FASE 1-6 internally, not inside the delegate_task prompt.

### Célula Dialéctica timeout floor
Measured during functional test (May 2026):
- Evangelista (3 facts): ~15s
- Inquisidor (3 facts): ~84s (slowest)
- Mediador (3 facts): ~38s
- **Total Célula Dialéctica on 3+3 facts: ~138s** — acceptable

Scope rule: keep at 3+3 (not 5+5) to stay safely under 600s delegate_task limit.
More than 6 facts → prioritize by Jaccard entropy score (higher novelty = more valuable).

### Parallel search performance
4 web_search calls in parallel: **4.6s** (vs ~20s sequential). Anthropic's pattern holds.

## Spin-off loop design decisions

| Decision | Choice | Reason |
|----------|--------|--------|
| Execution vehicle | `execute_code` | No 600s timeout; `delegate_task` recursion forbidden |
| max_depth | 2 | depth=0 main research + depth=1 spin-offs only |
| max_spin_offs per level | 3 | Cost control |
| Topic dedup threshold | Jaccard > 0.6 | Avoid near-duplicate research topics |
| Spin-off scope | FASE 1-6 only | No separate report; insights merge into main report |
| State persistence | `research_state.json` | Tracks pending/already-researched topics across depth |

## Patterns from Anthropic multi-agent research

1. **Lead agent (MiniMax) orchestrates; subagents (DeepSeek v4 Flash) execute specialized tasks** — same pattern as Claude Opus 4 / Sonnet 4 split
2. **Parallel tool calls cut time 90%** — confirmed in our test: 4.6s vs ~20s sequential
3. **Outcome-based evaluation** — the report quality (not adherence to process) is what matters
4. **Flexible depth scaling** — quick (4 queries) vs deep (10 queries) adapts to query complexity
5. **Async execution prevents bottlenecks** — parallel delegate_task for the 3 dialectic roles

## Test artifact locations

- `facts/atomic_facts.jsonl` — accumulated atomic facts (append-only, survives sessions)
- `facts/atomic_facts.jsonl.bak.<timestamp>` — backups before test runs
- `facts/research_state.json` — spin-off loop state (created by FASE 9)
- `output/YYYY-MM-DD-[topic].md` — research reports
