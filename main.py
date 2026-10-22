import streamlit as st
import requests
import pandas as pd
import plotly.express as px
from datetime import datetime, timedelta, timezone

# 1. 페이지 설정 및 커스텀 CSS
st.set_page_config(page_title="Cinematic Box Office", page_icon="🎫", layout="wide")

st.markdown("""
    <style>
    .big-font { font-size:36px !important; font-weight: 900; letter-spacing: -1px; }
    .highlight-gold { color: #FFD700; }
    .ticket-box { 
        padding: 25px; border-radius: 15px; 
        background: linear-gradient(135deg, #1e1e1e, #3a3a3a); 
        border-left: 6px solid #E50914; margin-bottom: 30px;
        color: white;
    }
    </style>
""", unsafe_allow_html=True)

# 2. 상단 헤더 & 컨트롤 패널
header_col, control_col = st.columns([2, 1])
with header_col:
    st.markdown('<p class="big-font">🎬 <span class="highlight-gold">BOX OFFICE</span> INSIGHTS</p>', unsafe_allow_html=True)
    
with control_col:
    KST = timezone(timedelta(hours=9))
    yesterday_kst = (datetime.now(KST) - timedelta(days=1)).date()
    selected_date = st.date_input(
        "날짜를 선택해 타임머신을 타보세요 🕰️",
        value=yesterday_kst,
        min_value=datetime(2004, 1, 1).date(),
        max_value=yesterday_kst,
        label_visibility="collapsed"
    )
    target_dt = selected_date.strftime("%Y%m%d")

st.divider()

# 3. KOBIS API 연동
@st.cache_data(ttl=1800, show_spinner=False)
def fetch_boxoffice(date_text, api_key):
    url = "https://www.kobis.or.kr/kobisopenapi/webservice/rest/boxoffice/searchDailyBoxOfficeList.json"
    response = requests.get(url, params={"key": api_key, "targetDt": date_text}, timeout=10)
    response.raise_for_status()
    return response.json()

try:
    API_KEY = st.secrets["KOBIS_KEY"]
except KeyError:
    st.error("🚨 스트림릿 비밀 금고(secrets)에 'KOBIS_KEY'가 없습니다.")
    st.stop()

try:
    with st.spinner("영화관 전산망에 접속 중입니다... 🍿"):
        data = fetch_boxoffice(target_dt, API_KEY)
except requests.exceptions.RequestException:
    st.error("📡 통신 실패: 인터넷 연결이나 API 주소를 확인해 주세요.")
    st.stop()

if "faultInfo" in data:
    st.error("🚫 인증 거절: KOBIS 인증키가 올바른지 확인해 주세요.")
    st.stop()

movies = data.get("boxOfficeResult", {}).get("dailyBoxOfficeList", [])
if not movies:
    st.info("🌙 이 날짜는 아직 영진위 집계가 끝나지 않았거나, 극장이 쉬는 날이었습니다.")
    st.stop()

# 4. 데이터 가공
df = pd.DataFrame(movies)
numeric_cols = ["rank", "rankInten", "audiCnt", "audiAcc", "scrnCnt"]
for col in numeric_cols:
    df[col] = pd.to_numeric(df[col], errors="coerce").fillna(0).astype(int)

df["movieNm"] = df.apply(
    lambda row: f"{row['movieNm']} 🏆" if row["audiAcc"] >= 1_000_000 else row["movieNm"],
    axis=1
)

def format_rank_change(value):
    if value > 0: return f"🔺 {value}"
    if value < 0: return f"🔻 {abs(value)}"
    return "-"
df["순위 변동"] = df["rankInten"].apply(format_rank_change)

# 5. VIP 티켓 라운지 (1위 영화 강조)
top1 = df.iloc[0]
total_audi = df['audiCnt'].sum()

st.markdown('<div class="ticket-box">', unsafe_allow_html=True)
st.subheader(f"🥇 오늘의 흥행 제왕: {top1['movieNm']}")
col1, col2, col3, col4 = st.columns(4)
col1.metric("일일 관객수", f"{top1['audiCnt']:,} 명", f"전일 대비 {top1['rankInten']} 계단 이동" if top1['rankInten'] != 0 else "순위 방어 성공")
col2.metric("누적 관객수", f"{top1['audiAcc']:,} 명")
col3.metric("확보 스크린", f"{top1['scrnCnt']:,} 개")
col4.metric("총 관객수 파이", f"상위 10편 총 {total_audi:,}명")
st.markdown('</div>', unsafe_allow_html=True)

# ==========================================
# 📊 시각화 섹션: 화려한 그래프 추가
# ==========================================
st.subheader("📈 박스오피스 시각화 리포트")
tab1, tab2 = st.tabs(["📊 관객수 TOP 5 (막대그래프)", "🥧 관객 점유율 (트리맵)"])

with tab1:
    # 넷플릭스 스타일 그라데이션 막대그래프
    top5_df = df.head(5).sort_values("audiCnt", ascending=True)
    fig_bar = px.bar(
        top5_df, 
        x="audiCnt", 
        y="movieNm", 
        orientation="h",
        text="audiCnt",
        color="audiCnt",
        color_continuous_scale=["#333333", "#E50914", "#FFD700"] 
    )
    fig_bar.update_traces(texttemplate=" %{text:,}명", textposition="outside", cliponaxis=False)
    fig_bar.update_layout(
        xaxis_title="", yaxis_title="",
        coloraxis_showscale=False,
        margin=dict(l=0, r=60, t=20, b=0),
        height=350
    )
    st.plotly_chart(fig_bar, use_container_width=True)

with tab2:
    # 박스오피스 파이를 누가 얼마나 가져갔는지 보여주는 트리맵
    fig_tree = px.treemap(
        df, 
        path=[px.Constant("전체 관객"), "movieNm"], 
        values="audiCnt",
        color="audiCnt",
        color_continuous_scale="Viridis"
    )
    fig_tree.update_traces(textinfo="label+value+percent parent")
    fig_tree.update_layout(margin=dict(t=20, l=0, r=0, b=0), height=400)
    st.plotly_chart(fig_tree, use_container_width=True)

st.divider()

# ==========================================
# 📋 데이터 표 섹션: 프로그레스 바(Progress Bar) 추가
# ==========================================
st.subheader("📋 전체 박스오피스 세부 지표")

# Streamlit column_config를 활용해 표 안에 미니 그래프(Progress) 삽입
display_df = df[["rank", "순위 변동", "movieNm", "audiCnt", "audiAcc", "scrnCnt"]].copy()
max_audi = int(display_df["audiCnt"].max())

st.dataframe(
    display_df,
    column_config={
        "rank": st.column_config.NumberColumn("순위"),
        "순위 변동": st.column_config.TextColumn("변동"),
        "movieNm": st.column_config.TextColumn("영화명"),
        "audiCnt": st.column_config.ProgressColumn(
            "일일 관객수(명)",
            help="오늘 하루 동안 모은 관객수",
            format="%d",
            min_value=0,
            max_value=max_audi, # 1위 관객수 기준으로 게이지가 찹니다.
        ),
        "audiAcc": st.column_config.NumberColumn("누적관객(명)", format="%d"),
        "scrnCnt": st.column_config.NumberColumn("스크린수", format="%d"),
    },
    hide_index=True,
    use_container_width=True
)
