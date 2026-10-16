"""Public SAFE demo for TRACE. Fake records only; no DB, photos, or signatures.

Deploy THIS file to Streamlit Community Cloud, never app.py (the local writer).
"""
from datetime import datetime, timedelta
from html import escape
from pathlib import Path
from zoneinfo import ZoneInfo

import pandas as pd
import streamlit as st

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

st.markdown('''<div class="head"><div class="brand">✳ TRACE<b>.</b></div>
<div class="kicker">SAMPLE CARE · PUBLIC PORTFOLIO DEMO</div>
<h1>시료의 이동과 인수 여부를 한눈에.</h1>
<p>누가, 언제, 어떤 시료를 전달하고 보관했는지 한곳에서 확인하는 인수인계 서비스의 시연 화면입니다.</p>
<span class="chip">✓ 가상 시료만 사용</span><span class="chip">✓ 조회 전용</span><span class="chip">✓ 실무 데이터 저장 안 함</span></div>''',unsafe_allow_html=True)

m1,m2,m3=st.columns(3)
m1.metric("등록된 시료",f"{len(DEMO)}건")
m2.metric("인수 완료",f"{sum(x['status']=='인수 완료' for x in DEMO)}건")
m3.metric("이력 이벤트",f"{sum(len(x['history']) for x in DEMO)}건")

st.markdown('<div class="section">🧪 시료 검색 및 조회</div>',unsafe_allow_html=True)
c1,c2=st.columns([2,1])
with c1:
    q=st.text_input("검색",placeholder="시료코드 · 시료명 · 프로젝트 · 담당자",label_visibility="collapsed")
with c2:
    status=st.selectbox("상태",["전체","보관 중","인수 완료"],label_visibility="collapsed")

filtered=[x for x in DEMO if (status=="전체" or x["status"]==status) and (not q or q.lower() in ' '.join([x[k] for k in ("code","label","project","custodian")]).lower())]
if not filtered:
    st.info("검색 결과가 없습니다.")
else:
    cols=st.columns(2)
    for i,x in enumerate(filtered):
        with cols[i%2]:
            klass='done' if x['status']=='인수 완료' else ''
            st.markdown(f'''<div class="card"><span class="code">{escape(x['code'])}</span><h3>{escape(x['label'])}</h3>
            <span class="status {klass}">{escape(x['status'])}</span><p>📍 {escape(x['location'])} · {escape(x['custodian'])}</p>
            <p>{escape(x['type'])} · {escape(x['qty'])} · {escape(x['project'])}</p></div>''',unsafe_allow_html=True)
            with st.expander(f"{x['code']} 인수인계 이력 보기"):
                for j,(action,who,loc) in enumerate(reversed(x['history'])):
                    st.markdown(f'<div class="timeline"><strong>{escape(action)}</strong><p>{escape(who)} · {escape(loc)}</p><p>데모 이벤트 {len(x["history"])-j} (가상 기록)</p></div>',unsafe_allow_html=True)

with st.expander("📋 가상 시료 전체 목록 다운로드"):
    df=pd.DataFrame([{k:v for k,v in x.items() if k!="history"} for x in DEMO])
    st.dataframe(df,use_container_width=True,hide_index=True)
    st.download_button("가상 데이터 CSV 다운로드",df.to_csv(index=False).encode('utf-8-sig'),file_name="trace_demo_samples.csv",mime="text/csv")

st.markdown('''<div class="footer">TRACE · 포트폴리오 시연용 읽기 전용 웹앱. 이 앱은 서명·사진·실제 시료 정보를 받거나 저장하지 않습니다. 실제 입력·인수·서명 기능은 인증 없는 인터넷 배포를 금지한 로컬 FastAPI MVP에서만 제공합니다.</div>''',unsafe_allow_html=True)
