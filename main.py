import streamlit as st
import requests
import pandas as pd
from datetime import datetime, timedelta, timezone

# 1. 페이지 기본 설정
st.set_page_config(page_title="일일 박스오피스", page_icon="🎬", layout="wide")
st.title("🍿 일일 박스오피스 조회")

# 2. 한국 시간 기준으로 '어제' 날짜 계산하기
KST = timezone(timedelta(hours=9))
today_kst = datetime.now(KST).date()
yesterday_kst = today_kst - timedelta(days=1)

# 달력 위젯 생성 (가장 늦은 날짜를 어제로 제한)
selected_date = st.date_input(
    "조회할 날짜를 선택하세요", 
    value=yesterday_kst, 
    max_value=yesterday_kst
)

# API가 요구하는 yyyymmdd 형식으로 변환
target_dt = selected_date.strftime("%Y%m%d") 

# 3. KOBIS API 연동 및 데이터 가져오기
@st.cache_data(ttl=3600) # 한 번 불러온 데이터는 1시간 동안 임시 저장
def fetch_box_office(date_str):
    url = "https://www.kobis.or.kr/kobisopenapi/webservice/rest/boxoffice/searchDailyBoxOfficeList.json"
    
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
        response.raise_for_status()
        return response.json()
    except Exception as e:
        return {"error": "network_fail", "details": str(e)}

# 선택한 날짜로 데이터 요청
data = fetch_box_office(target_dt)

# 4. 에러 및 예외 상황 처리하기
if "error" in data:
    if data["error"] == "secret_missing":
        st.error("🚨 스트림릿 비밀 금고(secrets)에 'KOBIS_KEY'가 설정되어 있지 않습니다.")
