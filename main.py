import streamlit as st
import requests
import pandas as pd
from datetime import datetime, timedelta, timezone

# 1. 페이지 기본 설정
st.set_page_config(page_title="일일 박스오피스", page_icon="🎬", layout="wide")
st.title("🍿 어제의 박스오피스")

# 2. 한국 시간 기준으로 '어제' 날짜 계산하기
# 서버 시간이 달라도 항상 한국 시간(KST, UTC+9)을 기준으로 작동하도록 설정합니다.
KST = timezone(timedelta(hours=9))
today_kst = datetime.now(KST)
yesterday_kst = today_kst - timedelta(days=1)
target_dt = yesterday_kst.strftime("%Y%m%d") # API가 요구하는 yyyymmdd 형식

st.write(f"**조회 일자:** {yesterday_kst.strftime('%Y년 %m월 %d일')}")

# 3. KOBIS API 연동 및 데이터 가져오기
@st.cache_data(ttl=3600) # 한 번 불러온 데이터는 1시간 동안 캐시(임시 저장)하여 API 호출을 줄입니다.
def fetch_box_office(date_str):
    url = "https://www.kobis.or.kr/kobisopenapi/webservice/rest/boxoffice/searchDailyBoxOfficeList.json"
    
    # 스트림릿 클라우드의 비밀 금고(secrets)에서 KOBIS_KEY를 가져옵니다.
    # 로컬 테스트 시에는 .streamlit/secrets.toml 파일에 저장해야 합니다.
    try:
        api_key = st.secrets["KOBIS_KEY"]
    except KeyError:
        return {"error": "secret_missing"}

    params = {
        "key": api_key,
        "targetDt": date_str
    }
    
    try:
        response = requests.get(url, params=params)
        response.raise_for_status() # HTTP 200이 아닌 경우 예외를 발생시킵니다.
        return response.json()
    except Exception as e:
        return {"error": "network_fail", "details": str(e)}

# 데이터 요청
data = fetch_box_office(target_dt)

# 4. 에러 및 예외 상황 처리하기
if "error" in data:
    if data["error"] == "secret_missing":
        st.error("🚨 스트림릿 비밀 금고(secrets)에 'KOBIS_KEY'가 설정되어 있지 않습니다. 설정을 확인해 주세요.")
    else:
        st.error("🚨 통신에 실패했습니다. 인터넷 연결이나 API 주소를 다시 확인해 주세요.")
    st.stop()

# 인증키 오류 등 API 자체에서 에러 메시지(faultInfo)를 보낸 경우
if "faultInfo" in data:
    st.error("🚨 API 요청이 거절되었습니다. 발급받은 KOBIS 인증키가 정확한지 확인해 주세요.")
    st.info(f"상세 메시지: {data['faultInfo'].get('message', '알 수 없는 오류')}")
    st.stop()

# 영화 목록 추출
movies = data.get("boxOfficeResult", {}).get("dailyBoxOfficeList", [])

# 결과가 비어있는 경우
if not movies:
    st.warning("⚠️ 어제 날짜의 박스오피스 결과가 없습니다. 아직 영화진흥위원회의 집계가 끝나지 않았을 수 있습니다.")
    st.stop()

# 5. 데이터 가공하기 (문자열을 숫자로 변환)
df = pd.DataFrame(movies)
df["rank"] = df["rank"].astype(int)
df["audiCnt"] = df["audiCnt"].astype(int)
df["audiAcc"] = df["audiAcc"].astype(int)
df["scrnCnt"] = df["scrnCnt"].astype(int)

# 6. 화면에 1위 영화 지표 카드 보여주기
st.subheader("🏆 1위 영화")
top1 = df.iloc[0] # 순위가 가장 높은 첫 번째 행 데이터

col1, col2, col3 = st.columns(3)
with col1:
    st.metric(label=f"🥇 1위: {top1['movieNm']}", value=f"{top1['audiCnt']:,} 명", delta="어제 하루 관객수")
with col2:
    st.metric(label="누적 관객수", value=f"{top1['audiAcc']:,} 명")
with col3:
    st.metric(label="스크린 수", value=f"{top1['scrnCnt']:,} 개")

st.divider() # 구분선

# 7. 상위 5편 관객수 막대그래프 보여주기
st.subheader("📊 관객수 상위 5편")
top5_df = df.head(5)[["movieNm", "audiCnt"]].set_index("movieNm")
st.bar_chart(top5_df)

st.divider()

# 8. 전체 순위 표로 보여주기
st.subheader("📋 전체 박스오피스 순위")

# 표에 보여줄 컬럼만 선택하고 보기 좋게 이름 변경
display_df = df[["rank", "movieNm", "openDt", "audiCnt", "audiAcc", "scrnCnt"]].copy()
display_df.columns = ["순위", "영화명", "개봉일", "관객수(명)", "누적관객(명)", "스크린수(개)"]

# 숫자에 천 단위 콤마 포맷 적용
styled_df = display_df.style.format({
    "관객수(명)": "{:,}",
    "누적관객(명)": "{:,}",
    "스크린수(개)": "{:,}"
})

st.dataframe(styled_df, use_container_width=True, hide_index=True)
