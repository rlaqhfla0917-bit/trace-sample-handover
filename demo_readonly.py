"""Public SAFE demo for TRACE. Synthetic, session-only registration; no DB, photos or signatures.

Deploy THIS file to Streamlit Community Cloud, never app.py (the local writer).
"""
from datetime import datetime, timedelta
from copy import deepcopy
import secrets
from html import escape
from pathlib import Path
from zoneinfo import ZoneInfo

import pandas as pd
import streamlit as st
from demo_samples import create_demo_specimen, safe_csv_cell, VALID_TYPES, VALID_UNITS

st.set_page_config(page_title="TRACE | 가상 시료 이력 데모", page_icon="🧪", layout="wide", initial_sidebar_state="collapsed")

styles = r"""
@import url('https://fonts.googleapis.com/css2?family=DM+Sans:wght@400;500;600;700;800&family=Noto+Sans+KR:wght@400;500;600;700;800&display=swap');
:root{--ink:#483830;--muted:#897971;--border:#eee6dd;--peach:#e8c7b7;--cream:#fcf7ef}
html,body,[class*="css"]{font-family:'DM Sans','Noto Sans KR',sans-serif!important}
.stApp{background:#f7eee5!important;color:var(--ink)}
.block-container{max-width:1220px!important;padding:2.2rem 2.3rem 4rem!important}
[data-testid="stHeader"]{background:#f7eee5e8!important}
.head{background:#fff;border:1px solid #f0e6de;border-radius:28px;padding:29px 34px;margin:0 0 18px;box-shadow:0 14px 32px #76543c10}
.brand{font-size:1.6rem;font-weight:800;letter-spacing:-.06em;color:#61443a}.brand b{color:#c69d8c}
.kicker{color:#b88a77;font-weight:800;font-size:.72rem;letter-spacing:.09em;margin-top:10px}
.head h1{font-size:2.1rem;font-weight:800;letter-spacing:-.06em;color:#4b362d;margin:11px 0}
.head p{color:#917c72;font-size:.93rem;line-height:1.7;margin:0}
.chip{display:inline-flex;gap:5px;border-radius:99px;padding:6px 12px;border:1px solid #f0dfd4;background:#fdf6f1;color:#946b58;font-size:.74rem;font-weight:700;margin:16px 6px 0 0}
.section{font-size:1.14rem;font-weight:800;letter-spacing:-.035em;color:#604239;margin:20px 0 11px}
[data-testid="stMetric"]{background:#fff;border-radius:17px;border:1px solid #efe5dc;padding:16px 20px}
[data-testid="stMetricLabel"] p{color:#a08b7f;font-weight:700}
[data-testid="stMetricValue"]{font-weight:800!important;color:#65483d!important;letter-spacing:-.045em!important}
.card{padding:22px 23px;background:#fff;border:1px solid #eee5de;border-radius:20px;margin-bottom:15px;box-shadow:0 5px 20px #6d49380d}
.card .code{color:#be917f;font-size:.75rem;font-weight:800;letter-spacing:.04em}
.card h3{font-size:1.13rem;color:#49392f;letter-spacing:-.035em;margin:9px 0}
.card p{color:#87776e;font-size:.87rem;margin:6px 0;line-height:1.6}
.status{font-size:.72rem;display:inline-block;background:#eaf3e8;color:#597e62;font-weight:800;border-radius:99px;padding:5px 10px}
.status.done{background:#f7e5e0;color:#a76553}
.timeline{border-left:3px solid #e6caba;margin:9px 0 18px;padding:2px 0 2px 16px}
.timeline strong{color:#5b463a}.timeline p{color:#80746b;font-size:.84rem;line-height:1.6;margin:5px 0}
.small{font-size:.79rem;color:#9c8c81;line-height:1.6}
.footer{padding:20px 0;font-size:.78rem;color:#938379;border-top:1px solid #eaddd1;margin-top:35px}
div.stButton>button[kind="primary"],div.stFormSubmitButton>button{background:#956654;color:#fff;border:0;border-radius:12px;min-height:44px;font-weight:800}
[data-testid="stForm"]{background:#fff;border:1px solid #eee5de;border-radius:22px;padding:24px}
[data-testid="stAlert"]{border-radius:15px}
@media(max-width:720px){.block-container{padding:1rem .9rem 3rem!important}.head{padding:25px 22px}.head h1{font-size:1.55rem}}
"""
st.markdown(f"<style>{styles}</style>", unsafe_allow_html=True)

# Everything here is synthetic. Intentionally do not import app.py or its SQLite/media folders.
DEMO = [
    {"code":"SMP-2026-001","label":"저서생물 정점 A-03","type":"저서생물","qty":"12병","project":"연안 모니터링 시범사업","location":"냉장보관실 A-2","custodian":"담당자 가","status":"보관 중", "history":[("등록","담당자 가","냉장보관실 A-2"),("보관 위치 확인","담당자 가","냉장보관실 A-2")]},
    {"code":"SMP-2026-002","label":"해수 시료 W-12","type":"해수","qty":"4병","project":"해수환경 시범조사","location":"저온보관실 B-1","custodian":"담당자 나","status":"인수 완료","history":[("등록","담당자 가","해상조사 보관함"),("인계·인수","담당자 나","저온보관실 B-1")]},
    {"code":"SMP-2026-003","label":"퇴적물 정점 S-08","type":"퇴적물","qty":"7봉투","project":"연안 모니터링 시범사업","location":"시료실 선반 3","custodian":"담당자 다","status":"보관 중","history":[("등록","담당자 다","시료실 선반 3")]},
    {"code":"SMP-2026-004","label":"식물플랑크톤 P-02","type":"식물플랑크톤","qty":"6병","project":"해수환경 시범조사","location":"냉장보관실 A-1","custodian":"담당자 가","status":"인수 완료","history":[("등록","담당자 나","선상 시료함"),("인계·인수","담당자 가","냉장보관실 A-1")]},
]

# A fresh deep copy is created separately for every visitor's Streamlit session.
# No server-side database, file writes, or global shared mutation.
if "trace_demo_records" not in st.session_state:
    st.session_state.trace_demo_records = deepcopy(DEMO)
if "trace_demo_screen" not in st.session_state:
    st.session_state.trace_demo_screen = "list"
if "trace_demo_flash" not in st.session_state:
    st.session_state.trace_demo_flash = None
if "trace_demo_suggested_code" not in st.session_state:
    st.session_state.trace_demo_suggested_code = f"SMP-DEMO-{secrets.token_hex(3).upper()}"
records = st.session_state.trace_demo_records

st.markdown('''<div class="head"><div class="brand">✳ TRACE<b>.</b></div>
<div class="kicker">SAMPLE CARE · INTERACTIVE PORTFOLIO DEMO</div>
<h1>시료의 이동과 인수 여부를 한눈에.</h1>
<p>누가, 언제, 어떤 시료를 전달하고 보관했는지 기록하는 인수인계 서비스의 시연 화면입니다.</p>
<span class="chip">✓ 가상 시료 전용</span><span class="chip">✓ 새 시료 등록 체험</span><span class="chip">✓ 접속 중에만 보관</span></div>''',unsafe_allow_html=True)

st.warning("공개 시연용입니다. 실제 회사명·담당자 실명·시료정보를 입력하지 마세요. 추가한 시료는 현재 접속 세션에서만 보이고, 새 세션이 시작되면 초기화됩니다.", icon="🔐")

nav_list, nav_register = st.columns([1,1])
with nav_list:
    if st.button("📋 시료 목록 및 이력 보기", use_container_width=True, type="primary" if st.session_state.trace_demo_screen=="list" else "secondary"):
        st.session_state.trace_demo_screen="list"
        st.rerun()
with nav_register:
    if st.button("➕ 새로운 시료 등록", use_container_width=True, type="primary" if st.session_state.trace_demo_screen=="register" else "secondary"):
        st.session_state.trace_demo_screen="register"
        st.rerun()

if st.session_state.trace_demo_screen == "register":
    st.markdown('<div class="section">➕ 새로운 시료 등록</div>', unsafe_allow_html=True)
    st.caption("모든 항목은 가상의 예시로 입력해 주세요. 사진·서명 파일은 공개 데모에서 받지 않습니다.")
    with st.form("new_demo_specimen", clear_on_submit=False):
        c1,c2=st.columns(2)
        with c1:
            code=st.text_input("시료코드 *",value=st.session_state.trace_demo_suggested_code,max_chars=60,
                               help="영문·숫자·하이픈·밑줄 사용, 중복 불가")
            name=st.text_input("시료명 *",placeholder="예: 가상 해수 정점 W-21",max_chars=100)
            sample_type=st.selectbox("시료 유형 *",sorted(VALID_TYPES))
            project=st.text_input("프로젝트명 *",placeholder="예: 가상 해양환경 시범조사",max_chars=100)
        with c2:
            quantity=st.number_input("수량 *",min_value=0.1,max_value=999999.0,value=1.0,step=1.0)
            unit=st.selectbox("수량 단위 *",sorted(VALID_UNITS))
            location=st.text_input("현재 보관 장소 *",placeholder="예: 냉장보관실 A-3",max_chars=100)
            custodian=st.text_input("보관 담당자(가명) *",placeholder="예: 담당자 라",max_chars=60)
        note=st.text_input("비고 (선택)",placeholder="예: 가상 시료 등록 실습",max_chars=300)
        submitted=st.form_submit_button("🧪 새 시료 등록하기",type="primary",use_container_width=True)
    if submitted:
        payload={"code":code,"label":name,"type":sample_type,"quantity":quantity,
                 "unit":unit,"project":project,"location":location,"custodian":custodian,"notes":note}
        try:
            specimen=create_demo_specimen(payload,records)
        except ValueError as exc:
            st.error(str(exc))
        else:
            records.insert(0,specimen)
            st.session_state.trace_demo_flash=f"{specimen['code']} 시료가 등록됐어요. 목록에서 확인할 수 있어요!"
            st.session_state.trace_demo_screen="list"
            st.session_state.trace_demo_suggested_code = f"SMP-DEMO-{secrets.token_hex(3).upper()}"
            st.rerun()
else:
    if st.session_state.trace_demo_flash:
        st.success(st.session_state.trace_demo_flash)
        st.session_state.trace_demo_flash=None

    m1,m2,m3=st.columns(3)
    m1.metric("등록된 시료",f"{len(records)}건")
    m2.metric("인수 완료",f"{sum(x['status']=='인수 완료' for x in records)}건")
    m3.metric("이력 이벤트",f"{sum(len(x['history']) for x in records)}건")

    st.markdown('<div class="section">🧪 시료 검색 및 조회</div>',unsafe_allow_html=True)
    c1,c2=st.columns([2,1])
    with c1:
        q=st.text_input("검색",placeholder="시료코드 · 시료명 · 프로젝트 · 담당자",label_visibility="collapsed")
    with c2:
        status=st.selectbox("상태",["전체","보관 중","인수 완료"],label_visibility="collapsed")

    filtered=[x for x in records if (status=="전체" or x["status"]==status) and
              (not q or q.lower() in ' '.join([x[k] for k in ("code","label","project","custodian")]).lower())]
    if not filtered:
        st.info("검색 결과가 없습니다.")
    else:
        cols=st.columns(2)
        for i,x in enumerate(filtered):
            with cols[i%2]:
                klass='done' if x['status']=='인수 완료' else ''
                created=f" · 등록 {escape(x['created_at'])}" if x.get('created_at') else ''
                st.markdown(f'''<div class="card"><span class="code">{escape(x['code'])}</span><h3>{escape(x['label'])}</h3>
                <span class="status {klass}">{escape(x['status'])}</span><p>📍 {escape(x['location'])} · {escape(x['custodian'])}</p>
                <p>{escape(x['type'])} · {escape(x['qty'])} · {escape(x['project'])}{created}</p></div>''',unsafe_allow_html=True)
                with st.expander(f"{x['code']} 등록·인수인계 이력 보기"):
                    for j,(action,who,loc) in enumerate(reversed(x['history'])):
                        event_time=x.get('created_at',f"데모 이벤트 {len(x['history'])-j} (가상 기록)")
                        st.markdown(f'<div class="timeline"><strong>{escape(action)}</strong><p>{escape(who)} · {escape(loc)}</p><p>{escape(event_time)}</p></div>',unsafe_allow_html=True)
                    if x.get('notes'):
                        st.caption(f"비고: {x['notes']}")

    with st.expander("📋 시료 전체 목록 · CSV 다운로드"):
        df=pd.DataFrame([{k:v for k,v in x.items() if k!="history"} for x in records])
        st.dataframe(df,use_container_width=True,hide_index=True)
        safe_export=df.apply(lambda column: column.map(safe_csv_cell))
        st.download_button("가상 시료 CSV 다운로드",safe_export.to_csv(index=False).encode('utf-8-sig'),
                           file_name="trace_demo_samples.csv",mime="text/csv")

st.markdown('''<div class="footer">TRACE · 포트폴리오 시연용 웹앱. 가상 시료의 등록·조회만 지원하며 등록 내용은 본인 접속 세션에서만 유지됩니다. 인증·사진·서명·SQLite 저장을 포함한 로컬 FastAPI MVP와는 별도 버전입니다.</div>''',unsafe_allow_html=True)
