# 云游戏日报自动化工具（v1.0.1）

统一生成 870 日报 + 分析后台（fenxi）扩展数据 + 505 付费表图片 + PC 网页端新增/活跃/Top10。

## 项目功能
- 拉取 870 多条线路数据，输出总览日报与 PC 日报。
- 自动计算并发峰值、排队峰值、排队时段，并生成趋势图。
- 拉取 fenxi 扩展指标：新增、活跃、会员付费率、会员充值、会员数。
- 拉取 505 付费数据并输出两张固定样式图片：页游对比表、手游双列榜单表。
- 拉取 PC 网页端数据（`yapiadmin/yadmin`）：新增、活跃、活跃 Top10（去重）、会员指标（总金额/总订单数/首开会员总金额/首开会员数）。
- 将以上内容整合到同一份日报文本里。

## 项目结构
- `generate_daily_report.py`: 主入口（单命令跑完整日报）。
- `fastapi_app.py`: FastAPI 服务入口（HTTP 调用任务）。
- `extra_metrics_service.py`: fenxi/505 数据抓取与解析。
- `extra_metrics_render.py`: 扩展文案渲染 + 505 图片渲染。
- `extra_auth.py`: 从 HAR 构建并读取扩展认证信息。
- `network_hosts.py`: hosts 映射重写。
- `templates/`: 日报模板。

## 快速开始
建议 Python 3.10+。

```bash
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
```

复制本地配置文件：

```bash
cp config.example.yaml config.yaml
cp hosts_870.example.yaml hosts_870.yaml
cp hosts_505.example.yaml hosts_505.yaml
cp extra_auth.example.json extra_auth.json
```

## 核心配置说明
`config.yaml` 重点字段：
- `base_url`: 870 接口地址。
- `session_cookie`: 870 登录态（`PHPSESSID=...`）。
- `network.hosts_yaml_path`: 870 hosts 文件路径。
- `targets`: 870 线路配置（总/页游/主机/手游/原神等）。
- `extra_metrics.enabled`: 是否启用 fenxi+505 扩展数据。
- `extra_metrics.fenxi_base`: fenxi 基地址。
- `extra_metrics.manage_base`: 505 基地址。
- `extra_metrics.hosts_yaml_path`: 505 hosts 文件路径。
- `pc_web_metrics.enabled`: 是否启用 PC 网页端新增/活跃/Top10。
- `pc_web_metrics.base`: PC API 基地址（默认 `http://yapiadmin.4399.com`）。
- `pc_web_metrics.web_origin`: PC 控制台来源域（默认 `http://yadmin.4399.com`）。
- `pc_web_metrics.strict`: PC 链路失败是否中断（默认 `true`，推荐保持开启，避免输出不完整 PC 日报）。
- `pc_web_metrics.auth_key`: `extra_auth.json` 中用于 PC 的认证键（默认 `pc_web`，PC 登录态独立，不再回退到 `505`）。
- `pc_web_metrics.include_member_metrics`: 是否抓取 PC 会员指标（依赖 fenxi 登录态，默认 `true`）。
- `pc_web_metrics.hosts_yaml_path`: PC 请求 hosts 文件路径（可与 505 共用）。
- `feishu_doc.enabled`: 是否推送到飞书文档（不填时默认开启）。
- `feishu_doc.pc_enabled`: 是否额外推送 PC 日报到飞书（默认 `true`）。
- `feishu_doc.pc_title` / `feishu_doc.pc_title_prefix`: PC 飞书文档标题配置。
- `feishu_doc.app_id` / `feishu_doc.app_secret`: 飞书自建应用凭证（建议用环境变量提供）。
- `feishu_doc.folder_token`: 文档创建目录（可选）。
- `feishu_doc.auto_share_tenant_members`: 创建后自动共享给租户全员（默认 `false`）。
- `feishu_doc.auto_share_mode`: 自动共享权限，`read` 或 `edit`（默认 `read`）。
- `feishu_doc.auto_share_strict`: 自动共享失败是否中断任务（默认 `false`）。
- `feishu_doc.image_width` / `feishu_doc.narrow_image_width`: 飞书图片展示宽度（默认 `960/760`）。
- `feishu_doc.prevent_upscale`: 是否禁止小图放大（默认 `true`，推荐保持开启，避免变形）。

## 运行方式
### GUI 启动器（推荐）
你可以直接用桌面按钮运行，不需要命令行。

macOS：
```bash
chmod +x scripts/start_gui.command
./scripts/start_gui.command
```

Windows：
- 双击 `scripts/start_gui.bat`

启动器功能：
- `打开870登录页`：一键打开 870 登录页，先登录再跑任务。
- `立即启动任务`：立刻执行日报全流程（支持扩展数据与飞书推送）。
- `任务进度条`：按主流程阶段实时更新进度。
- `运行日志`：实时显示执行日志；成功后可点 `打开最新飞书文档`。
- `定时任务面板`：可直接设置每天时间，并在 GUI 内完成 `安装/更新`、`立即触发`、`取消任务`。

可选配置：
- `config.yaml` 可增加 `login_url_870`，用于覆盖默认登录跳转地址。

### 命令行
生成完整日报（870 + 扩展 + 图表）：

```bash
./.venv/bin/python generate_daily_report.py --date 2026-02-20 --with-extra-metrics
```

说明：`--with-extra-metrics` 现在会先做 fenxi/505 登录态预检，预检失败会直接中止，避免输出缺失扩展数据的“伪完整”日报。

生成完整日报（默认会推送飞书文档）：

```bash
FEISHU_APP_ID="cli_xxx" \
FEISHU_APP_SECRET="xxx" \
./.venv/bin/python generate_daily_report.py --date 2026-02-20 --with-extra-metrics
```

可选参数：
- `--no-push-feishu-doc`: 本次运行禁用飞书推送。
- `--feishu-folder-token`: 指定飞书目录 token。
- `--feishu-doc-title`: 指定文档标题（不传则按 `title_prefix_YYYYMMDD` 自动生成）。
- `--feishu-doc-url-prefix`: 自定义结果链接前缀（默认 `https://www.feishu.cn/docx/`）。
- `--verify-feishu-content`: 推送后调用 `docs/v1/content` 拉回 markdown 做内容校验（需权限 `docs:document.content:read`）。

自动共享说明：
- 开启 `feishu_doc.auto_share_tenant_members=true` 后，脚本会在创建文档后调用飞书权限接口设置“租户内可读/可编辑”。
- 若接口权限不足，可先保持 `feishu_doc.auto_share_strict=false`，任务仍会完成并在日志打印 `Feishu share status: warn`。

仅推送已有报告文件（快速验证，不重跑数据）：

```bash
FEISHU_APP_ID="cli_xxx" \
FEISHU_APP_SECRET="xxx" \
./.venv/bin/python generate_daily_report.py --push-report-file ./output/2026220_report.txt --date 2026-02-20
```

单独推送 PC 日报（图文）：

```bash
./.venv/bin/python generate_daily_report.py --push-report-file ./output/2026220_pc_report.txt --date 2026-02-20
```

说明：若报告中包含 `[pc云游戏图片]` 占位符，脚本会自动尝试读取 `output/charts/pc_cloud.png` 并上传到飞书。

每日登录态建议流程（手机验证码登录后）：

```bash
# 1) 推荐：从本机浏览器自动刷新 fenxi + PC 登录态（无需HAR）
./.venv/bin/python browser_auth_refresh.py \
  --browser auto \
  --extra-auth-file ./extra_auth.json \
  --output ./extra_auth.json \
  --hosts-yaml-path ./hosts_505.yaml

# 若 auto 失败，可显式指定浏览器（含 arc / atlas）：
# ./.venv/bin/python browser_auth_refresh.py --browser arc --extra-auth-file ./extra_auth.json --output ./extra_auth.json --hosts-yaml-path ./hosts_505.yaml
# ./.venv/bin/python browser_auth_refresh.py --browser atlas --extra-auth-file ./extra_auth.json --output ./extra_auth.json --hosts-yaml-path ./hosts_505.yaml
# 非标准安装路径可加：--cookie-file /path/to/Cookies --key-file /path/to/Local\\ State

# 2) 如需连 505 一起更新，或自动刷新失败，再用 HAR 刷新扩展认证（fenxi/505/PC网页端）
./.venv/bin/python generate_daily_report.py \
  --build-extra-auth \
  --fenxi-har "/path/to/fenxi.har" \
  --manage-har "/path/to/manage.har" \
  --pc-har "/path/to/yadmin_pc.har"

# 3) 只做扩展登录态预检（不跑870）
./.venv/bin/python generate_daily_report.py --check-extra-auth --date 2026-02-20

# 4) 预检通过后再跑正式日报
./.venv/bin/python generate_daily_report.py --date 2026-02-20 --with-extra-metrics
```

预检日志会输出 `fenxi e_token` 的 `iat/exp/remaining_min`。若剩余时间低于 6 小时，会按不可用处理并直接失败，避免“跑到一半过期”。

Playwright 自动登录修复（推荐配合 GUI 自动重试）：

```bash
# 首次使用需安装浏览器内核
./.venv/bin/playwright install chromium

# 失效时拉起登录页，弹窗输入手机号/验证码，自动回填 fenxi + pc_web 凭证
./.venv/bin/python auth_recovery_playwright.py \
  --extra-auth-file ./extra_auth.json \
  --output ./extra_auth.json \
  --ask-sms
```

说明：
- 脚本会尝试自动切到“验证码登录”、勾选协议、点击“发送验证码”。
- 若日志出现 `[AUTH] 未检测到发送验证码请求`，说明页面结构未匹配成功，请在浏览器页面手动点“发送验证码/登录”，脚本会继续等待并抓取登录态。

也可以先一条命令刷新并预检：

```bash
./.venv/bin/python generate_daily_report.py \
  --build-extra-auth \
  --pc-har "/path/to/yadmin_pc.har" \
  --check-extra-auth \
  --date 2026-02-20
```

`--extra-auth-max-age-hours` 可设置认证文件老化阈值（默认 24 小时）：

```bash
./.venv/bin/python generate_daily_report.py --check-extra-auth --extra-auth-max-age-hours 24
```

### FastAPI 服务版
用于团队系统集成：通过 HTTP API 触发日报任务、查询进度和日志。

启动（macOS/Linux）：

```bash
chmod +x scripts/start_api.sh
./scripts/start_api.sh
```

启动（Windows）：
- 双击 `scripts/start_api.bat`

默认地址：
- API: `http://127.0.0.1:8000`
- Swagger: `http://127.0.0.1:8000/docs`

鉴权（可选但推荐）：
- 配置环境变量 `REPORT_API_TOKEN` 后，`/jobs*` 接口将强制校验请求头 `X-API-Token`。
- 未配置 `REPORT_API_TOKEN` 时，默认不启用鉴权（便于本机调试）。

核心接口：
- `GET /health`: 健康检查。
- `GET /meta/login-url-870`: 返回 870 登录页地址（从 `config.yaml` 解析）。
- `POST /jobs/report`: 创建并启动日报任务。
- `GET /jobs`: 查看任务列表。
- `GET /jobs/{job_id}`: 查看单任务状态（含进度、飞书链接）。
- `GET /jobs/{job_id}/logs?limit=300`: 查看任务日志。
- `POST /jobs/{job_id}/cancel`: 取消运行中的任务。

创建任务示例：

```bash
curl -X POST "http://127.0.0.1:8000/jobs/report" \
  -H "Content-Type: application/json" \
  -H "X-API-Token: <YOUR_TOKEN>" \
  -d '{
    "date": "2026-02-20",
    "with_extra_metrics": true,
    "verify_feishu_content": false,
    "disable_feishu_push": false
  }'
```

说明：
- API 内置“单任务并发保护”，同一时刻只允许一个任务运行，避免登录态/文件冲突。
- API 运行时会实时解析 `[PROGRESS]` 日志并回传进度。

## 定时任务（稳定每日推送飞书）
前提：你每天先完成一次手机验证码登录，刷新当天登录态（`session_cookie` + `extra_auth.json`）。

### macOS（launchd）
1. 准备调度环境变量：
```bash
cp .env.scheduler.example .env.scheduler
```
填入真实 `FEISHU_APP_ID/FEISHU_APP_SECRET`。

2. 给脚本执行权限：
```bash
chmod +x scripts/run_daily_report.sh scripts/install_macos_launchd.sh
```

3. 安装每天定时任务（示例：每天 09:10）：
```bash
./scripts/install_macos_launchd.sh 9 10
```

4. 手动触发一次测试：
```bash
launchctl kickstart -k gui/$(id -u)/com.starfish.autodatareport.daily
```

日志位置：
- `output/scheduler_logs/launchd_stdout.log`
- `output/scheduler_logs/launchd_stderr.log`
- `output/scheduler_logs/daily_*.log`

### Windows（任务计划程序）
1. 先手动验证一次脚本：
```powershell
powershell -ExecutionPolicy Bypass -File .\scripts\run_daily_report.ps1 -DateMode today
```

2. 创建每日任务（示例：每天 09:10）：
```powershell
schtasks /Create /SC DAILY /TN "AutoDataReportDaily" /TR "powershell -ExecutionPolicy Bypass -File C:\path\to\autodatareport\scripts\run_daily_report.ps1 -DateMode today" /ST 09:10
```

3. 立即执行测试：
```powershell
schtasks /Run /TN "AutoDataReportDaily"
```

日志位置：
- `output\scheduler_logs\daily_*.log`

脚本特性（macOS/Windows）：
- 自动做扩展登录态预检（失败直接终止，避免推送错误日报）。
- 失败自动重试（默认 3 次，间隔 300 秒）。
- 带运行日志，便于定位问题。
- macOS 脚本带并发锁，避免重复触发时重入。

## 打包分发（macOS 双版本）
本项目当前提供两种 macOS 分发包：
- `CLI`：命令行版（适合服务器/脚本调用）
- `GUI`：桌面点击版（适合运营同学）

一键构建：

```bash
chmod +x scripts/build_release_macos.sh
./scripts/build_release_macos.sh
```

构建产物目录：
- `dist/releases/<timestamp>/autodatareport-cli-macos.zip`
- `dist/releases/<timestamp>/autodatareport-gui-macos.zip`

说明：
- 打包时只包含 `config.example.yaml`，不会打包本地 `config.yaml`、`extra_auth.json` 等敏感文件。
- Windows `.exe` 需在 Windows 环境打包（保留 `build_exe.bat` 流程）。

仅跑 870 主报告：

```bash
./.venv/bin/python generate_daily_report.py --date 2026-02-20
```

首次接入扩展时，用 HAR 生成认证文件：

```bash
./.venv/bin/python generate_daily_report.py \
  --build-extra-auth \
  --fenxi-har "/path/to/fenxi1.har" \
  --fenxi-har "/path/to/fenxi2.har" \
  --manage-har "/path/to/manage505.har"
```

## 产物输出
- `output/YYYYMMDD_report.txt`: 总览日报（含扩展备注与图片路径）。
- `output/YYYYMMDD_pc_report.txt`: PC 云游戏日报。
- `output/charts/*.png`: 870 图表 + 505 两张付费表图。
  - `505_page_payment_table_YYYYMMDD.png`
  - `505_mobile_payment_table_YYYYMMDD.png`

## 常见问题
- 870 返回登录页：`session_cookie` 失效，重新登录后更新 `config.yaml`。
- fenxi/505 失败：检查 `extra_auth.json`、hosts 配置、是否需要重新抓 HAR。
- 扩展登录态当天可用但次日失效：先手机验证码登录，再执行 `--build-extra-auth` + `--check-extra-auth`。
- 浏览器自动刷新失败（`无法读取浏览器Cookie`）：先确认目标浏览器已登录，再显式指定 `--browser chrome|edge|chromium|brave|firefox|safari|arc|atlas`；非标准安装路径可加 `--cookie-file/--key-file`；仍失败时回退 HAR 刷新。
- Atlas 提示 `Admin-Token` 加密无法读取：这是浏览器本地加密限制，直接使用 GUI 的 `上传PC HAR并更新`。
- PC 返回 `status=-100, msg=请先登录`：优先检查 `extra_auth.json` 中 `pc_web.headers.Bearer` 是否存在；没有则重抓 `yadmin` HAR 并重新 `--build-extra-auth`。
- fenxi 返回 401：检查预检日志里的 `e_token exp`（到期时间）并重新登录抓 HAR。
- 无法弹 GUI：无图形环境是正常现象，脚本会自动跳过 GUI 输入框。

GUI 登录态维护（`scripts/start_gui.command`）：
- `自动刷新PC登录态`：调用 `browser_auth_refresh.py --pc-only`，默认按 atlas 浏览器刷新 `pc_web`。
- `上传PC HAR并更新`：选择 yadmin/yapiadmin HAR 后只更新 `extra_auth.json` 的 pc_web 区块，不覆盖 `fenxi/505`。
- `上传Fenxi HAR并更新`：选择 fenxi HAR 后只更新 `extra_auth.json` 的 fenxi 区块，不覆盖 `pc_web/505`。
- 勾选 `登录态失败时自动修复并重试一次` 后：任务若命中登录态错误，会自动触发 `auth_recovery_playwright.py`（弹窗输入验证码）+ `--check-extra-auth`，通过后自动重试主任务一次。

## 安全注意
- 不要提交这些本地敏感文件：`config.yaml`、`extra_auth.json`、`hosts_*.yaml`、`*.har`、`output/`。
