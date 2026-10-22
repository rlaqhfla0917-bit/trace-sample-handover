"""Functional API tests with isolated demo storage (no actual workplace data)."""
import base64
import io
import os
import sys
import tempfile
from pathlib import Path

import pytest
from fastapi.testclient import TestClient
from PIL import Image

ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT))
TEST_DIR = tempfile.TemporaryDirectory()
os.environ['HANDOVER_DATA_DIR']=TEST_DIR.name
from app import app, connect, seed_demo, init_db
client=TestClient(app)


def png_signature():
    img=Image.new('RGBA',(350,100),(255,255,255,255))
    from PIL import ImageDraw
    draw=ImageDraw.Draw(img)
    draw.line([(20,70),(65,20),(135,73),(170,22),(230,60)],fill=(60,40,40),width=5)
    out=io.BytesIO()
    img.save(out,format='PNG')
    return 'data:image/png;base64,'+base64.b64encode(out.getvalue()).decode()


def specimen_form(code='TEST-001'):
    return dict(sample_code=code,label='가상 해수 시료',sample_type='해수',quantity='3',unit='병',project='시범 조사',location='냉장고 A-1',custodian='담당자 가',notes='테스트 가상 데이터')


def test_dashboard_and_seed():
    seed_demo()
    page=client.get('/')
    assert page.status_code==200
    assert '시료 목록' in page.text
    assert 'SMP-2026-001' in page.text
    assert '3' in page.text


def test_registration_duplicate_and_detail():
    first=client.post('/specimens',data=specimen_form(),follow_redirects=False)
    assert first.status_code==303
    assert first.headers['location'].startswith('/specimens/')
    sid=int(first.headers['location'].split('/')[2].split('?')[0])
    view=client.get(f'/specimens/{sid}')
    assert '가상 해수 시료' in view.text
    again=client.post('/specimens',data=specimen_form())
    assert again.status_code==409
    with connect() as db:
        assert db.execute('select count(*) from specimens where id=?',(sid,)).fetchone()[0]==1
        assert db.execute('select count(*) from movements where specimen_id=?',(sid,)).fetchone()[0]==1


def test_handover_and_location_history():
    sid=_spec_id()
    if not sid:
        client.post('/specimens',data=specimen_form())
        sid=_spec_id()
    assert client.post(f'/specimens/{sid}/handover',data={'to_person':'담당자 나','location':'분석실 B-2','signed_by':'담당자 나','signature_data':'','confirm':'yes'}).status_code==422
    payload={'to_person':'담당자 나','location':'분석실 B-2','signed_by':'담당자 나','signature_data':png_signature(),'confirm':'yes','note':'병수 3병 일치'}
    changed=client.post(f'/specimens/{sid}/handover',data=payload,follow_redirects=False)
    assert changed.status_code==303
    with connect() as db:
        s=db.execute('select * from specimens where id=?',(sid,)).fetchone()
        assert s['current_custodian']=='담당자 나'
        assert s['current_location']=='분석실 B-2'
        assert s['status']=='인수 완료'
        events=db.execute('select * from movements where specimen_id=? order by id',(sid,)).fetchall()
        assert events[-1]['signature_path'].startswith('signatures/')
    moved=client.post(f'/specimens/{sid}/move',data={'location':'보관실 C-1','actor':'담당자 나','note':'냉장고 교체'},follow_redirects=False)
    assert moved.status_code==303
    with connect() as db:
        events=db.execute('select event_type from movements where specimen_id=? order by id',(sid,)).fetchall()
        assert [r['event_type'] for r in events]==['등록','인계·인수','보관장소 변경']
    response=client.get('/export.csv')
    assert response.status_code==200
    assert 'text/csv' in response.headers['content-type']
    assert 'TEST-001' in response.content.decode('utf-8-sig')


def _spec_id():
    with connect() as db:
        row=db.execute("select id from specimens where sample_code='TEST-001'").fetchone()
        return row['id'] if row else None


def test_validation_bad_content_and_media_protection():
    data=specimen_form('NOT VALID!')
    assert client.post('/specimens',data=data).status_code==422
    assert client.get('/media/handover.sqlite3').status_code==404
    assert client.get('/specimens/999999').status_code==404
    data=specimen_form('FILE-001')
    files={'photo':('payload.txt',b'bad','text/plain')}
    assert client.post('/specimens',data=data,files=files).status_code==422


def test_search():
    r=client.get('/?q=%EA%B0%80%EC%83%81+%ED%95%B4%EC%88%98')
    assert r.status_code==200


def test_export_csv_does_not_execute_spreadsheet_formulas():
    data=specimen_form("CSV-INJECTION")
    data["label"]="=HYPERLINK(\"https://example.org\",\"click\")"
    created=client.post("/specimens",data=data,follow_redirects=False)
    assert created.status_code == 303
    exported=client.get("/export.csv").content.decode("utf-8-sig")
    assert "'=HYPERLINK(" in exported
    assert "CSV-INJECTION" in exported
