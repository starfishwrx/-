from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime, timezone
import os
from pathlib import Path
import re
import subprocess
import threading
import uuid
from typing import Dict, List, Optional

from fastapi import Depends, FastAPI, HTTPException, Query, Security
from fastapi.security import APIKeyHeader
from pydantic import BaseModel, Field
import yaml


PROGRESS_RE = re.compile(r"\[PROGRESS\]\s*(\d{1,3})\|(.+)")
FEISHU_URL_RE = re.compile(r"Feishu(?: PC)? doc published:\s*(https?://\S+)")
DATE_RE = re.compile(r"\d{4}-\d{2}-\d{2}")
MAX_JOB_LOG_LINES = 4000
MAX_LOGS_API_LIMIT = 2000


OPENAPI_DESCRIPTION = """
## 使用说明
1. 先调用 `/meta/login-url-870` 获取 870 登录页，确认当天登录态有效。
2. 调用 `POST /jobs/report` 启动日报任务。
3. 用 `GET /jobs/{job_id}` 或 `GET /jobs/{job_id}/logs` 轮询进度。
4. 任务结束后在响应中的 `feishu_url` 查看推送结果（若开启飞书推送）。

## 鉴权说明
- 当环境变量 `REPORT_API_TOKEN` 已配置时，`/jobs*` 接口必须带请求头：`X-API-Token: <token>`。
- 当未配置 `REPORT_API_TOKEN` 时，本地调试可免鉴权调用。

## 运行约束
- 同一时间只允许 1 个报告任务运行，避免登录态和配置冲突。
- 任务日志在内存中保留最近 4000 行，避免长期运行占用过高内存。
"""

OPENAPI_TAGS = [
    {
        "name": "system",
        "description": "服务基础信息与健康检查。",
    },
    {
        "name": "meta",
        "description": "辅助信息接口（例如 870 登录页地址）。",
    },
    {
        "name": "jobs",
        "description": "日报任务管理：启动、查询、日志、取消。",
    },
]


def _now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


def _project_root() -> Path:
    return Path(__file__).resolve().parent


def _resolve_python_bin(root: Path) -> str:
    venv = root / ".venv" / "bin" / "python"
    if venv.exists():
        return str(venv)
    return "python3"


def _resolve_870_login_url(config_path: Path) -> str:
    if not config_path.exists():
        return ""
    try:
        cfg = yaml.safe_load(config_path.read_text(encoding="utf-8")) or {}
    except Exception:  # noqa: BLE001
        return ""
    if not isinstance(cfg, dict):
        return ""
    explicit = str(cfg.get("login_url_870") or "").strip()
    if explicit:
        return explicit
    base = str(cfg.get("base_url") or "").strip()
    if not base:
        return ""
    # Keep logic aligned with GUI launcher behavior.
    if "://" in base:
        parts = base.split("://", 1)
        scheme = parts[0]
        host = parts[1].split("/", 1)[0]
        if host:
            return f"{scheme}://{host}/?m=user&ac=login"
    return ""


class RunReportRequest(BaseModel):
    date: Optional[str] = Field(
        default=None,
        description="日报日期，格式 YYYY-MM-DD；不传则按脚本默认逻辑取值。",
        examples=["2026-02-20"],
    )
    config: str = Field(
        default="config.yaml",
        description="配置文件路径（可绝对路径，或相对于项目根目录）。",
        examples=["config.yaml"],
    )
    with_extra_metrics: bool = Field(
        default=True,
        description="是否启用分析后台 + 505 扩展指标。",
    )
    verify_feishu_content: bool = Field(
        default=False,
        description="是否在推送后调用 Feishu 内容接口做二次校验。",
    )
    disable_feishu_push: bool = Field(
        default=False,
        description="是否禁用飞书推送（仅本地生成）。",
    )
    no_charts: bool = Field(
        default=False,
        description="是否禁用图表生成（仅文本和表格）。",
    )
    verbose: bool = Field(
        default=False,
        description="是否输出更详细日志。",
    )
    extra_auth_max_age_hours: Optional[int] = Field(
        default=None,
        description="扩展后台登录态最大有效小时数；超时会触发鉴权失败。",
        examples=[24],
    )

    model_config = {
        "json_schema_extra": {
            "examples": [
                {
                    "summary": "常用完整日报",
                    "description": "生成 2026-02-20 的完整日报并包含扩展指标。",
                    "value": {
                        "date": "2026-02-20",
                        "config": "config.yaml",
                        "with_extra_metrics": True,
                        "verify_feishu_content": True,
                        "disable_feishu_push": False,
                        "no_charts": False,
                        "verbose": False,
                    },
                },
                {
                    "summary": "快速调试（不推飞书）",
                    "description": "仅用于本地逻辑验证，跳过飞书推送。",
                    "value": {
                        "date": "2026-02-20",
                        "config": "config.yaml",
                        "with_extra_metrics": True,
                        "disable_feishu_push": True,
                        "no_charts": False,
                        "verbose": True,
                    },
                },
            ]
        }
    }


class JobStatusResponse(BaseModel):
    job_id: str = Field(description="任务 ID。")
    status: str = Field(description="任务状态：queued/running/succeeded/failed/canceled。")
    created_at: str = Field(description="任务创建时间（UTC ISO8601）。")
    started_at: Optional[str] = Field(default=None, description="任务开始时间（UTC ISO8601）。")
    finished_at: Optional[str] = Field(default=None, description="任务结束时间（UTC ISO8601）。")
    return_code: Optional[int] = Field(default=None, description="脚本退出码（0 表示成功）。")
    progress: int = Field(default=0, description="进度百分比，范围 0-100。")
    stage: str = Field(default="", description="当前阶段文本（由脚本 PROGRESS 日志解析）。")
    feishu_url: Optional[str] = Field(default=None, description="飞书文档链接（若推送成功）。")
    command: List[str] = Field(default_factory=list, description="实际执行命令（数组形式）。")


class JobLogsResponse(BaseModel):
    job_id: str = Field(description="任务 ID。")
    status: str = Field(description="任务状态。")
    progress: int = Field(description="进度百分比。")
    stage: str = Field(description="当前阶段文本。")
    log_lines: List[str] = Field(description="最近日志行（按请求 limit 截断）。")


@dataclass
class Job:
    job_id: str
    status: str = "queued"
    created_at: str = field(default_factory=_now_iso)
    started_at: Optional[str] = None
    finished_at: Optional[str] = None
    return_code: Optional[int] = None
    progress: int = 0
    stage: str = ""
    feishu_url: Optional[str] = None
    command: List[str] = field(default_factory=list)
    log_lines: List[str] = field(default_factory=list)
    process: Optional[subprocess.Popen[str]] = None
    cancel_requested: bool = False

    def to_status(self) -> JobStatusResponse:
        return JobStatusResponse(
            job_id=self.job_id,
            status=self.status,
            created_at=self.created_at,
            started_at=self.started_at,
            finished_at=self.finished_at,
            return_code=self.return_code,
            progress=self.progress,
            stage=self.stage,
            feishu_url=self.feishu_url,
            command=self.command,
        )


class JobStore:
    def __init__(self) -> None:
        self._lock = threading.Lock()
        self._jobs: Dict[str, Job] = {}

    def create(self, command: List[str]) -> Job:
        with self._lock:
            # Operational guardrail: one running job at a time to avoid auth/config conflicts.
            for job in self._jobs.values():
                if job.status in {"queued", "running"}:
                    raise RuntimeError(f"已有运行中任务: {job.job_id}")
            job_id = uuid.uuid4().hex[:12]
            job = Job(job_id=job_id, command=list(command))
            self._jobs[job_id] = job
            return job

    def get(self, job_id: str) -> Job:
        with self._lock:
            job = self._jobs.get(job_id)
            if job is None:
                raise KeyError(job_id)
            return job

    def list(self) -> List[Job]:
        with self._lock:
            return list(self._jobs.values())

    def append_log(self, job_id: str, line: str) -> None:
        with self._lock:
            job = self._jobs[job_id]
            job.log_lines.append(line)
            if len(job.log_lines) > MAX_JOB_LOG_LINES:
                job.log_lines = job.log_lines[-MAX_JOB_LOG_LINES:]
            m = PROGRESS_RE.search(line)
            if m:
                job.progress = max(0, min(100, int(m.group(1))))
                job.stage = m.group(2).strip()
            u = FEISHU_URL_RE.search(line)
            if u:
                job.feishu_url = u.group(1).strip()

    def mark_running(self, job_id: str, process: subprocess.Popen[str]) -> None:
        with self._lock:
            job = self._jobs[job_id]
            job.status = "running"
            job.started_at = _now_iso()
            job.process = process

    def mark_done(self, job_id: str, return_code: int) -> None:
        with self._lock:
            job = self._jobs[job_id]
            job.return_code = return_code
            job.finished_at = _now_iso()
            job.process = None
            if job.cancel_requested and return_code != 0:
                job.status = "canceled"
            else:
                job.status = "succeeded" if return_code == 0 else "failed"
            if return_code == 0:
                job.progress = 100
                if not job.stage:
                    job.stage = "任务完成"

    def request_cancel(self, job_id: str) -> bool:
        with self._lock:
            job = self._jobs[job_id]
            job.cancel_requested = True
            proc = job.process
        if proc is None:
            return False
        try:
            proc.terminate()
            return True
        except Exception:  # noqa: BLE001
            return False


app = FastAPI(
    title="AutoDataReport API",
    version="1.1.0",
    description=OPENAPI_DESCRIPTION,
    openapi_tags=OPENAPI_TAGS,
)
store = JobStore()
api_token_header = APIKeyHeader(
    name="X-API-Token",
    auto_error=False,
    description="可选请求头。配置了 REPORT_API_TOKEN 时必填。",
)


def _require_api_token(x_api_token: Optional[str] = Security(api_token_header)) -> None:
    expected = str(os.getenv("REPORT_API_TOKEN") or "").strip()
    # Keep local/dev experience simple when token is not configured.
    if not expected:
        return
    if x_api_token != expected:
        raise HTTPException(status_code=401, detail="invalid api token")


def _resolve_config_path(root: Path, raw_path: str) -> Path:
    p = Path(raw_path)
    if p.is_absolute():
        return p
    return (root / p).resolve()


def _build_report_command(root: Path, req: RunReportRequest) -> List[str]:
    if req.date and not DATE_RE.fullmatch(req.date):
        raise ValueError("date must be YYYY-MM-DD")
    config_path = _resolve_config_path(root, req.config)
    if not config_path.exists():
        raise ValueError(f"config not found: {config_path}")

    cmd: List[str] = [
        _resolve_python_bin(root),
        str(root / "generate_daily_report.py"),
        "--config",
        str(config_path),
        "--no-runtime-gui",
    ]
    if req.date:
        cmd.extend(["--date", req.date])
    if req.with_extra_metrics:
        cmd.append("--with-extra-metrics")
    if req.verify_feishu_content:
        cmd.append("--verify-feishu-content")
    if req.disable_feishu_push:
        cmd.append("--no-push-feishu-doc")
    if req.no_charts:
        cmd.append("--no-charts")
    if req.verbose:
        cmd.append("--verbose")
    if req.extra_auth_max_age_hours is not None:
        cmd.extend(["--extra-auth-max-age-hours", str(req.extra_auth_max_age_hours)])
    return cmd


def _run_job_thread(root: Path, job_id: str, cmd: List[str]) -> None:
    try:
        proc = subprocess.Popen(
            cmd,
            cwd=str(root),
            stdout=subprocess.PIPE,
            stderr=subprocess.STDOUT,
            text=True,
            bufsize=1,
            env=os.environ.copy(),
        )
        store.mark_running(job_id, proc)
        store.append_log(job_id, f"[JOB] started pid={proc.pid}")
        assert proc.stdout is not None
        for raw in proc.stdout:
            store.append_log(job_id, raw.rstrip("\n"))
        rc = proc.wait()
        store.mark_done(job_id, rc)
    except Exception as exc:  # noqa: BLE001
        store.append_log(job_id, f"[JOB ERROR] {exc}")
        store.mark_done(job_id, 1)


@app.get(
    "/health",
    tags=["system"],
    summary="服务健康检查",
    description="用于确认 FastAPI 服务是否可用，并返回服务时间。",
)
def health() -> Dict[str, str]:
    return {"status": "ok", "time": _now_iso()}


@app.get(
    "/meta/login-url-870",
    tags=["meta"],
    summary="获取 870 登录页地址",
    description="从配置文件解析 870 登录页 URL，用于引导手动登录。",
)
def get_login_url_870(
    config: str = Query(
        default="config.yaml",
        description="配置文件路径（可绝对路径或项目相对路径）。",
        examples=["config.yaml"],
    )
) -> Dict[str, str]:
    root = _project_root()
    config_path = _resolve_config_path(root, config)
    return {"login_url_870": _resolve_870_login_url(config_path)}


@app.post(
    "/jobs/report",
    tags=["jobs"],
    response_model=JobStatusResponse,
    summary="启动日报任务",
    description=(
        "启动一次日报生成任务。为了避免登录态冲突，服务端限制同一时刻最多 1 个运行中任务。"
    ),
    responses={
        400: {
            "description": "参数错误，例如日期格式不正确或配置文件不存在。",
            "content": {"application/json": {"example": {"detail": "date must be YYYY-MM-DD"}}},
        },
        401: {
            "description": "API Token 错误（仅在配置 REPORT_API_TOKEN 时出现）。",
            "content": {"application/json": {"example": {"detail": "invalid api token"}}},
        },
        409: {
            "description": "已有运行中任务，触发并发保护。",
            "content": {"application/json": {"example": {"detail": "已有运行中任务: ab12cd34ef56"}}},
        },
    },
)
def run_report_job(req: RunReportRequest, _: None = Depends(_require_api_token)) -> JobStatusResponse:
    root = _project_root()
    try:
        cmd = _build_report_command(root, req)
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc

    try:
        job = store.create(cmd)
    except RuntimeError as exc:
        raise HTTPException(status_code=409, detail=str(exc)) from exc

    t = threading.Thread(target=_run_job_thread, args=(root, job.job_id, cmd), daemon=True)
    t.start()
    return job.to_status()


@app.get(
    "/jobs",
    tags=["jobs"],
    response_model=List[JobStatusResponse],
    summary="获取任务列表",
    description="按创建时间倒序返回任务列表，最新任务在最前。",
    responses={
        401: {
            "description": "API Token 错误。",
            "content": {"application/json": {"example": {"detail": "invalid api token"}}},
        }
    },
)
def list_jobs(_: None = Depends(_require_api_token)) -> List[JobStatusResponse]:
    jobs = sorted(store.list(), key=lambda x: x.created_at, reverse=True)
    return [j.to_status() for j in jobs]


@app.get(
    "/jobs/{job_id}",
    tags=["jobs"],
    response_model=JobStatusResponse,
    summary="查询任务状态",
    description="通过 job_id 获取单个任务的当前状态、进度、执行命令和飞书链接。",
    responses={
        401: {
            "description": "API Token 错误。",
            "content": {"application/json": {"example": {"detail": "invalid api token"}}},
        },
        404: {
            "description": "任务不存在。",
            "content": {"application/json": {"example": {"detail": "job not found"}}},
        },
    },
)
def get_job(job_id: str, _: None = Depends(_require_api_token)) -> JobStatusResponse:
    try:
        return store.get(job_id).to_status()
    except KeyError as exc:
        raise HTTPException(status_code=404, detail="job not found") from exc


@app.get(
    "/jobs/{job_id}/logs",
    tags=["jobs"],
    response_model=JobLogsResponse,
    summary="获取任务日志",
    description="获取任务的最近日志片段，可用于前端轮询显示实时进度。",
    responses={
        401: {
            "description": "API Token 错误。",
            "content": {"application/json": {"example": {"detail": "invalid api token"}}},
        },
        404: {
            "description": "任务不存在。",
            "content": {"application/json": {"example": {"detail": "job not found"}}},
        },
    },
)
def get_job_logs(
    job_id: str,
    limit: int = Query(
        300,
        gt=0,
        le=MAX_LOGS_API_LIMIT,
        description=f"返回日志行数，范围 1-{MAX_LOGS_API_LIMIT}。",
    ),
    _: None = Depends(_require_api_token),
) -> JobLogsResponse:
    try:
        job = store.get(job_id)
    except KeyError as exc:
        raise HTTPException(status_code=404, detail="job not found") from exc
    return JobLogsResponse(
        job_id=job.job_id,
        status=job.status,
        progress=job.progress,
        stage=job.stage,
        log_lines=job.log_lines[-limit:],
    )


@app.post(
    "/jobs/{job_id}/cancel",
    tags=["jobs"],
    response_model=JobStatusResponse,
    summary="取消任务",
    description="请求终止指定任务。若进程正在运行会发送 terminate 信号。",
    responses={
        401: {
            "description": "API Token 错误。",
            "content": {"application/json": {"example": {"detail": "invalid api token"}}},
        },
        404: {
            "description": "任务不存在。",
            "content": {"application/json": {"example": {"detail": "job not found"}}},
        },
    },
)
def cancel_job(job_id: str, _: None = Depends(_require_api_token)) -> JobStatusResponse:
    try:
        store.request_cancel(job_id)
        return store.get(job_id).to_status()
    except KeyError as exc:
        raise HTTPException(status_code=404, detail="job not found") from exc


if __name__ == "__main__":
    import uvicorn

    uvicorn.run("fastapi_app:app", host="127.0.0.1", port=8000, reload=False)
