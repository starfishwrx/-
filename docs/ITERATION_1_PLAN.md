# Iteration 1 Plan: Fenxi + 505 Extension

## Goal
- Keep current 870 local flow stable.
- Add Fenxi backend metrics (new, active, member) and 505 recharge outputs.
- Generate two 505 images in the exact agreed table style.

## Non-Goals
- No automatic re-login loop in this iteration.
- No browser automation for auth refresh in this iteration.

## Strategy
- Isolate auth state from data logic.
- Validate each endpoint with a tiny preflight request before full pipeline.
- Build output in small vertical slices and integrate only after each slice passes.

## Work Breakdown

### Phase 1: Auth Isolation (manual cookie mode)
- Input source:
  - `extra_auth.json` (or env var fallback) for Fenxi/505 cookies and tokens.
  - `hosts_870.yaml` and `hosts_505.yaml` for host routing/proxy.
- Deliverables:
  - Single auth loader that returns request headers/cookies for each backend.
  - Preflight check command (per backend) with clear pass/fail logs.
- Done when:
  - Preflight passes for Fenxi and 505 on the same day without re-login.

### Phase 2: Fenxi Data Fetch (3 blocks)
- Blocks:
  - New users
  - Active users
  - Member metrics (including paid rate, recharge amount, valid members)
- Deliverables:
  - Unified normalized schema in code (`date`, `metric_key`, `value`).
  - Strict field mapping from endpoint response to report fields.
- Done when:
  - Numbers match manual backend check for one target date.

### Phase 3: 505 Recharge Data Fetch
- Blocks:
  - Web-game recharge list and compare column.
  - Mobile-game recharge list with dual-date layout.
- Deliverables:
  - Stable parser for both lists.
  - Date pair support (`today` vs `last_week_same_day`).
- Done when:
  - Totals and per-game rows match backend exports for one target date.

### Phase 4: 505 Image Rendering (strict style)
- Deliverables:
  - Image A: 4-column comparison table with positive/negative color rules.
  - Image B: side-by-side mobile list table with summary rows.
  - Fixed canvas size, header colors, border width, row height, font sizing.
- Done when:
  - Visual output matches sample style and layout constraints.

### Phase 5: Integration into Daily Report
- Deliverables:
  - End-to-end command generates markdown + 505 images in `output/`.
  - Failure isolation: if one backend fails, report marks section as unavailable.
- Done when:
  - Full run succeeds for `2026-02-20` and outputs complete artifacts.

## Quality Gates
- Functional:
  - `python -m py_compile` passes on changed modules.
  - One smoke run for a fixed date completes end-to-end.
- Data:
  - Key totals manually verified against backend UI.
- Safety:
  - No sensitive values committed (`config.yaml`, `*.har`, auth json).

## Branch and Commit Policy
- Branch: `codex/iter1-extra-metrics-505-charts`
- Commit by phase; one intent per commit.
- Keep `main` releasable at all times.
