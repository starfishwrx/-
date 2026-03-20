# AGENTS.md

## Scope

These notes apply to the `autodatareport` repository.

## Repository Reality

- The stable branch is `main`.
- Old Codex branches such as `codex/qw`, `codex/deta3`, and `codex/aiproblem` may exist locally and can lag behind `main`.
- Before debugging GUI regressions or missing files, confirm the workspace is actually on `main`.

Recommended check:

```bash
git status --short --branch
git branch -vv
```

If the workspace is on an old Codex branch and GUI/auth helper files appear to be missing, switch back to `main` before deeper debugging:

```bash
git switch main
```

## Default Operating Rule

- Treat every full report run as gated by auth preflight.
- Do not run the full report if `--check-extra-auth` fails.
- Prefer the smallest operation that satisfies the request:
  - preflight only
  - auth refresh only
  - push-only
  - full rerun

## Canonical Run Commands

### Full preflight

```bash
./.venv/bin/python generate_daily_report.py --config config.yaml --date 2026-03-11 --no-runtime-gui --check-extra-auth
```

### Full daily run

```bash
./.venv/bin/python generate_daily_report.py --config config.yaml --date 2026-03-11 --no-runtime-gui --with-extra-metrics
```

### Main report Feishu push-only

```bash
./.venv/bin/python generate_daily_report.py \
  --config config.yaml \
  --date 2026-03-11 \
  --no-runtime-gui \
  --push-report-file ./output/2026311_report.txt
```

### PC report Feishu push-only

```bash
./.venv/bin/python generate_daily_report.py \
  --config config.yaml \
  --date 2026-03-11 \
  --no-runtime-gui \
  --push-pc-report-file ./output/2026311_pc_report.txt
```

### WeCom push-only

This path republishes Feishu docs first, then pushes Feishu links to WeCom.

```bash
./.venv/bin/python generate_daily_report.py \
  --config config.yaml \
  --date 2026-03-11 \
  --no-runtime-gui \
  --push-wecom-reports \
  --wecom-target single
```

Valid `--wecom-target` values:

- `single`
- `group`

## Auth Maintenance

### Browser-based refresh

Preferred for `pc_web`; can also refresh `fenxi` if the browser exposes the right cookies.

```bash
./.venv/bin/python browser_auth_refresh.py \
  --browser atlas \
  --extra-auth-file ./extra_auth.json \
  --output ./extra_auth.json \
  --hosts-yaml-path ./hosts_505.yaml
```

### PC-only browser refresh

```bash
./.venv/bin/python browser_auth_refresh.py \
  --browser atlas \
  --pc-only \
  --extra-auth-file ./extra_auth.json \
  --output ./extra_auth.json \
  --hosts-yaml-path ./hosts_505.yaml
```

### Fenxi HAR merge refresh

```bash
./.venv/bin/python fenxi_auth_from_har.py \
  --extra-auth-file ./extra_auth.json \
  --output ./extra_auth.json \
  --fenxi-har "/path/to/fenxi.har"
```

### PC HAR merge refresh

```bash
./.venv/bin/python pc_auth_from_har.py \
  --extra-auth-file ./extra_auth.json \
  --output ./extra_auth.json \
  --pc-har "/path/to/pc.har"
```

### Interactive browser recovery

Use only when preflight failed and browser extraction/HAR merge is not enough.

```bash
./.venv/bin/python auth_recovery_playwright.py \
  --extra-auth-file ./extra_auth.json \
  --output ./extra_auth.json \
  --pc-login-url "http://yadmin.4399.com/" \
  --fenxi-url "https://fenxi.4399dev.com/analysis/" \
  --timeout-seconds 300 \
  --ask-sms
```

## Known Auth Constraints

- `870` failure usually appears as HTML login redirect instead of JSON. Treat that as expired `session_cookie`.
- `fenxi` uses `e_token` with real expiry. A fresh login may be required; heartbeat is not a real fix.
- `pc_web` requires more than one signal:
  - `Admin-Token`
  - `Bearer`
  - correct `chain`
- A token being present is not enough. It still must pass preflight.

## GUI Reality

- The desktop launcher should point to the source GUI:
  - `scripts/start_gui.command` on macOS
  - `scripts/start_gui.bat` on Windows
- If buttons appear to be missing, first confirm the workspace is on `main`.
- The expected source GUI includes:
  - open 870 login
  - run task
  - stop task
  - open main Feishu doc
  - open PC Feishu doc
  - refresh PC auth
  - import PC HAR
  - import Fenxi HAR

## WeCom Delivery Rules

- WeCom delivery is link-based, not image-based.
- The active flow is:
  1. publish Feishu docs
  2. push Feishu doc links to WeCom
- Direct image push via WeCom long-bot active send was rejected by the platform with `invalid message type`.
- Auto targets are controlled by `config.yaml -> wecom_bot.auto_targets`.

## Packaging

### Windows

- Build on Windows, not macOS.
- Current `build_exe.bat` runs `pyinstaller --clean build_exe.spec`.
- Current expected artifact is `dist/generate_daily_report.exe`.
- TODO: confirm whether the repository should move to a dual GUI/CLI Windows release layout before documenting `windows-release/` paths.

### macOS

```bash
chmod +x scripts/build_release_macos.sh
./scripts/build_release_macos.sh
```

## Useful Verification Commands

### Member module verification

```bash
./.venv/bin/python scripts/verify_member_metrics_module.py \
  --date 2026-03-11 \
  --config ./config.yaml \
  --extra-auth-file ./extra_auth.json
```

### PC delivery verification

```bash
./.venv/bin/python scripts/verify_pc_delivery.py \
  --report-file ./output/2026311_pc_report.txt \
  --date 2026-03-11 \
  --skip-push
```

### Focused tests

```bash
./.venv/bin/python -m unittest tests.test_auth_stability -v
./.venv/bin/python -m unittest tests.test_feishu_doc_retry -v
./.venv/bin/python -m unittest tests.test_pc_report_features -v
./.venv/bin/python -m unittest tests.test_verify_member_metrics_module -v
./.venv/bin/python -m unittest tests.test_browser_auth_refresh -v
./.venv/bin/python -m unittest tests.test_fenxi_auth_from_har -v
./.venv/bin/python -m unittest tests.test_pc_auth_from_har -v
./.venv/bin/python -m unittest tests.test_auth_recovery_playwright -v
```

## Recommended Incident Workflow

1. Confirm branch and working tree.
2. Run auth preflight.
3. Refresh only the failing platform auth.
4. Re-run preflight.
5. Use push-only if report artifacts already exist.
6. Use full rerun only when data generation itself must be repeated.
