# 云游戏日报自动化工具

基于配置接口数据，自动拉取并生成“游戏盒云游戏数据”与“游戏盒PC云游戏数据”日报文本，同时可选生成并发/排队趋势图。

## 功能概览
- 按照配置批量请求不同参数（`game_type`、`game_id`、`pre_type` 等）数据。
- 自动汇总并发、排队时序，计算峰值与峰值时间，识别排队时段。
- 支持写出两份日报：
  - `report_template.j2`：总览（含手游/页游/主机/高画质等）+ PC 云游戏部分。
  - `pc_report_template.j2`：PC 云游戏独立日报。
- 根据配置输出排队主导游戏、异常提示等分析语句。
- 使用 Jinja2 模板渲染日报文案，保持格式与既定样例一致。
- 可选生成并发/排队趋势图（需要安装 `matplotlib`）。

## 环境准备
建议使用 Python 3.10+。

```powershell
cd report_automation
python -m venv .venv
.venv\Scriptsctivate
pip install -r requirements.txt
```

先复制示例配置：

```powershell
cp config.example.yaml config.yaml
cp hosts_870.example.yaml hosts_870.yaml
cp hosts_505.example.yaml hosts_505.yaml
cp extra_auth.example.json extra_auth.json
```

> `config.yaml`、`extra_auth.json`、`hosts_*.yaml` 包含敏感信息，默认已在 `.gitignore` 中忽略，不要提交。

## 核心配置（`config.yaml`）

- `base_url`: 870 数据接口地址。
- `session_cookie`: 登录后的会话 Cookie，格式类似 `PHPSESSID=xxxx`。
- `default_time_field`: 数据行中表示时间的字段名，默认 `ctime`。
- `default_http_method`: 请求接口所用的 HTTP 方法，默认 `post`（接口在 `get` 时会忽略筛选参数）。
- `network`: 870 接口代理策略。
  - `proxy_mode`: `direct` / `system` / `custom`。
  - `http_proxy` / `https_proxy`: 当 `proxy_mode=custom` 时生效。
  - `hosts_yaml_path`: 可选，hosts 映射文件路径，用于将域名重写到固定 IP。
  - 建议为 870 单独维护一个 hosts 文件，例如 `hosts_870.yaml`。
- `auto_query_params`: 自动注入到所有查询中的日期参数，可通过 `format` 指定 `strftime` 模式，`offset_days` 控制相对报表日期的偏移（例如 `0` 表示当日，`-1` 表示昨日）。
- `targets`: 定义需要拉取的所有指标。新增 `pc_cloud` 条目示例：
  ```yaml
  pc_cloud:
    label: "PC云游戏"
    queries:
      - params:
          game_type: 7
    concurrency_series_patterns:
      - "used_container_num_0"
    queue_series_patterns:
      - "line_member_num_0"
  ```
- `report_section_order`: 报告中各部分的顺序；默认已追加 `pc_cloud`。
- `analysis_groups`、`anomaly_rules`: 仍可按需扩展分析语句与异常检测。
- `extra_metrics`: 可选扩展数据源（fenxi + 505）配置。
  - `enabled`: 是否在生成日报时拉取扩展指标。
  - `auth_file`: 扩展认证文件路径（默认 `extra_auth.json`）。
  - `fenxi_base` / `manage_base`: 扩展接口基地址（建议只写在本地 `config.yaml`）。
  - `fenxi_hars` / `manage_hars`: 用于生成扩展认证文件的 HAR 路径列表。
  - `hosts_yaml_path` / `query_proxy_url`: 扩展接口请求网络设置（可留空）。
  - 建议为 505 单独维护一个 hosts 文件，例如 `hosts_505.yaml`。

## 运行脚本

```powershell
python generate_daily_report.py --date 2025-10-22 --cookie "PHPSESSID=..." --no-charts
```

870 代理模式可通过命令行覆盖（优先级高于 `config.yaml`）：

```powershell
# 直连（忽略系统代理）
python generate_daily_report.py --proxy-mode direct

# 跟随系统代理
python generate_daily_report.py --proxy-mode system

# 指定自定义代理
python generate_daily_report.py --proxy-mode custom --http-proxy "http://127.0.0.1:7890" --https-proxy "http://127.0.0.1:7890"

# 指定 hosts 映射文件（可覆盖 config.yaml）
python generate_daily_report.py --network-hosts-yaml "/path/to/hosts_870.yaml"
```

### 扩展指标（fenxi + 505）首次使用

1) 先用 HAR 构建扩展认证文件：

```powershell
python generate_daily_report.py --build-extra-auth --fenxi-har "/path/to/fenxi_a.har" --fenxi-har "/path/to/fenxi_b.har" --manage-har "/path/to/manage_505.har"
```

2) 生成日报时附带扩展指标：

```powershell
python generate_daily_report.py --with-extra-metrics --date 2026-02-21 --cookie "PHPSESSID=..."
```

扩展指标失败不会阻断 870 主报告，会在报告末尾写出 warning。

开启扩展指标后，会额外生成两张 505 付费表图片（样式为表格图）：
- `output/charts/505_page_payment_table_YYYYMMDD.png`：页游（工作web+厦门夜游）当日 vs 上周同期 + 对比。
- `output/charts/505_mobile_payment_table_YYYYMMDD.png`：手游当日榜 vs 上周同期榜 + 合计对比。

脚本启动时默认弹出 GUI 询问 `PHPSESSID` 与报表日期；如已通过命令行提供，会自动带出默认值。无图形环境或批量任务可自行注入 `prompt_runtime_inputs`（或在未来版本关闭 GUI）。

生成结果：
- `output/20251022_report.txt`：总览日报。
- `output/20251022_pc_report.txt`：PC 云游戏日报。
- `output/charts/*.png`：各线路并发/排队图表（包含 `pc_cloud.png`）。

> **查看提示**：文本使用 UTF-8 编码，若在 Windows PowerShell 中查看出现 `??`，请改用支持 UTF-8 的编辑器（如 VS Code、Notepad）或执行 `chcp 65001` 后再 `type`。

## 打包为独立 exe

```powershell
cd report_automation
.venv\Scriptsctivate
.uild_exe.bat
```

打包完成后，`dist\generate_daily_report.exe` 会携带 `config.yaml`、`templates/`。如需覆盖模板，可在 exe 同目录提供同名文件；程序会优先读取外部模板。

## GitHub 发布（脱敏）

首次发布建议：

```powershell
# 1) 确认敏感文件未被跟踪
git status --ignored

# 2) 初始化仓库（如果当前目录还没有 .git）
git init
git branch -M main

# 3) 提交首版
git add .
git commit -m "v1: report automation (sanitized)"

# 4) 关联远端并推送
git remote add origin <YOUR_GITHUB_REPO_URL>
git push -u origin main
```

发布前检查：
- 不提交 `config.yaml`、`extra_auth.json`、`hosts_*.yaml`、`*.har`、`output/`。
- 只提交 `config.example.yaml`、`hosts_*.example.yaml`、`extra_auth.example.json`。

## 常见调整
- **返回结构不匹配**：可在 `generate_daily_report.py` 中扩展 `extract_series`/`normalize_series_entry`，或开启 `--verbose` 查看详细日志。
- **字段名称不同**：在配置里新增匹配正则即可，例如 `queue_series_patterns: ["line_member_num_0", "line_member_num_1"]`。
- **新增游戏或线路**：在 `targets` 中新增条目即可，将其加入 `report_section_order` 和分析分组。
- **异常检测**：根据需要在 `anomaly_rules` 中编写规则，生成定制提示。

## 已知限制
- 依赖有效的后台 Cookie，失效需重新登录更新。
- 目前通过多次 HTTP 请求直接聚合数据，尚未做节流/重试；如接口限频请自行添加延迟。
- 报表输出位于 `output/` 目录，图表中文依赖系统可用字体（`Microsoft YaHei`、`SimHei` 等）。如图表出现方块，可安装相关字体后重新生成。
