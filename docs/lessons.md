# Lessons Learned
Purpose: capture repeatable pitfalls and prevention rules for future tasks.

## Template
Use this template for every new entry:

```md
### [2026-02-22] gui launcher with stage progress
- date: 2026-02-22
- task: provide click-to-run desktop launcher with progress bar and login shortcut
- pitfall: mixing multiple GUI prompts caused duplicated interactions and reduced reliability.
- fix: add `--no-runtime-gui` in core script, emit structured progress logs, and let dedicated launcher own the full interaction flow.
- prevention: when adding a dashboard GUI, centralize user interaction in one entrypoint and keep backend script headless-compatible.

### [2026-02-22] gui ergonomics and scheduler controls
- date: 2026-02-22
- task: improve launcher usability and add in-app scheduler operations
- pitfall: minimal form-style UI reduced clarity, and scheduler required external shell commands.
- fix: redesign launcher with card layout + styled log panel, and add scheduler buttons (install/update, trigger now, disable, refresh).
- prevention: for operational tools, include common daily actions directly in UI to avoid context switching to terminal.

### [2026-02-22] dual-package release with desensitized assets
- date: 2026-02-22
- task: package CLI+GUI releases and push sanitized repo update
- pitfall: local config/secrets can be accidentally bundled (for example by including `config.yaml` in PyInstaller data files).
- fix: package from `config.example.yaml` only, run explicit secret-pattern scans before commit, and produce timestamped release zips.
- prevention: treat packaging as a release gate: verify artifacts, verify no secret files in bundle, then push.

### [2026-02-23] fastapi service wrapper for report execution
- date: 2026-02-23
- task: expose report pipeline via FastAPI with job progress and cancellation
- pitfall: directly exposing raw command execution can cause concurrent job conflicts and uncontrolled memory growth in logs.
- fix: add a guarded in-memory job store (single active job), progress parsing from structured logs, bounded log retention, and cancel endpoint.
- prevention: when API-izing a batch script, always add concurrency guardrails, progress protocol, and bounded runtime state.

### [2026-02-23] fastapi boot verification
- date: 2026-02-23
- task: start FastAPI service and verify runtime health
- pitfall: background start without explicit health probe can leave false-positive “started” state.
- fix: start with nohup, persist pid/log file, and immediately validate `GET /health`.
- prevention: treat service startup as complete only after a successful health check response.

### [2026-02-23] stale pid cleanup before api restart
- date: 2026-02-23
- task: recover FastAPI when pid file exists but service is down
- pitfall: stale `output/fastapi.pid` can mislead status checks and block smooth restart.
- fix: validate pid liveness before trusting pid file, remove stale pid, then restart and probe health twice.
- prevention: always couple pid checks with port/health checks; never rely on pid file alone.

### [2026-02-22] swagger docs enrichment and restart verification
- date: 2026-02-22
- task: enrich FastAPI Swagger docs with examples and auth guidance
- pitfall: docs looked unchanged because an old process was still bound to port 8000.
- fix: killed the stale listener, restarted FastAPI from current workspace, and verified updated `/openapi.json` fields.
- prevention: after API doc edits, always validate the live process PID and confirm version/description changed in OpenAPI before reporting done.

### [2026-02-24] fenxi auth expiry diagnosis from runtime logs
- date: 2026-02-24
- task: identify why fenxi preflight started failing while 505 remained healthy
- pitfall: relying on stale `extra_auth.json` can pass for part of the day and then suddenly fail with 401 once fenxi token expires.
- fix: verify `extra_auth` age + decode `e_token` expiry and confirm with `--check-extra-auth` before full report run.
- prevention: enforce daily auth refresh after SMS login and run preflight check first; block full run when fenxi preflight is not ok.

### [2026-02-24] fenxi-only auth refresh without breaking 505
- date: 2026-02-24
- task: urgent refresh of fenxi auth from new HAR
- pitfall: full rebuild from only fenxi HAR can wipe 505 auth section in `extra_auth.json`.
- fix: backup file first, replace only `fenxi` block, keep existing `505`, then run `--check-extra-auth`.
- prevention: when only one platform auth is refreshed, do partial merge update instead of full overwrite.

### [2026-02-24] feishu doc default location without folder token
- date: 2026-02-24
- task: explain why pushed Feishu doc link is not visible in expected cloud folder
- pitfall: creating docx without `folder_token` makes the file land in the app identity default space, which can be hard to locate in personal cloud folders.
- fix: confirm code path only sets `folder_token` when configured, and document explicit folder-token configuration.
- prevention: always set `feishu_doc.folder_token` (or `FEISHU_DOC_FOLDER_TOKEN`) for stable, discoverable storage location.

### [2026-02-24] feishu sharing strategy after doc creation
- date: 2026-02-24
- task: answer whether reports can auto-share to all members
- pitfall: creating doc with link only does not guarantee visibility in target team space.
- fix: clarify current behavior and require either fixed shared folder token or explicit permission API step.
- prevention: define sharing policy (folder-based vs tenant-wide) before enabling automatic publish in production.

### [2026-02-24] feishu tenant auto-share with non-blocking fallback
- date: 2026-02-24
- task: add automatic tenant-wide sharing after report doc creation
- pitfall: permission API compatibility/authorization differs by tenant and can break report delivery if treated as hard failure.
- fix: add configurable auto-share (`read/edit`) with optional strict mode, default non-blocking and explicit status logs.
- prevention: keep sharing as a separable post-create step with clear logs and a strict switch for controlled rollout.

### [2026-02-24] feishu storage location clarification
- date: 2026-02-24
- task: clarify where pushed Feishu docs and images are stored
- pitfall: users may expect both doc and uploaded media to appear as separate files in cloud drive lists.
- fix: distinguish docx file storage (folder/default space) from doc-bound media behavior.
- prevention: always explain storage behavior with and without `folder_token` when enabling Feishu push.

### [2026-02-24] locating Feishu folder_token from folder URL
- date: 2026-02-24
- task: explain where to find folder_token for deterministic doc placement
- pitfall: users often copy document link instead of folder link, causing wrong token usage.
- fix: use cloud drive folder URL and extract token segment after `/drive/folder/`.
- prevention: validate token source before config update and confirm app has folder edit permission.

### [2026-02-24] apply folder token and sharing defaults in runtime config
- date: 2026-02-24
- task: configure Feishu folder target in production config
- pitfall: leaving folder/share settings only in docs can still route docs to default space at runtime.
- fix: set `feishu_doc.folder_token` directly in `config.yaml` and pair with non-strict tenant read sharing.
- prevention: after receiving a folder URL, persist token to runtime config and validate parsed YAML immediately.

### [2026-02-24] full-run blocked by expired 870 session cookie
- date: 2026-02-24
- task: execute full report after Feishu folder/share configuration
- pitfall: run can fail before extra metrics/push when 870 endpoint silently returns login-page HTML instead of JSON.
- fix: detect non-JSON login redirect snippet and treat as invalid session cookie; refresh 870 login first.
- prevention: run a lightweight 870 probe/check before full pipeline, and refresh `session_cookie` whenever probe returns HTML login content.

### [2026-02-24] feishu folder permission denial on doc create
- date: 2026-02-24
- task: troubleshoot Feishu publish failure code 1770040
- pitfall: valid folder token still fails if app identity lacks folder edit permission.
- fix: grant the Feishu app folder access via "添加文档应用" or folder share permissions, then retry push.
- prevention: whenever changing `folder_token`, verify app access on target folder before production run.

### [2026-02-24] rollback folder token when app lacks folder permission
- date: 2026-02-24
- task: restore Feishu push after folder permission failure
- pitfall: keeping unauthorized folder token blocks all pushes with code 1770040.
- fix: clear `feishu_doc.folder_token` to fall back to default space until folder permission is granted.
- prevention: use temporary no-folder fallback for urgent delivery, then re-enable folder token after app authorization.

### [2026-02-24] distinguish DNS failure from upstream 502 for cloud admin hosts
- date: 2026-02-24
- task: diagnose yapiadmin login failure
- pitfall: frontend 502 can be misread as credential/login issue when root cause is upstream gateway/backend outage.
- fix: test both DNS resolution and forced-host IP requests; confirm `stgw 502` persists even with `--resolve`.
- prevention: for admin host incidents, always run a two-step probe (DNS + forced IP HTTP status) before changing local auth or code.

### [2026-02-24] browser relogin does not refresh extra auth file automatically
- date: 2026-02-24
- task: explain whether fenxi relogin alone can recover morning auth expiry
- pitfall: users may relogin in browser but script still reads stale cookies from `extra_auth.json`.
- fix: after relogin, refresh auth material file (HAR -> extra_auth) before running preflight/full report.
- prevention: make `--check-extra-auth` a mandatory gate in daily runbook before report generation.

### [2026-02-24] compare fenxi HAR auth fields before deciding refresh strategy
- date: 2026-02-24
- task: verify whether latest fenxi login tokens changed vs prior HAR
- pitfall: assuming fenxi behaves like 870 can cause stale auth usage and morning failures.
- fix: compare key fields (`e_token` claims and `JSESSIONID`) between old/new HAR; refresh auth file when changed.
- prevention: treat fenxi auth as rotating; use HAR diff + preflight as standard daily check.

### [2026-02-24] ping reachable but service still unavailable
- date: 2026-02-24
- task: explain why yadmin can ping but still cannot log in
- pitfall: treating ICMP reachability as equivalent to HTTP application health.
- fix: verify with HTTPS status checks (for example `curl -I`) and inspect gateway/app status codes.
- prevention: use layered checks in order: DNS -> TCP/TLS -> HTTP status -> app login flow.

### [2026-02-24] cloud admin host protocol mismatch http vs https
- date: 2026-02-24
- task: diagnose why admin host seems reachable but browser shows errors
- pitfall: assuming https is available when backend is only reliably serving http in current environment.
- fix: verify both protocols explicitly; use `http://yadmin.4399.com` for console and `http://yapiadmin.4399.com` for API login checks.
- prevention: include protocol in runbook URLs and avoid browser auto-upgrade to https for these internal endpoints.

### [2026-02-24] yapiadmin failure can stack protocol and token issues
- date: 2026-02-24
- task: diagnose why yapiadmin still failed after host/IP checks
- pitfall: fixing https->http alone may still fail if oauth access_token is stale or unauthorized.
- fix: confirm https path returns 502, then test same oauth URL on http and inspect app-level JSON error (`status=-1 login failed`).
- prevention: validate in two layers for this backend: protocol first, then token/account validity.

### [2026-02-24] HAR evidence of local proxy interference and domain typo
- date: 2026-02-24
- task: analyze yapiadmin HAR where login still failed
- pitfall: troubleshooting can miss that browser traffic is routed through localhost proxy and even wrong domain (`yadmin.4399.co`) was opened.
- fix: read HAR `serverIPAddress`/`connection` fields (127.0.0.1:7890) and isolate direct access with correct domain.
- prevention: when web auth fails, first verify exact host suffix and disable/bypass local proxy for internal domains.

### [2026-02-24] windows forced https and proxy-induced 502 on internal admin host
- date: 2026-02-24
- task: explain why Windows browser upgrades to https while http works elsewhere
- pitfall: browser/proxy/security policies can auto-upgrade or redirect to https and hide true http availability.
- fix: disable forced-https behavior, bypass proxy for internal domains, and clear HSTS for affected host.
- prevention: keep dedicated browser profile for intranet admin sites with proxy bypass and no https-only enforcement.

### [2026-02-24] pc report metrics integration with auth fallback
- date: 2026-02-24
- task: add PC网页端新增/活跃/Top10 to pc日报
- pitfall: PC HAR often omits cookies, so direct `pc_web` auth can be empty and break data pull.
- fix: add `pc_web` auth slot but fallback to `505` cookies for yapiadmin requests; keep strict mode optional.
- prevention: for every new backend integration, implement auth fallback + preflight + non-blocking warning path before making it strict.

### [2026-02-24] pc member metrics via fenxi report 793
- date: 2026-02-24
- task: add PC会员指标到pc日报
- pitfall: PC会员数据不在 yapiadmin，而在 fenxi BI 报表组件（793），直接沿用 PC 接口会漏数。
- fix: 新增 fenxi 组件抓取（总金额/总订单数/首开会员总金额/首开会员数），并和 PC 新增活跃结果合并渲染。
- prevention: 新增指标前先在 HAR 中确认“数据来源域 + 组件ID + 字段ID”，再落代码，避免接口选错。

### [2026-02-24] split pc auth and run minimal offline verification
- date: 2026-02-24
- task: validate PC日报最小链路（不跑全量）
- pitfall: 在主链路未通（870过期）时做全量验证会混淆问题来源。
- fix: 先离线用 HAR 直验 PC 新增活跃 + 会员指标 + 模板渲染，再单独验证编译和鉴权分离逻辑。
- prevention: 对新增子模块先做“离线最小可证据验证”，通过后再接入全链路。

### [2026-02-24] align pc template first then standalone push
- date: 2026-02-24
- task: 对齐 PC 报告格式并单独推送飞书
- pitfall: 未对齐模板结构就推送，会把版式问题带到飞书文档里，回滚成本高。
- fix: 先离线渲染校验标题/段落顺序/表格，再用 `--push-report-file` 单独推送 PC 报告。
- prevention: 任何发布动作前，先做“模板一致性最小验证（本地文本 + 图片占位）”。

### [2026-02-24] codify pc feature checks with unittest
- date: 2026-02-24
- task: 为 PC 新增功能建立自动化测试
- pitfall: 仅靠人工预览容易漏掉模板细节和推送路径回归。
- fix: 新增 3 个 unittest 覆盖 PC 模板文案、PC 图片自动识别、PC 会员指标计算。
- prevention: 每次改 PC 模块后先跑 `python -m unittest discover -s tests -p 'test_*.py' -v`，通过后再做线上推送验证。

### [2026-02-24] convert pc notes into fixed two-line remark structure
- date: 2026-02-24
- task: 修正 PC 新增活跃与会员排版结构
- pitfall: 分散段落会和业务期望模板不一致，导致“数据对但版式错”。
- fix: 统一改为“备注”两条结构（新增+活跃一条、会员汇总一条）并保留 top 表。
- prevention: 模板变更后先用固定断言测试标题/小节/备注语句，再推飞书。

### [2026-02-24] pc member weekly ratio must not rely on first-row fallback
- date: 2026-02-24
- task: fix missing PC recharge week-over-week text in daily report
- pitfall: extracting single-day member amount by taking the first row can pick wrong date (or no comparable baseline), causing `暂无同比数据`.
- fix: normalize date keys, match single-value extraction by target day, and add trend-table override (`当前充值金额/对比充值金额/涨幅`) as a stronger source.
- prevention: for BI single-day metrics, enforce target-date matching plus fallback-source cross-check before rendering summary text.
```

## Entries

### [2026-02-24] browser-based auth refresh for fenxi and pc_web
- date: 2026-02-24
- task: reduce HAR dependency by auto-refreshing extension auth from local browser state
- pitfall: relying on HAR for every refresh is slow and error-prone, while pc_web needs exact Bearer token+chain.
- fix: add `browser_auth_refresh.py` to read browser cookies, refresh fenxi cookies, probe valid pc chain, and write `extra_auth.json`.
- prevention: make browser refresh + `--check-extra-auth` the default daily path, and keep HAR refresh as fallback only.

### [2026-02-24] atlas browser uses non-standard encrypted cookie store
- date: 2026-02-24
- task: support auth refresh for OpenAI Atlas (alts) browser users
- pitfall: standard browser auto-detection can miss atlas profile path or fail decryption without explicit cookie db hints.
- fix: add atlas-specific cookie-path probing (`com.openai.atlas/.../Cookies`) and expose `--cookie-file/--key-file` override.
- prevention: for non-standard Chromium builds, always provide explicit cookie-db fallback path in tooling and docs.

### [2026-02-24] pc web auth depends on exact bearer chain
- date: 2026-02-24
- task: diagnose whether pc_web login state needs fenxi-like frequent refresh
- pitfall: assuming cookie-only auth works causes false negatives; `Admin-Token` without matching `Bearer chain` returns permission errors.
- fix: verify with preflight experiments (header-only pass, cookie-only fail, wrong chain fail) and treat `Bearer(token+chain)` as the authoritative pc_web credential.
- prevention: always run `--check-extra-auth` before full run; if pc_web fails, refresh bearer source instead of only refreshing cookies.

### [2026-02-24] gui auth maintenance split by source reliability
- date: 2026-02-24
- task: add GUI actions for pc auto-refresh and fenxi HAR import
- pitfall: one-click full auth rebuild can accidentally wipe unaffected auth blocks and block daily run.
- fix: add `自动刷新PC登录态` (pc-only browser refresh) and `上传Fenxi HAR并更新` (fenxi-only merge update) as separate GUI actions.
- prevention: for multi-source auth, expose per-source refresh actions and never overwrite unrelated auth sections.

### [2026-02-24] atlas encrypted cookie fallback to pc HAR in GUI
- date: 2026-02-24
- task: fix repeated GUI failure when auto-refreshing PC auth from atlas cookies
- pitfall: atlas stores `Admin-Token` as encrypted cookie, so browser-cookie auto-read may fail even after successful login.
- fix: add explicit atlas encrypted-cookie diagnosis and provide GUI `上传PC HAR并更新` path to refresh `pc_web` auth without touching fenxi/505.
- prevention: when browser auto-refresh fails on non-standard clients, always ship a same-screen HAR import fallback instead of blocking the run.

### [2026-02-24] prefer gameStartData bearer over snapshot chain for pc auth
- date: 2026-02-24
- task: resolve pc_web preflight `status=-101 权限不足` after HAR import
- pitfall: selecting the last yapi bearer can capture `snapshotInfo` chain=0 instead of `gameStartData` chain=545, producing valid-looking but unauthorized auth.
- fix: update HAR extraction priority to `gameStartData` bearer first, then non-zero-chain yapi bearer, and sync `Admin-Token` to bearer token when mismatched.
- prevention: for multi-chain backends, bind auth extraction to the target business endpoint and reject/repair token mismatch in the same auth block.

### [2026-02-24] gui auto-recover with playwright and one-shot retry
- date: 2026-02-24
- task: continue report task automatically when auth expires mid-run
- pitfall: task stopped at first auth failure and required manual HAR workflow, causing repeated restart loops.
- fix: add GUI path to detect auth-like failures, run `auth_recovery_playwright.py` (popup phone/code + token capture), run `--check-extra-auth`, then retry the report once.
- prevention: for auth-dependent scheduled jobs, implement a bounded auto-recovery branch (single retry + explicit preflight gate) before surfacing hard failure.

### [2026-02-24] strengthen sms-login automation with tab/consent/request detection
- date: 2026-02-24
- task: fix Playwright auth recovery not triggering SMS send on login page
- pitfall: generic selector clicks can miss real SMS-login flow (wrong tab, unchecked consent, iframe field), so users input phone but no code is sent.
- fix: add multi-target interaction (page+frames), switch to SMS tab, attempt consent checkbox, click send-code button, and log whether SMS request traffic was detected.
- prevention: for login automation, always validate action success with network evidence (e.g., send-code request) and provide manual fallback guidance in logs.
