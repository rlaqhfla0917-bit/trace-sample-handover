"""Validated, session-only synthetic sample registration for public TRACE demo.

No database, disk persistence, photo or signature handling is used here.
"""
import math
import re
from datetime import datetime
from zoneinfo import ZoneInfo

KST = ZoneInfo("Asia/Seoul")
CODE_FORMAT = re.compile(r"[A-Za-z0-9_-]{3,60}\Z")
MAX_FIELDS = {"label": 100, "project": 100, "custodian": 60, "location": 100, "notes": 300}
VALID_UNITS = {"병", "봉투", "개", "튜브", "통"}
VALID_TYPES = {"해수", "퇴적물", "저서생물", "식물플랑크톤", "동물플랑크톤", "기타"}


def create_demo_specimen(values, existing, now=None):
    """Return a new synthetic specimen, rejecting invalid/duplicate sample codes."""
    code = str(values.get("code") or "").strip().upper()
    if not CODE_FORMAT.fullmatch(code):
        raise ValueError("시료코드는 3~60자의 영문, 숫자, 하이픈(-), 밑줄(_)만 사용할 수 있어요.")
    if any(code.casefold() == str(item.get("code", "")).casefold() for item in existing):
        raise ValueError("이미 등록된 시료코드예요. 다른 코드를 입력해 주세요.")
    safe = {}
    for name, length in MAX_FIELDS.items():
        val = str(values.get(name) or "").strip()
        if name != "notes" and not val:
            raise ValueError("필수 항목을 모두 입력해 주세요.")
        if len(val) > length or any(ch in val for ch in "\x00\r\n"):
            raise ValueError(f"{name} 값을 확인해 주세요. (최대 {length}자, 한 줄 입력)")
        safe[name] = val
    kind = str(values.get("type") or "").strip()
    unit = str(values.get("unit") or "").strip()
    if kind not in VALID_TYPES or unit not in VALID_UNITS:
        raise ValueError("시료 유형 또는 수량 단위를 확인해 주세요.")
    try:
        quantity = float(values.get("quantity"))
    except (TypeError, ValueError):
        raise ValueError("수량은 올바른 숫자여야 해요.") from None
    if not math.isfinite(quantity) or not 0 < quantity <= 999999:
        raise ValueError("수량은 0보다 크고 999,999 이하이어야 해요.")
    now = now or datetime.now(KST)
    return {
        "code": code,
        "label": safe["label"],
        "type": kind,
        "qty": f"{quantity:g}{unit}",
        "project": safe["project"],
        "location": safe["location"],
        "custodian": safe["custodian"],
        "status": "보관 중",
        "notes": safe["notes"],
        "created_at": now.strftime("%Y-%m-%d %H:%M"),
        "history": [("등록", safe["custodian"], safe["location"])],
    }


def safe_csv_cell(value):
    """Prevent spreadsheet formula execution when users open the exported CSV."""
    if not isinstance(value, str):
        return value
    if value.lstrip().startswith(("=", "+", "-", "@")) or any(c in value for c in "\r\n\t"):
        return "'" + value.replace("\r", " ").replace("\n", " ").replace("\t", " ")
    return value
