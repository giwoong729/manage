import streamlit as st
import requests
import pandas as pd
import plotly.express as px
from datetime import datetime, timedelta, timezone

# 1. 페이지 기본 설정 (가장 먼저 실행되어야 함)
st.set_page_config(page_title="일일 박스오피스", page_icon="🍿", layout="wide")

# 2. 사이드바 구성 (컨트롤 영역 분리)
with st.sidebar:
    st.title("🍿 박스오피스 조회")
    
    # 한국 시간 기준 어제 날짜 계산
    KST = timezone(timedelta(hours=9))
    yesterday_kst = (datetime.now(KST) - timedelta(days=1)).date()
    
    selected_date = st.date_input(
        "📅 날짜를 선택하세요",
        value=yesterday_kst,
        min_value=datetime(2004, 1, 1).date(),
        max_value=yesterday_kst
    )
    target_dt = selected_date.strftime("%Y%m%d")
    
    st.divider()
    st.caption("데이터 출처: KOBIS 일별 박스오피스 API")

# 3. KOBIS API 연동 및 데이터 가져오기
@st.cache_data(ttl=1800, show_spinner=False)
def fetch_boxoffice(date_text, api_key):
    url = "https://www.kobis.or.kr/kobisopenapi/webservice/rest/boxoffice/searchDailyBoxOfficeList.json"
    response = requests.get(url, params={"key": api_key, "targetDt": date_text}, timeout=10)
    response.raise_for_status()
    return response.json()

# 인증키 확인
try:
    API_KEY = st.secrets["KOBIS_KEY"]
except KeyError:
    st.error("🔐 KOBIS 인증키를 찾을 수 없습니다.")
    st.info("Streamlit Cloud의 Settings > Secrets에 `KOBIS_KEY`를 등록해 주세요.")
    st.stop()

# API 호출 및 예외 처리 (통합)
try:
    with st.spinner(f"{selected_date.strftime('%Y년 %m월 %d일')} 데이터를 불러오는 중..."):
        data = fetch_boxoffice(target_dt, API_KEY)
except requests.exceptions.RequestException as e:
    st.error("🌐 서버 통신에 실패했습니다. 인터넷 연결이나 API 상태를 확인해 주세요.")
    st.stop()

# API 오류 응답 처리
if "faultInfo" in data:
    fault = data["faultInfo"]
    st.error(f"🚨 API 요청 거절 (코드: {fault.get('errorCode', '알 수 없음')})")
    st.warning(fault.get("message", "인증키가 올바른지 확인해 주세요."))
    st.stop()

# 4. 데이터 가공
movies = data.get("boxOfficeResult", {}).get("dailyBoxOfficeList", [])
if not movies:
    st.warning("📭 해당 날짜는 아직 집계 전이거나 데이터가 없습니다.")
    st.stop()

df = pd.DataFrame(movies)

# 숫자형 데이터 변환
numeric_cols = ["rank", "rankInten", "audiCnt", "audiAcc", "scrnCnt"]
for col in numeric_cols:
    df[col] = pd.to_numeric(df[col], errors="coerce").fillna(0).astype(int)

# 100만 관객 돌파 트로피 및 텍스트 가공
df["movieNm"] = df.apply(
    lambda row: f"{row['movieNm']} 🏆" if row["audiAcc"] >= 1_000_000 else row["movieNm"],
    axis=1
)

# 순위 변동 화살표 처리
def format_rank_change(value):
    if value > 0: return f"🔺 {value}"
    if value < 0: return f"🔻 {abs(value)}"
    return "-"

df["순위 변동"] = df["rankInten"].apply(format_rank_change)

# 5. 메인 화면 출력 (탭 분리)
st.title(f"🎬 {selected_date.strftime('%Y년 %m월 %d일')} 박스오피스")

# 요약 대시보드와 전체 표를 탭으로 나누어 화면을 깔끔하게 유지합니다.
tab1, tab2 = st.tabs(["📊 요약 대시보드", "📋 전체 순위표"])

with tab1:
    # 1위 영화 하이라이트 (st.metric 활용)
    top1 = df.iloc[0]
    st.subheader("🥇 오늘의 1위 영화")
    
    # st.container를 둥근 상자처럼 보이게 꾸밀 수 있습니다.
    with st.container():
        col1, col2, col3, col4 = st.columns(4)
        
        # delta 매개변수를 사용하여 순위 변동을 직관적으로 보여줍니다.
        # 이전 순위 = 현재 순위(1) - 순위 변동(rankInten)
        prev_rank = 1 - top1['rankInten']
        rank_delta = f"전일 대비 {top1['rankInten']} 계단 상승" if top1['rankInten'] > 0 else (
            f"전일 대비 {abs(top1['rankInten'])} 계단 하락" if top1['rankInten'] < 0 else "순위 유지"
        )
        
        col1.metric("영화명", top1['movieNm'], rank_delta)
        col2.metric("일일 관객수", f"{top1['audiCnt']:,} 명")
        col3.metric("누적 관객수", f"{top1['audiAcc']:,} 명")
        col4.metric("스크린 수", f"{top1['scrnCnt']:,} 개")

    st.divider()

    # 상위 5편 막대그래프 (Plotly)
    st.subheader("📈 관객수 상위 5편")
    top5_df = df.nsmallest(5, "rank").sort_values("audiCnt", ascending=True)
    
    fig = px.bar(
        top5_df, 
        x="audiCnt", 
        y="movieNm", 
        orientation="h",
        text="audiCnt",
        color="audiCnt",
        color_continuous_scale="Blues" # 세련된 색상 테마 적용
    )
    fig.update_traces(texttemplate="%{text:,} 명", textposition="outside")
    fig.update_layout(
        xaxis_title="", 
        yaxis_title="", 
        coloraxis_showscale=False,
        margin=dict(l=0, r=0, t=10, b=0)
    )
    st.plotly_chart(fig, use_container_width=True)

with tab2:
    st.subheader("전체 박스오피스 세부 지표")
    
    # 출력용 데이터프레임 정리
    display_df = df[["rank", "순위 변동", "movieNm", "openDt", "audiCnt", "audiAcc", "scrnCnt"]].copy()
    display_df.columns = ["순위", "순위 변동", "영화명", "개봉일", "관객수(명)", "누적관객(명)", "스크린수(개)"]
    
    # 색상 적용 함수
    def style_dataframe(val):
        if isinstance(val, str):
            if "🔺" in val: return "color: #ff4b4b; font-weight: bold;"
            if "🔻" in val: return "color: #1c83e1; font-weight: bold;"
        return ""

    styled_df = display_df.style.map(style_dataframe, subset=["순위 변동"]).format({
        "관객수(명)": "{:,}",
        "누적관객(명)": "{:,}",
        "스크린수(개)": "{:,}"
    })
    
    st.dataframe(styled_df, use_container_width=True, hide_index=True)
