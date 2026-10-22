"""Sample handover prototype. Local demonstration only; not a production records system."""
from __future__ import annotations

import base64
import csv
import io
import os
import re
import secrets
import sqlite3
import uuid
from datetime import datetime
from contextlib import contextmanager
from pathlib import Path
from zoneinfo import ZoneInfo

from fastapi import FastAPI, File, Form, HTTPException, Request, UploadFile
from fastapi.responses import HTMLResponse, RedirectResponse, StreamingResponse
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates
from PIL import Image, UnidentifiedImageError, ImageOps

ROOT = Path(__file__).resolve().parent
BASE_DATA = Path(os.environ.get("HANDOVER_DATA_DIR", str(ROOT / "local_data")))
PHOTO_DIR = BASE_DATA / "photos"
SIG_DIR = BASE_DATA / "signatures"
DB_PATH = BASE_DATA / "handover.sqlite3"
TIMEZONE = ZoneInfo("Asia/Seoul")
MAX_UPLOAD = 5 * 1024 * 1024
MAX_SIGNATURE = 350 * 1024

for directory in [BASE_DATA, PHOTO_DIR, SIG_DIR]:
    directory.mkdir(parents=True, exist_ok=True)

app = FastAPI(title="TRACE | 시료 인수인계 관리", version="0.1.0")
app.mount("/static", StaticFiles(directory=str(ROOT / "static")), name="static")
app.mount("/media/photos", StaticFiles(directory=str(PHOTO_DIR)), name="photos")
app.mount("/media/signatures", StaticFiles(directory=str(SIG_DIR)), name="signatures")
templates = Jinja2Templates(directory=str(ROOT / "templates"))


def now_kr():
    return datetime.now(TIMEZONE).strftime("%Y-%m-%d %H:%M:%S")


@contextmanager
def connect():
    c = sqlite3.connect(DB_PATH, timeout=10)
    try:
        c.row_factory = sqlite3.Row
        c.execute("PRAGMA foreign_keys=ON")
        yield c
        c.commit()
    except Exception:
        c.rollback()
        raise
    finally:
        c.close()


def init_db():
    with connect() as db:
        db.executescript("""
        CREATE TABLE IF NOT EXISTS specimens (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            sample_code TEXT NOT NULL UNIQUE,
            label TEXT NOT NULL,
            sample_type TEXT NOT NULL,
            quantity REAL NOT NULL CHECK(quantity > 0),
            unit TEXT NOT NULL,
            project TEXT NOT NULL,
            current_location TEXT NOT NULL,
            current_custodian TEXT NOT NULL,
            status TEXT NOT NULL DEFAULT '보관 중',
            notes TEXT NOT NULL DEFAULT '',
            photo_path TEXT,
            created_at TEXT NOT NULL
        );
        CREATE TABLE IF NOT EXISTS movements (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            specimen_id INTEGER NOT NULL REFERENCES specimens(id) ON DELETE RESTRICT,
            event_type TEXT NOT NULL CHECK(event_type IN ('등록','인계·인수','보관장소 변경')),
            from_person TEXT NOT NULL,
            to_person TEXT NOT NULL,
            from_location TEXT NOT NULL,
            to_location TEXT NOT NULL,
            note TEXT NOT NULL DEFAULT '',
            photo_path TEXT,
            signature_path TEXT,
            signed_by TEXT,
            created_at TEXT NOT NULL
        );
        CREATE INDEX IF NOT EXISTS movements_specimen_date ON movements(specimen_id, id);
        """)

init_db()


def tidy(s: str, field: str, maxlen=120) -> str:
    s = (s or "").strip()
    if not s or len(s) > maxlen:
        raise HTTPException(422, f"{field} 항목을 확인해 주세요. (최대 {maxlen}자)")
    return s


def photo_name(photo: UploadFile | None) -> str | None:
    if photo is None or not photo.filename:
        return None
    if photo.content_type not in {"image/jpeg", "image/png", "image/webp"}:
        raise HTTPException(422, "이미지는 JPG, PNG, WEBP만 첨부할 수 있습니다.")
    raw = photo.file.read(MAX_UPLOAD + 1)
    if len(raw) > MAX_UPLOAD:
        raise HTTPException(413, "이미지 크기는 5MB를 초과할 수 없습니다.")
    try:
        with Image.open(io.BytesIO(raw)) as img:
            if img.width * img.height > 16_000_000:
                raise HTTPException(413, "이미지 해상도가 너무 큽니다.")
            img = ImageOps.exif_transpose(img).convert("RGB")
            img.thumbnail((1600, 1600))
            name = f"photo_{uuid.uuid4().hex}.jpg"
            img.save(PHOTO_DIR / name, format="JPEG", quality=84)
    except (UnidentifiedImageError, OSError):
        raise HTTPException(422, "올바른 이미지 파일이 아닙니다.")
    return f"photos/{name}"


def signature_name(data: str) -> str:
    # Demo confirmation signature, not a legally certified e-signature.
    if not data or not data.startswith("data:image/png;base64,"):
        raise HTTPException(422, "인수 확인 서명을 입력해 주세요.")
    try:
        raw = base64.b64decode(data.split(",", 1)[1], validate=True)
        if not raw or len(raw) > MAX_SIGNATURE:
            raise HTTPException(413, "서명 이미지가 너무 큽니다.")
        with Image.open(io.BytesIO(raw)) as img:
            if img.format != "PNG" or img.width > 1200 or img.height > 700:
                raise HTTPException(422, "서명 이미지를 확인해 주세요.")
            img.load()
            target = img.convert("RGBA")
            name = f"sign_{uuid.uuid4().hex}.png"
            target.save(SIG_DIR / name, "PNG")
            return f"signatures/{name}"
    except (ValueError, UnidentifiedImageError, OSError):
        raise HTTPException(422, "올바른 서명 이미지가 아닙니다.")


def page(request: Request, file: str, **ctx):
    return templates.TemplateResponse(request=request, name=file, context={"request": request, "year": datetime.now(TIMEZONE).year, **ctx})


def get_specimen(db: sqlite3.Connection, sid: int):
    record = db.execute("SELECT * FROM specimens WHERE id=?", (sid,)).fetchone()
    if record is None:
        raise HTTPException(404, "시료 정보를 찾을 수 없습니다.")
    return record


@app.get("/", response_class=HTMLResponse)
def dashboard(request: Request, q: str = "", status: str = "전체"):
    with connect() as db:
        where, args = [], []
        if q.strip():
            term = f"%{q.strip()}%"
            where.append("(sample_code LIKE ? OR label LIKE ? OR project LIKE ? OR current_custodian LIKE ?)")
            args.extend([term] * 4)
        if status != "전체":
            where.append("status=?")
            args.append(status)
        sql = "SELECT * FROM specimens" + (" WHERE " + " AND ".join(where) if where else "") + " ORDER BY id DESC"
        rows = db.execute(sql, args).fetchall()
        stats = db.execute("""SELECT COUNT(*) AS total,
            SUM(CASE WHEN status='보관 중' THEN 1 ELSE 0 END) AS stored,
            SUM(CASE WHEN status='인수 완료' THEN 1 ELSE 0 END) AS handed
            FROM specimens""").fetchone()
        recent = db.execute("""SELECT m.*,s.sample_code,s.label FROM movements m
            JOIN specimens s ON s.id=m.specimen_id ORDER BY m.id DESC LIMIT 6""").fetchall()
    return page(request, "dashboard.html", active="home", rows=rows, stats=stats, recent=recent, q=q, status=status)


@app.get("/new", response_class=HTMLResponse)
def new(request: Request):
    return page(request, "new.html", active="new")


@app.post("/specimens")
def create_specimen(
    sample_code: str = Form(...), label: str = Form(...), sample_type: str = Form(...),
    quantity: float = Form(...), unit: str = Form(...), project: str = Form(...),
    location: str = Form(...), custodian: str = Form(...), notes: str = Form(""),
    photo: UploadFile | None = File(None)
):
    code = tidy(sample_code, "시료 코드", 60)
    if not re.fullmatch(r"[A-Za-z0-9_\-]+", code):
        raise HTTPException(422, "시료 코드는 영문·숫자·하이픈·밑줄만 사용해 주세요.")
    if not 0 < quantity < 10_000_000:
        raise HTTPException(422, "수량을 확인해 주세요.")
    label, sample_type = tidy(label, "시료명"), tidy(sample_type, "유형")
    unit, project = tidy(unit, "단위", 15), tidy(project, "프로젝트")
    location, custodian = tidy(location, "보관 위치"), tidy(custodian, "담당자")
    photo_rel = photo_name(photo)
    created = now_kr()
    try:
        with connect() as db:
            cur = db.execute("""INSERT INTO specimens
            (sample_code,label,sample_type,quantity,unit,project,current_location,current_custodian,status,notes,photo_path,created_at)
            VALUES(?,?,?,?,?,?,?,?,?,?,?,?)""",
            (code,label,sample_type,quantity,unit,project,location,custodian,"보관 중",notes.strip()[:1000],photo_rel,created))
            sid = cur.lastrowid
            db.execute("""INSERT INTO movements(specimen_id,event_type,from_person,to_person,from_location,to_location,note,photo_path,created_at)
            VALUES(?,?,?,?,?,?,?,?,?)""",(sid,"등록",custodian,custodian,location,location,"최초 시료 등록",photo_rel,created))
    except sqlite3.IntegrityError:
        raise HTTPException(409, "이미 사용 중인 시료 코드입니다.")
    return RedirectResponse(f"/specimens/{sid}?created=1", status_code=303)


@app.get("/specimens/{sid}", response_class=HTMLResponse)
def specimen_detail(request: Request, sid: int, created: int = 0, transferred: int = 0, moved: int = 0):
    with connect() as db:
        specimen = get_specimen(db,sid)
        events = db.execute("SELECT * FROM movements WHERE specimen_id=? ORDER BY id DESC", (sid,)).fetchall()
    return page(request, "detail.html", active="home", specimen=specimen, events=events, created=created, transferred=transferred, moved=moved)


@app.post("/specimens/{sid}/handover")
def handover(
    sid: int, to_person: str = Form(...), location: str = Form(...),
    signed_by: str = Form(...), signature_data: str = Form(...),
    note: str = Form(""), confirm: str = Form(""),
    photo: UploadFile | None = File(None)
):
    to_person, location, signed_by = (tidy(to_person,"인수자"), tidy(location,"인계 후 보관 장소"),tidy(signed_by,"서명자"))
    if signed_by != to_person:
        raise HTTPException(422, "서명자 이름은 인수자와 일치해야 합니다.")
    if confirm != "yes":
        raise HTTPException(422, "인수 확인에 동의해 주세요.")
    sig_rel = signature_name(signature_data)
    img_rel = photo_name(photo)
    with connect() as db:
        db.execute("BEGIN IMMEDIATE")
        before = get_specimen(db,sid)
        timestamp = now_kr()
        db.execute("UPDATE specimens SET current_custodian=?,current_location=?,status='인수 완료' WHERE id=?",
                   (to_person,location,sid))
        db.execute("""INSERT INTO movements
        (specimen_id,event_type,from_person,to_person,from_location,to_location,note,photo_path,signature_path,signed_by,created_at)
        VALUES(?,?,?,?,?,?,?,?,?,?,?)""",
        (sid,"인계·인수",before["current_custodian"],to_person,before["current_location"],location,
        note.strip()[:1000],img_rel,sig_rel,signed_by,timestamp))
    return RedirectResponse(f"/specimens/{sid}?transferred=1",status_code=303)


@app.post("/specimens/{sid}/move")
def move(sid: int, location: str = Form(...), actor: str = Form(...), note: str = Form("")):
    location, actor = tidy(location,"새 보관 장소"), tidy(actor,"변경 담당자")
    with connect() as db:
        db.execute("BEGIN IMMEDIATE")
        before = get_specimen(db,sid)
        timestamp = now_kr()
        if location == before["current_location"]:
            raise HTTPException(422, "현재 위치와 다른 위치를 입력해 주세요.")
        db.execute("UPDATE specimens SET current_location=? WHERE id=?",(location,sid))
        db.execute("""INSERT INTO movements(specimen_id,event_type,from_person,to_person,from_location,to_location,note,created_at)
        VALUES(?,?,?,?,?,?,?,?)""",
        (sid,"보관장소 변경",actor,actor,before["current_location"],location,note.strip()[:1000],timestamp))
    return RedirectResponse(f"/specimens/{sid}?moved=1",status_code=303)


@app.get("/export.csv")
def export_csv():
    with connect() as db:
        rows = db.execute("""SELECT s.sample_code,s.label,s.project,s.sample_type,s.quantity,s.unit,
            m.event_type,m.from_person,m.to_person,m.from_location,m.to_location,m.signed_by,m.created_at,m.note
            FROM movements m JOIN specimens s ON s.id=m.specimen_id ORDER BY m.id DESC""").fetchall()
    columns=["시료코드","시료명","프로젝트","시료유형","수량","단위","이벤트","이전담당자","다음담당자","이전위치","다음위치","서명자","기록시각","비고"]
    stream=io.StringIO()
    writer=csv.writer(stream)
    writer.writerow(columns)
    for r in rows:
        # Protect reviewers opening exported records in spreadsheet programs.
        # CSV quoting does not prevent formula execution in Excel/Sheets.
        safe = []
        for cell in r:
            value = str(cell) if cell is not None else ""
            if value.lstrip().startswith(("=", "+", "-", "@", "\\t", "\\r", "\\n")):
                value = "\'" + value
            safe.append(value)
        writer.writerow(safe)
    content="\ufeff"+stream.getvalue()
    return StreamingResponse(iter([content.encode("utf-8")]), media_type="text/csv; charset=utf-8",headers={"Content-Disposition":"attachment; filename=handover_audit.csv"})


def seed_demo():
    """Use fictional project and person names ONLY, for local demonstration."""
    with connect() as db:
        if db.execute("SELECT COUNT(*) FROM specimens").fetchone()[0]:
            return
        fixture=[
            ("SMP-2026-001","저서생물 정점 A-03","저서생물",12,"병","연안 모니터링 시범사업","냉장보관실 A-2","담당자 가"),
            ("SMP-2026-002","해수 시료 W-12","해수",4,"병","해수환경 시범조사","저온보관실 B-1","담당자 나"),
            ("SMP-2026-003","퇴적물 정점 S-08","퇴적물",7,"봉투","연안 모니터링 시범사업","시료실 선반 3","담당자 다"),
            ("SMP-2026-004","식물플랑크톤 P-02","식물플랑크톤",6,"병","해수환경 시범조사","냉장보관실 A-1","담당자 가"),
        ]
        for code,label,typ,quantity,unit,project,loc,who in fixture:
            t=now_kr()
            cur=db.execute("""INSERT INTO specimens(sample_code,label,sample_type,quantity,unit,project,current_location,current_custodian,status,notes,created_at)
            VALUES(?,?,?,?,?,?,?,?,?,?,?)""",(code,label,typ,quantity,unit,project,loc,who,"보관 중","데모용 가상 시료",t))
            db.execute("""INSERT INTO movements(specimen_id,event_type,from_person,to_person,from_location,to_location,note,created_at)
            VALUES(?,?,?,?,?,?,?,?)""",(cur.lastrowid,"등록",who,who,loc,loc,"데모용 가상 데이터",t))


if __name__ == "__main__":
    seed_demo()
    import uvicorn
    uvicorn.run(app, host="127.0.0.1", port=8502)
