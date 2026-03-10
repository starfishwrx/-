# 云游戏日报自动化工具（v1.0.1）

自动抓取多个后台数据统计，并制作可视化表格，渲染合并成一整份完整的数据日报

## 项目功能
- 拉取后台多条线路数据，输出总览日报与 PC 日报。
- 自动计算并发峰值、排队峰值、排队时段，并生成趋势图。
- 拉取 后台2 扩展指标：新增、活跃、会员付费率、会员充值、会员数。
- 拉取 后台3付费数据并输出两张固定样式图片：页游对比表、手游双列榜单表。
- 将以上内容整合到同一份日报文本里。

## 项目结构
- `generate_daily_report.py`: 主入口（单命令跑完整日报）。
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

## 运行方式
生成完整日报（870 + 扩展 + 图表）：

```bash
./.venv/bin/python generate_daily_report.py --date 2026-02-20 --with-extra-metrics
```

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
- 无法弹 GUI：无图形环境是正常现象，脚本会自动跳过 GUI 输入框。

## 安全注意
- 不要提交这些本地敏感文件：`config.yaml`、`extra_auth.json`、`hosts_*.yaml`、`*.har`、`output/`。
