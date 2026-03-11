# Lessons Archive

Historical entries moved from `docs/lessons.md`.

## Entries

### [date] task
- pitfall:
- fix:
- prevention:
```

## Entries

### [2026-02-22] bootstrap lessons workflow
- pitfall: no repository-level workflow existed to force lesson review/writeback.
- fix: added `AGENTS.md` rules and initialized `docs/lessons.md`.
- prevention: keep this file updated after every completed task.

### [2026-02-22] scheduler hardening for daily Feishu delivery
- date: 2026-02-22
- task: add cross-platform scheduled-run entrypoints for report automation
- pitfall: direct cron/Task Scheduler wiring without locks, retries, and auth checks causes flaky pushes and silent failures.
- fix: add dedicated runner scripts with auth precheck, retry loop, per-run logs, and macOS launchd installer.
- prevention: always schedule a hardened wrapper script, not the raw report command.

### [2026-02-22] scheduler secret source consolidation
- date: 2026-02-22
- task: apply existing Feishu credentials to scheduler runtime
- pitfall: runtime jobs fail if secrets were only passed interactively in past runs.
- fix: store scheduler secrets in `.env.scheduler` (gitignored) and lock file permissions to user-only.
- prevention: for any unattended task, keep one persistent secret source and avoid ad-hoc CLI credential input.

### [2026-02-22] prompt-driven hardening and validation planning
- date: 2026-02-22
- task: design prompts and correctness checks for report hardening
- pitfall: feature work can loop without explicit pass/fail criteria and fixed test fixtures.
- fix: define phase prompts with required artifacts, golden outputs, and measurable acceptance gates.
- prevention: every implementation prompt must include: input fixtures, expected outputs, and machine-checkable validation commands.

### [2026-02-22] extra auth preflight gating
- date: 2026-02-22
- task: enforce fenxi/505 auth preflight before full extra-metrics report
- pitfall: report could finish with warnings while extra backend data silently missing, creating a false sense of completion.
- fix: run `preflight` in `--with-extra-metrics` flow and fail fast when either backend auth is invalid.
- prevention: any non-core backend marked as required must have a hard preflight gate before report rendering.

### [2026-02-22] feishu doc publish integration
- date: 2026-02-22
- task: add optional Feishu Doc publish after daily report generation
- pitfall: adding external push can break stable report flow when credentials are missing or API fails.
- fix: keep push feature opt-in (`--push-feishu-doc`), validate credentials only when enabled, and fail with explicit error message.
- prevention: all external integrations must be optional by default and have clear preflight-style configuration checks.

### [2026-02-22] feishu doc payload validation and fast push mode
- date: 2026-02-22
- task: stabilize Feishu Doc publish and avoid slow full reruns during debugging
- pitfall: auth response structure differs by endpoint and large block payloads can fail field validation.
- fix: parse tenant token from top-level response, batch doc blocks in small chunks, and add `--push-report-file` for fast push-only verification.
- prevention: for external APIs, validate response schema per endpoint and always add a minimal fast-path command for integration debugging.

### [2026-02-22] feishu rich-content push via placeholder image blocks
- date: 2026-02-22
- task: push report to Feishu with inline charts and table-style top section
- pitfall: plain text push drops images and markdown tables; direct image block create failed because token binding was wrong.
- fix: create image placeholders via `descendant` first, upload media with `parent_node=<image_block_id>`, then `replace_image`; render markdown table to PNG and upload as image block.
- prevention: for docx media workflows, always verify block-type counts through API (`block_type=27`) and ensure no placeholder/table text residues remain.

### [2026-02-22] reduce Feishu image whitespace with trim and adaptive width
- date: 2026-02-22
- task: reduce excessive vertical whitespace around report images in Feishu doc
- pitfall: fixed large image width plus retained blank text blocks caused oversized image areas and visible top/bottom gaps.
- fix: drop empty text blocks, auto-trim near-white image borders before upload, and apply adaptive width (default 900, tall/505 tables 760).
- prevention: validate pushed doc by API block metrics (image widths/heights + residue scan) before rerunning full report.

### [2026-02-22] upload_all compatibility with drive_route_token
- date: 2026-02-22
- task: harden Feishu media upload for docx image replacement
- pitfall: relying only on `parent_node` can trigger tenant-specific relation checks in some environments.
- fix: keep `parent_type=docx_image` + `parent_node=<image_block_id>` and add `extra={"drive_route_token":"<document_id>"}`.
- prevention: when using `upload_all` for docx media, include both precise upload point and route token to reduce environment-specific validation failures.

### [2026-02-22] post-publish content verification via docs v1 content
- date: 2026-02-22
- task: add optional Feishu doc markdown verification after publish
- pitfall: visual checks alone are slow and subjective, and regressions are easy to miss.
- fix: add `--verify-feishu-content` to call `GET /docs/v1/content` after publish and record markdown length in logs.
- prevention: every external publishing path should have a machine-checkable post-publish verification option.

### [2026-02-22] feishu image anti-distortion sizing
- date: 2026-02-22
- task: make Feishu report images match template scale and avoid deformation
- pitfall: default image width was too large and could upscale small source images, making charts look stretched/blurry.
- fix: lower default widths to `960/760`, add `prevent_upscale` behavior, and expose width controls in `feishu_doc` config.
- prevention: for document image rendering, always preserve source aspect ratio and block any default upscaling unless explicitly enabled.

### [2026-02-22] default-on feishu push and single-output flow
- date: 2026-02-22
- task: simplify main flow to Feishu-first output and remove html artifact generation
- pitfall: dual outputs (txt+html+feishu) increased branching and made daily usage unclear.
- fix: stop calling html generation in main flow, make Feishu push default-on, and add `--no-push-feishu-doc` as runtime escape hatch.
- prevention: keep one primary delivery channel by default; optional paths must be explicit opt-out or opt-in flags.

### [2026-02-24] harden Feishu push retries and expose PC push status
- date: 2026-02-24
- task: stabilize GUI full-run push where upload_all hits intermittent SSL EOF
- pitfall: transient TLS/connection failures aborted at main Feishu push, making PC push look unintegrated.
- fix: add retry/backoff for Feishu HTTP/media upload, split main+PC push attempts with aggregated errors, and parse both main/PC Feishu URLs in GUI/API logs.
- prevention: for external delivery steps, keep retryable transport errors isolated and ensure sub-report push stages are independently observable.

### [2026-02-24] avoid upload_all size mismatch with fresh file stream per retry
- date: 2026-02-24
- task: fix Feishu upload_all code=1062009 during full GUI run
- pitfall: retrying multipart upload on a reused file handle can send fewer bytes than declared size.
- fix: reopen image file for each upload attempt, keep declared size constant, and only retry on retryable transport/API errors.
- prevention: for multipart retries, never reuse a consumed file stream across attempts.

