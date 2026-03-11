from __future__ import annotations

from dataclasses import dataclass
from datetime import date
import mimetypes
import re
import tempfile
import time
import uuid
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

import requests

_TABLE_FONT_CONFIGURED = False
_RETRYABLE_FEISHU_CODES = {1061001, 1061006, 1061045}
_RETRYABLE_STATUS_CODES = {429, 500, 502, 503, 504}
_MAX_HTTP_ATTEMPTS = 4


class FeishuDocError(RuntimeError):
    """Raised when Feishu doc API returns an error."""


@dataclass
class FeishuDocSettings:
    app_id: str
    app_secret: str
    folder_token: str = ""
    doc_url_prefix: str = "https://www.feishu.cn/docx/"
    timeout: int = 30
    api_base: str = "https://open.feishu.cn"
    image_width: int = 960
    narrow_image_width: int = 760
    tall_ratio_threshold: float = 1.9
    prevent_upscale: bool = True
    enable_auto_trim: bool = True
    trim_background_threshold: float = 0.985
    trim_padding: int = 4
    verify_content_after_publish: bool = False
    verify_content_lang: str = "zh"
    auto_share_tenant_members: bool = False
    auto_share_mode: str = "read"
    auto_share_strict: bool = False


def _safe_json(response: requests.Response) -> Dict[str, Any]:
    try:
        payload = response.json()
    except ValueError as exc:  # pragma: no cover - depends on remote API response
        raise FeishuDocError(f"飞书接口返回非JSON响应: HTTP {response.status_code}") from exc
    if not isinstance(payload, dict):
        raise FeishuDocError(f"飞书接口响应格式异常: HTTP {response.status_code}")
    return payload


def _is_retryable_request_exception(exc: Exception) -> bool:
    return isinstance(
        exc,
        (
            requests.Timeout,
            requests.ConnectionError,
            requests.exceptions.SSLError,
            requests.exceptions.ChunkedEncodingError,
        ),
    )


def _retry_sleep(attempt: int) -> None:
    # Short bounded backoff keeps UX responsive while masking transient network spikes.
    delay = min(2.5, 0.5 * (2 ** max(0, attempt - 1)))
    time.sleep(delay)


def _request_with_retry(
    *,
    label: str,
    sender,
    max_attempts: int = _MAX_HTTP_ATTEMPTS,
) -> requests.Response:
    last_exc: Optional[Exception] = None
    for attempt in range(1, max_attempts + 1):
        try:
            return sender()
        except requests.RequestException as exc:
            last_exc = exc
            if attempt >= max_attempts or not _is_retryable_request_exception(exc):
                raise
            _retry_sleep(attempt)
    if last_exc is not None:
        raise requests.RequestException(f"{label} failed after retries") from last_exc
    raise requests.RequestException(f"{label} failed: unknown error")


def _api_request(
    method: str,
    url: str,
    timeout: int,
    headers: Optional[Dict[str, str]] = None,
    params: Optional[Dict[str, Any]] = None,
    json_body: Optional[Dict[str, Any]] = None,
) -> Dict[str, Any]:
    last_error: Optional[Exception] = None
    for attempt in range(1, _MAX_HTTP_ATTEMPTS + 1):
        try:
            response = _request_with_retry(
                label=f"{method.upper()} {url}",
                sender=lambda: requests.request(
                    method=method.upper(),
                    url=url,
                    headers=headers,
                    params=params,
                    json=json_body,
                    timeout=timeout,
                ),
            )
        except requests.RequestException as exc:
            raise FeishuDocError(f"飞书接口请求失败: {exc}") from exc

        if response.status_code in _RETRYABLE_STATUS_CODES and attempt < _MAX_HTTP_ATTEMPTS:
            _retry_sleep(attempt)
            continue
        try:
            payload = _safe_json(response)
        except FeishuDocError as exc:
            last_error = exc
            if response.status_code in _RETRYABLE_STATUS_CODES and attempt < _MAX_HTTP_ATTEMPTS:
                _retry_sleep(attempt)
                continue
            raise
        code = payload.get("code")
        if code in (0, "0"):
            data = payload.get("data")
            if not isinstance(data, dict):
                return {}
            return data
        msg = payload.get("msg") or payload.get("message") or "unknown error"
        error = FeishuDocError(f"飞书接口失败(code={code}): {msg}")
        last_error = error
        retryable_code = False
        try:
            retryable_code = int(code) in _RETRYABLE_FEISHU_CODES
        except (TypeError, ValueError):
            retryable_code = False
        if retryable_code and attempt < _MAX_HTTP_ATTEMPTS:
            _retry_sleep(attempt)
            continue
        raise error

    if last_error is not None:
        raise last_error
    raise FeishuDocError("飞书接口失败：未知错误")


def _fetch_tenant_access_token(settings: FeishuDocSettings) -> str:
    response = _request_with_retry(
        label="fetch tenant access token",
        sender=lambda: requests.post(
            f"{settings.api_base.rstrip('/')}/open-apis/auth/v3/tenant_access_token/internal",
            json={"app_id": settings.app_id, "app_secret": settings.app_secret},
            timeout=settings.timeout,
        ),
    )
    payload = _safe_json(response)
    code = payload.get("code")
    if code not in (0, "0"):
        msg = payload.get("msg") or payload.get("message") or "unknown error"
        raise FeishuDocError(f"飞书鉴权失败(code={code}): {msg}")
    token = str(payload.get("tenant_access_token") or "").strip()
    if not token:
        raise FeishuDocError("飞书鉴权失败：未返回 tenant_access_token")
    return token


def _create_document(settings: FeishuDocSettings, token: str, title: str) -> str:
    body: Dict[str, Any] = {"title": title}
    folder_token = settings.folder_token.strip()
    if folder_token:
        body["folder_token"] = folder_token
    data = _api_request(
        method="POST",
        url=f"{settings.api_base.rstrip('/')}/open-apis/docx/v1/documents",
        timeout=settings.timeout,
        headers={"Authorization": f"Bearer {token}", "Content-Type": "application/json; charset=utf-8"},
        json_body=body,
    )
    document = data.get("document")
    if not isinstance(document, dict):
        raise FeishuDocError("飞书文档创建失败：响应缺少 document 字段")
    document_id = str(document.get("document_id") or "").strip()
    if not document_id:
        raise FeishuDocError("飞书文档创建失败：响应缺少 document_id")
    return document_id


def _set_document_tenant_share(
    settings: FeishuDocSettings,
    token: str,
    document_id: str,
) -> str:
    mode = str(settings.auto_share_mode or "read").strip().lower()
    if mode not in {"read", "edit"}:
        raise FeishuDocError(f"飞书自动共享模式不支持: {mode}")

    if mode == "edit":
        link_share_entity = "tenant_editable"
        security_entity = "anyone_can_edit"
        comment_entity = "anyone_can_edit"
    else:
        link_share_entity = "tenant_readable"
        security_entity = "anyone_can_view"
        comment_entity = "anyone_can_view"

    body = {
        "external_access": False,
        "security_entity": security_entity,
        "comment_entity": comment_entity,
        "share_entity": "anyone",
        "link_share_entity": link_share_entity,
        "invite_external": False,
    }
    last_error: Optional[Exception] = None
    # Feishu environments differ on `type` value (docx/doc); try both.
    for doc_type in ("docx", "doc"):
        try:
            _api_request(
                method="PATCH",
                url=f"{settings.api_base.rstrip('/')}/open-apis/drive/v1/permissions/{document_id}/public",
                timeout=settings.timeout,
                headers={"Authorization": f"Bearer {token}", "Content-Type": "application/json; charset=utf-8"},
                params={"type": doc_type},
                json_body=body,
            )
            return link_share_entity
        except Exception as exc:  # noqa: BLE001
            last_error = exc
    if last_error is None:
        raise FeishuDocError("飞书自动共享失败：未知错误")
    raise FeishuDocError(f"飞书自动共享失败: {last_error}")


def _list_blocks(settings: FeishuDocSettings, token: str, document_id: str) -> List[Dict[str, Any]]:
    items: List[Dict[str, Any]] = []
    page_token = ""
    while True:
        params: Dict[str, Any] = {"page_size": 200}
        if page_token:
            params["page_token"] = page_token
        data = _api_request(
            method="GET",
            url=f"{settings.api_base.rstrip('/')}/open-apis/docx/v1/documents/{document_id}/blocks",
            timeout=settings.timeout,
            headers={"Authorization": f"Bearer {token}"},
            params=params,
        )
        batch = data.get("items")
        if isinstance(batch, list):
            items.extend([item for item in batch if isinstance(item, dict)])
        has_more = bool(data.get("has_more"))
        if not has_more:
            break
        page_token = str(data.get("page_token") or "").strip()
        if not page_token:
            break
    return items


def _resolve_root_block_id(document_id: str, blocks: List[Dict[str, Any]]) -> str:
    for block in blocks:
        if int(block.get("block_type") or 0) != 1:
            continue
        parent_id = str(block.get("parent_id") or "").strip()
        block_id = str(block.get("block_id") or "").strip()
        if block_id and not parent_id:
            return block_id
    for block in blocks:
        block_id = str(block.get("block_id") or "").strip()
        if block_id == document_id:
            return block_id
    return document_id


def _split_for_docx(text: str, max_len: int = 1200) -> List[str]:
    line = text.rstrip("\n")
    if not line:
        return []
    parts: List[str] = []
    idx = 0
    while idx < len(line):
        parts.append(line[idx : idx + max_len])
        idx += max_len
    return parts


def _to_text_children(report_text: str) -> List[Dict[str, Any]]:
    children: List[Dict[str, Any]] = []
    for line in report_text.replace("\r", "").split("\n"):
        for chunk in _split_for_docx(line):
            children.append(
                {
                    "block_type": 2,
                    "text": {
                        "elements": [
                            {
                                "text_run": {
                                    "content": chunk,
                                }
                            }
                        ]
                    },
                }
            )
    if not children:
        children.append(
            {
                "block_type": 2,
                "text": {
                    "elements": [
                        {
                            "text_run": {
                                "content": "日报内容为空",
                            }
                        }
                    ]
                },
            }
        )
    return children


def _insert_children(
    settings: FeishuDocSettings,
    token: str,
    document_id: str,
    root_block_id: str,
    children: List[Dict[str, Any]],
) -> None:
    # Split into batches to avoid field validation failures on large payloads.
    batch_size = 50
    insert_index = 0
    for offset in range(0, len(children), batch_size):
        batch = children[offset : offset + batch_size]
        _api_request(
            method="POST",
            url=f"{settings.api_base.rstrip('/')}/open-apis/docx/v1/documents/{document_id}/blocks/{root_block_id}/children",
            timeout=settings.timeout,
            headers={"Authorization": f"Bearer {token}", "Content-Type": "application/json; charset=utf-8"},
            params={"document_revision_id": -1},
            json_body={"index": insert_index, "children": batch},
        )
        insert_index += len(batch)


def _guess_mime(path: Path) -> str:
    guessed, _ = mimetypes.guess_type(str(path))
    return guessed or "application/octet-stream"


def _append_text_blocks(
    settings: FeishuDocSettings,
    token: str,
    document_id: str,
    root_block_id: str,
    index: int,
    lines: List[str],
) -> int:
    if not lines:
        return 0
    children: List[Dict[str, Any]] = []
    for line in lines:
        content = str(line).rstrip("\n")
        if not content:
            continue
        children.append(
            {
                "block_type": 2,
                "text": {
                    "elements": [
                        {
                            "text_run": {
                                "content": content,
                            }
                        }
                    ]
                },
            }
        )
    if not children:
        return 0
    _api_request(
        method="POST",
        url=f"{settings.api_base.rstrip('/')}/open-apis/docx/v1/documents/{document_id}/blocks/{root_block_id}/children",
        timeout=settings.timeout,
        headers={"Authorization": f"Bearer {token}", "Content-Type": "application/json; charset=utf-8"},
        params={"document_revision_id": -1},
        json_body={"index": index, "children": children},
    )
    return len(children)


def _create_image_placeholder(
    settings: FeishuDocSettings,
    token: str,
    document_id: str,
    root_block_id: str,
    index: int,
) -> str:
    temp_id = f"tmp_img_{uuid.uuid4().hex}"
    data = _api_request(
        method="POST",
        url=f"{settings.api_base.rstrip('/')}/open-apis/docx/v1/documents/{document_id}/blocks/{root_block_id}/descendant",
        timeout=settings.timeout,
        headers={"Authorization": f"Bearer {token}", "Content-Type": "application/json; charset=utf-8"},
        params={"document_revision_id": -1},
        json_body={
            "children_id": [temp_id],
            "index": index,
            "descendants": [{"block_id": temp_id, "block_type": 27, "image": {}}],
        },
    )
    relations = data.get("block_id_relations")
    if not isinstance(relations, list):
        raise FeishuDocError("飞书图片占位块创建失败：缺少 block_id_relations")
    for item in relations:
        if not isinstance(item, dict):
            continue
        if str(item.get("temporary_block_id") or "") == temp_id:
            real_id = str(item.get("block_id") or "").strip()
            if real_id:
                return real_id
    raise FeishuDocError("飞书图片占位块创建失败：无法解析 block_id")


def _upload_image_token_for_block(
    settings: FeishuDocSettings,
    token: str,
    image_path: Path,
    image_block_id: str,
    document_id: str,
) -> str:
    if not image_path.exists():
        raise FeishuDocError(f"图片文件不存在：{image_path}")
    file_size = image_path.stat().st_size
    response: Optional[requests.Response] = None
    request_error: Optional[Exception] = None
    for attempt in range(1, _MAX_HTTP_ATTEMPTS + 1):
        try:
            with image_path.open("rb") as fh:
                response = requests.post(
                    f"{settings.api_base.rstrip('/')}/open-apis/drive/v1/medias/upload_all",
                    headers={"Authorization": f"Bearer {token}"},
                    data={
                        "file_name": image_path.name,
                        "parent_type": "docx_image",
                        "parent_node": image_block_id,
                        "size": str(file_size),
                        "extra": f'{{"drive_route_token":"{document_id}"}}',
                    },
                    files={"file": (image_path.name, fh, _guess_mime(image_path))},
                    timeout=settings.timeout,
                )
        except requests.RequestException as exc:
            request_error = exc
            if attempt >= _MAX_HTTP_ATTEMPTS or not _is_retryable_request_exception(exc):
                raise FeishuDocError(f"飞书图片上传请求失败: {exc}") from exc
            _retry_sleep(attempt)
            continue

        if response.status_code in _RETRYABLE_STATUS_CODES and attempt < _MAX_HTTP_ATTEMPTS:
            _retry_sleep(attempt)
            continue

        payload = _safe_json(response)
        code = payload.get("code")
        if code in (0, "0"):
            token_value = str(((payload.get("data") or {}).get("file_token") or "")).strip()
            if not token_value:
                raise FeishuDocError("飞书图片上传失败：未返回 file_token")
            return token_value

        msg = payload.get("msg") or payload.get("message") or "unknown error"
        retryable_code = False
        try:
            retryable_code = int(code) in _RETRYABLE_FEISHU_CODES
        except (TypeError, ValueError):
            retryable_code = False
        if retryable_code and attempt < _MAX_HTTP_ATTEMPTS:
            _retry_sleep(attempt)
            continue
        raise FeishuDocError(f"飞书图片上传失败(code={code}): {msg}")

    if response is None:
        if request_error is not None:
            raise FeishuDocError(f"飞书图片上传请求失败: {request_error}") from request_error
        raise FeishuDocError("飞书图片上传失败：未获得响应")
    raise FeishuDocError("飞书图片上传失败：重试耗尽")


def _replace_image_for_block(
    settings: FeishuDocSettings,
    token: str,
    document_id: str,
    image_block_id: str,
    image_token: str,
    image_width: int,
    image_height: int,
) -> None:
    _api_request(
        method="PATCH",
        url=f"{settings.api_base.rstrip('/')}/open-apis/docx/v1/documents/{document_id}/blocks/{image_block_id}",
        timeout=settings.timeout,
        headers={"Authorization": f"Bearer {token}", "Content-Type": "application/json; charset=utf-8"},
        params={"document_revision_id": -1},
        json_body={"replace_image": {"token": image_token, "width": int(image_width), "height": int(image_height)}},
    )


def _read_image_size(image_path: Path) -> Optional[Tuple[int, int]]:
    try:
        import matplotlib.image as mpimg
    except ImportError:
        return None
    try:
        arr = mpimg.imread(image_path)
    except Exception:  # noqa: BLE001
        return None
    if getattr(arr, "ndim", 0) < 2:
        return None
    height = int(arr.shape[0])
    width = int(arr.shape[1])
    if width <= 0 or height <= 0:
        return None
    return (width, height)


def _trim_image_whitespace(settings: FeishuDocSettings, image_path: Path, temp_root: Path) -> Tuple[Path, Optional[Tuple[int, int]]]:
    if not settings.enable_auto_trim:
        return image_path, _read_image_size(image_path)
    try:
        import matplotlib.image as mpimg
        import matplotlib.pyplot as plt
        import numpy as np
    except ImportError:
        return image_path, _read_image_size(image_path)

    try:
        arr = mpimg.imread(image_path)
    except Exception:  # noqa: BLE001
        return image_path, _read_image_size(image_path)
    if getattr(arr, "ndim", 0) < 2:
        return image_path, None

    height = int(arr.shape[0])
    width = int(arr.shape[1])
    if width <= 0 or height <= 0:
        return image_path, None

    threshold = float(settings.trim_background_threshold)
    if arr.ndim == 2:
        mask = arr < threshold
    else:
        rgb = arr[:, :, :3]
        mask = np.any(rgb < threshold, axis=2)
        if arr.shape[2] >= 4:
            alpha = arr[:, :, 3]
            mask = mask | (alpha < 0.995)

    ys, xs = np.where(mask)
    if ys.size == 0 or xs.size == 0:
        return image_path, (width, height)

    pad = max(0, int(settings.trim_padding))
    y_min = max(0, int(ys.min()) - pad)
    y_max = min(height - 1, int(ys.max()) + pad)
    x_min = max(0, int(xs.min()) - pad)
    x_max = min(width - 1, int(xs.max()) + pad)

    if x_min == 0 and y_min == 0 and x_max == width - 1 and y_max == height - 1:
        return image_path, (width, height)

    cropped = arr[y_min : y_max + 1, x_min : x_max + 1]
    crop_h = int(cropped.shape[0])
    crop_w = int(cropped.shape[1])
    if crop_w <= 0 or crop_h <= 0:
        return image_path, (width, height)
    if crop_w >= int(width * 0.98) and crop_h >= int(height * 0.98):
        return image_path, (width, height)

    out_path = temp_root / f"trim_{uuid.uuid4().hex}.png"
    plt.imsave(out_path, cropped)
    return out_path, (crop_w, crop_h)


def _suggest_image_width(settings: FeishuDocSettings, image_path: Path, image_size: Optional[Tuple[int, int]]) -> int:
    target = int(settings.image_width)
    narrow = int(settings.narrow_image_width)
    name = image_path.name.lower()

    if "505_page_payment_table" in name or "505_mobile_payment_table" in name:
        target = min(target, narrow)

    if image_size:
        width, height = image_size
        if width > 0:
            ratio = float(height) / float(width)
            if ratio >= float(settings.tall_ratio_threshold):
                target = min(target, narrow)
            elif ratio >= 1.5:
                target = min(target, max(narrow + 60, 820))

    return max(560, target)


def _compute_target_dimensions(
    settings: FeishuDocSettings,
    image_path: Path,
    image_size: Optional[Tuple[int, int]],
) -> Tuple[int, int]:
    if not image_size:
        fallback_width = max(560, int(settings.image_width))
        # Use a conservative 4:3 fallback when actual size is unknown.
        return fallback_width, max(420, int(round(fallback_width * 0.75)))
    src_w, src_h = image_size
    if src_w <= 0 or src_h <= 0:
        fallback_width = max(560, int(settings.image_width))
        return fallback_width, max(420, int(round(fallback_width * 0.75)))

    target_w = _suggest_image_width(settings=settings, image_path=image_path, image_size=image_size)
    if settings.prevent_upscale:
        target_w = min(target_w, int(src_w))
        target_w = max(320, target_w)
    target_h = max(320, int(round(target_w * float(src_h) / float(src_w))))
    return target_w, target_h


def _split_pipe_row(line: str) -> List[str]:
    text = line.strip()
    if text.startswith("|"):
        text = text[1:]
    if text.endswith("|"):
        text = text[:-1]
    return [cell.strip() for cell in text.split("|")]


def _is_markdown_table_line(line: str) -> bool:
    text = line.strip()
    return text.startswith("|") and text.count("|") >= 2


def _render_markdown_table_image(table_lines: List[str], output_path: Path) -> bool:
    rows = [_split_pipe_row(line) for line in table_lines if line.strip()]
    if not rows:
        return False
    has_align = len(rows) > 1 and all(re.fullmatch(r":?-{3,}:?", cell or "") for cell in rows[1])
    header = rows[0]
    body = rows[2:] if has_align else rows[1:]
    if not header:
        return False
    try:
        import matplotlib.pyplot as plt
        from matplotlib import font_manager
        import matplotlib
    except ImportError:
        return False

    global _TABLE_FONT_CONFIGURED  # pylint: disable=global-statement
    if not _TABLE_FONT_CONFIGURED:
        preferred_fonts = [
            "Microsoft YaHei",
            "Microsoft YaHei UI",
            "Microsoft JhengHei",
            "PingFang SC",
            "Hiragino Sans GB",
            "Noto Sans CJK SC",
            "SimHei",
            "SimSun",
        ]
        for font_name in preferred_fonts:
            try:
                font_manager.findfont(font_name, fallback_to_default=False)
            except (ValueError, RuntimeError):
                continue
            matplotlib.rcParams["font.sans-serif"] = [font_name]
            matplotlib.rcParams["font.family"] = "sans-serif"
            matplotlib.rcParams["axes.unicode_minus"] = False
            break
        _TABLE_FONT_CONFIGURED = True

    cell_text = [header] + body
    row_count = max(1, len(cell_text))
    col_count = max(1, len(header))
    fig_width = max(8.0, min(24.0, col_count * 3.8))
    fig_height = max(1.8, min(24.0, row_count * 0.5 + 0.5))

    fig, ax = plt.subplots(figsize=(fig_width, fig_height), dpi=220)
    ax.axis("off")
    table = ax.table(cellText=cell_text, loc="center", cellLoc="center")
    table.auto_set_font_size(False)
    table.set_fontsize(11)
    table.scale(1.0, 1.28)
    for (row, _col), cell in table.get_celld().items():
        cell.set_edgecolor("#4f4f4f")
        cell.set_linewidth(0.6)
        if row == 0:
            cell.set_facecolor("#E8F4DC")
            cell.get_text().set_weight("bold")
        else:
            cell.set_facecolor("#F6F6F6")
    output_path.parent.mkdir(parents=True, exist_ok=True)
    fig.subplots_adjust(left=0.01, right=0.99, top=0.99, bottom=0.01)
    fig.tight_layout()
    fig.savefig(output_path, bbox_inches="tight", pad_inches=0.02)
    plt.close(fig)
    return True


def _resolve_path(path_text: str, report_base_dir: Path) -> Optional[Path]:
    raw = str(path_text or "").strip()
    if not raw:
        return None
    p = Path(raw)
    if p.is_absolute():
        return p
    return (report_base_dir / p).resolve()


def _default_chart_markers(report_base_dir: Path) -> Dict[str, Path]:
    charts_dir = (report_base_dir / "charts").resolve()
    return {
        "[总路线图片]": charts_dir / "total.png",
        "[页游图片]": charts_dir / "page.png",
        "[主机图片]": charts_dir / "console.png",
        "[手游图片]": charts_dir / "mobile.png",
        "[原神图片]": charts_dir / "genshin.png",
        "[星铁图片]": charts_dir / "starrail.png",
        "[绝区零图片]": charts_dir / "zzz.png",
        "[高画质图片]": charts_dir / "high_quality.png",
        "[pc云游戏图片]": charts_dir / "pc_cloud.png",
    }


def _build_report_segments(
    report_text: str,
    report_base_dir: Path,
    temp_root: Path,
    chart_image_paths: Optional[Dict[str, str]],
    payment_images: Optional[Dict[str, str]],
) -> List[Tuple[str, str]]:
    chart_image_paths = chart_image_paths or {}
    payment_images = payment_images or {}

    marker_to_path = _default_chart_markers(report_base_dir)
    custom_marker_map = {
        "[总路线图片]": chart_image_paths.get("total", ""),
        "[页游图片]": chart_image_paths.get("page", ""),
        "[主机图片]": chart_image_paths.get("console", ""),
        "[手游图片]": chart_image_paths.get("mobile", ""),
        "[原神图片]": chart_image_paths.get("genshin", ""),
        "[星铁图片]": chart_image_paths.get("starrail", ""),
        "[绝区零图片]": chart_image_paths.get("zzz", ""),
        "[高画质图片]": chart_image_paths.get("high_quality", ""),
        "[pc云游戏图片]": chart_image_paths.get("pc_cloud", ""),
    }
    for marker, rel_path in custom_marker_map.items():
        resolved = _resolve_path(str(rel_path or ""), report_base_dir)
        if resolved is not None:
            marker_to_path[marker] = resolved

    page_payment = _resolve_path(str(payment_images.get("page", "") or ""), report_base_dir)
    mobile_payment = _resolve_path(str(payment_images.get("mobile", "") or ""), report_base_dir)

    segments: List[Tuple[str, str]] = []
    lines = report_text.replace("\r", "").split("\n")
    idx = 0
    table_idx = 0
    while idx < len(lines):
        line = lines[idx]
        stripped = line.strip()

        if stripped in marker_to_path:
            image_path = marker_to_path[stripped]
            if image_path.exists():
                segments.append(("image", str(image_path)))
            idx += 1
            continue

        if stripped.startswith("页游付费表图片："):
            path_text = stripped.split("：", 1)[1].strip()
            image_path = _resolve_path(path_text, report_base_dir) or page_payment
            if image_path is not None and image_path.exists():
                segments.append(("image", str(image_path)))
            idx += 1
            continue

        if stripped.startswith("手游付费表图片："):
            path_text = stripped.split("：", 1)[1].strip()
            image_path = _resolve_path(path_text, report_base_dir) or mobile_payment
            if image_path is not None and image_path.exists():
                segments.append(("image", str(image_path)))
            idx += 1
            continue

        if _is_markdown_table_line(line):
            table_lines = [line]
            idx += 1
            while idx < len(lines) and _is_markdown_table_line(lines[idx]):
                table_lines.append(lines[idx])
                idx += 1
            table_idx += 1
            table_image = temp_root / f"table_{table_idx}.png"
            if _render_markdown_table_image(table_lines, table_image):
                segments.append(("image", str(table_image)))
            else:
                for raw in table_lines:
                    segments.append(("text", raw.strip()))
            continue

        segments.append(("text", stripped))
        idx += 1

    return segments


def _build_document_title(report_date: date, title_override: str, title_prefix: str) -> str:
    override = title_override.strip()
    if override:
        return override
    prefix = title_prefix.strip() or "云游戏日报"
    return f"{prefix}_{report_date.strftime('%Y%m%d')}"


def _build_document_url(prefix: str, document_id: str) -> str:
    base = prefix.strip() or "https://www.feishu.cn/docx/"
    if not base.endswith("/"):
        base = base + "/"
    return f"{base}{document_id}"


def _fetch_doc_markdown_content(
    settings: FeishuDocSettings,
    token: str,
    document_id: str,
) -> str:
    response = _request_with_retry(
        label="fetch docs content",
        sender=lambda: requests.get(
            f"{settings.api_base.rstrip('/')}/open-apis/docs/v1/content",
            headers={"Authorization": f"Bearer {token}"},
            params={
                "doc_token": document_id,
                "doc_type": "docx",
                "content_type": "markdown",
                "lang": settings.verify_content_lang or "zh",
            },
            timeout=settings.timeout,
        ),
    )
    payload = _safe_json(response)
    code = payload.get("code")
    if code not in (0, "0"):
        msg = payload.get("msg") or payload.get("message") or "unknown error"
        raise FeishuDocError(f"飞书文档内容校验失败(code={code}): {msg}")
    data = payload.get("data")
    if not isinstance(data, dict):
        return ""
    content = data.get("content")
    return str(content or "")


def publish_report_to_feishu_doc(
    settings: FeishuDocSettings,
    report_text: str,
    report_date: date,
    title_override: str = "",
    title_prefix: str = "云游戏日报",
    report_base_dir: Optional[Path] = None,
    chart_image_paths: Optional[Dict[str, str]] = None,
    payment_images: Optional[Dict[str, str]] = None,
) -> Dict[str, str]:
    token = _fetch_tenant_access_token(settings)
    title = _build_document_title(report_date=report_date, title_override=title_override, title_prefix=title_prefix)
    document_id = _create_document(settings=settings, token=token, title=title)
    share_scope = ""
    share_error = ""
    if settings.auto_share_tenant_members:
        try:
            share_scope = _set_document_tenant_share(settings=settings, token=token, document_id=document_id)
        except Exception as exc:  # noqa: BLE001
            if settings.auto_share_strict:
                raise
            share_error = str(exc)
    blocks = _list_blocks(settings=settings, token=token, document_id=document_id)
    root_block_id = _resolve_root_block_id(document_id=document_id, blocks=blocks)
    base_dir = (report_base_dir or Path.cwd()).resolve()
    with tempfile.TemporaryDirectory(prefix="feishu_doc_") as temp_dir:
        temp_root = Path(temp_dir)
        segments = _build_report_segments(
            report_text=report_text,
            report_base_dir=base_dir,
            temp_root=temp_root,
            chart_image_paths=chart_image_paths,
            payment_images=payment_images,
        )
        insert_index = 0
        text_buffer: List[str] = []
        for kind, payload in segments:
            if kind == "text":
                text_buffer.append(payload)
                continue
            if text_buffer:
                inserted = _append_text_blocks(
                    settings=settings,
                    token=token,
                    document_id=document_id,
                    root_block_id=root_block_id,
                    index=insert_index,
                    lines=text_buffer,
                )
                insert_index += inserted
                text_buffer = []
            image_path = Path(payload)
            if not image_path.exists():
                continue
            prepared_image_path, prepared_size = _trim_image_whitespace(
                settings=settings,
                image_path=image_path,
                temp_root=temp_root,
            )
            target_width, target_height = _compute_target_dimensions(
                settings=settings,
                image_path=image_path,
                image_size=prepared_size,
            )
            image_block_id = _create_image_placeholder(
                settings=settings,
                token=token,
                document_id=document_id,
                root_block_id=root_block_id,
                index=insert_index,
            )
            image_token = _upload_image_token_for_block(
                settings=settings,
                token=token,
                image_path=prepared_image_path,
                image_block_id=image_block_id,
                document_id=document_id,
            )
            _replace_image_for_block(
                settings=settings,
                token=token,
                document_id=document_id,
                image_block_id=image_block_id,
                image_token=image_token,
                image_width=target_width,
                image_height=target_height,
            )
            insert_index += 1
        if text_buffer:
            _append_text_blocks(
                settings=settings,
                token=token,
                document_id=document_id,
                root_block_id=root_block_id,
                index=insert_index,
                lines=text_buffer,
            )
    out = {
        "document_id": document_id,
        "title": title,
        "url": _build_document_url(settings.doc_url_prefix, document_id),
    }
    if settings.verify_content_after_publish:
        content = _fetch_doc_markdown_content(settings=settings, token=token, document_id=document_id)
        out["markdown_length"] = str(len(content))
    if settings.auto_share_tenant_members:
        if share_scope:
            out["share_scope"] = share_scope
            out["share_status"] = "ok"
        else:
            out["share_status"] = "warn"
            out["share_error"] = share_error or "unknown error"
    return out
