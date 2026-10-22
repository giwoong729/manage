import streamlit as st
import requests
import pandas as pd
import plotly.express as px
from datetime import datetime, timedelta, timezone

# 1. 페이지 기본 설정 (가장 먼저 실행)
st.set_page_config(page_title="박스오피스 명예의 전당", page_icon="🎫", layout="wide")

# ==========================================
# 🎨 커스텀 CSS (UI를 예쁘게 꾸며주는 역할)
# ==========================================
st.markdown("""
<style>
    /* VIP 티켓 스타일 (1위 영화) */
    .vip-ticket {
        background: linear-gradient(135deg, #FFD700 0%, #FDB931 100%);
        border-radius: 15px;
        padding: 30px;
        color: #333;
        text-align: center;
        box-shadow: 0 10px 20px rgba(0,0,0,0.15);
        border: 3px dashed #FFF;
        margin-bottom: 30px;
        transition: transform 0.3s;
    }
    .vip-ticket:hover { transform: scale(1.02); }
    .ticket-title { font-size: 1.2rem; font-weight: bold; color: #d35400; margin-bottom: 5px; }
    .ticket-movie { font-size: 2.8rem; font-weight: 900; margin: 10px 0; text-shadow: 1px 1px 2px rgba(255,255,255,0.8); line-height: 1.2;}
    .ticket-info { font-size: 1.1rem; font-weight: bold; background: rgba(255,255,255,0.4); padding: 10px; border-radius: 10px; display: inline-block;}
    
    /* 2위, 3위 카드 스타일 */
    .silver-card, .bronze-card {
        padding: 20px; border-radius: 15px; text-align: center; color: white; margin-top: 20px;
        box-shadow: 0 4px 8px rgba(0,0,0,0.1);
    }
    .silver-card { background: linear-gradient(135deg, #bdc3c7 0%, #2c3e50 100%); }
    .bronze-card { background: linear-gradient(135deg, #d35400 0%, #e67e22 100%); }
</style>
""", unsafe_allow_html=True)


# ==========================================
# ⚙️ 데이터 설정 및 API 호출
# ==========================================
with st.sidebar:
    st.image("https://cdn-icons-png.flaticon.com/512/3171/3171927.png", width=80) # 팝콘 아이콘
    st.title("Box Office V.I.P")
    
    KST = timezone(timedelta(hours=9))
    yesterday_kst = (datetime.now(KST) - timedelta(days=1)).date()
    
    selected_date = st.date_input("📅 타임머신 날짜 선택", value=yesterday_kst, max_value=yesterday_kst)
    target_dt = selected_date.strftime("%Y%m%d")
    
    st.divider()
    st.caption("Data Source: KOBIS (영화진흥위원회)")

@st.cache_data(ttl=1800, show_spinner=False)
def fetch_boxoffice(date_text, api_key):
    url = "https://www.kobis.or.kr/kobisopenapi/webservice/rest/boxoffice/searchDailyBoxOfficeList.json"
    response = requests.get(url, params={"key": api_key, "targetDt": date_text}, timeout=10)
    response.raise_for_status()
    return response.json()

try:
    API_KEY = st.secrets["KOBIS_KEY"]
except KeyError:
    st.error("🔐 KOBIS 인증키가 없습니다. Secrets 설정을 확인해 주세요.")
    st.stop()

with st.spinner(f"🎟️ {selected_date.strftime('%Y년 %m월 %d일')} 티켓을 발권 중입니다..."):
    try:
        data = fetch_boxoffice(target_dt, API_KEY)
    except Exception:
        st.error("🌐 서버 통신에 실패했습니다.")
        st.stop()

if "faultInfo" in data:
    st.error("🚨 API 인증 실패: KOBIS 인증키를 확인해 주세요.")
    st.stop()

movies = data.get("boxOfficeResult", {}).get("dailyBoxOfficeList", [])
if not movies:
    st.warning("📭 아직 영화진흥위원회 집계가 완료되지 않았습니다.")
    st.stop()

# ==========================================
# 📊 데이터 전처리
# ==========================================
df = pd.DataFrame(movies)
numeric_cols = ["rank", "rankInten", "audiCnt", "audiAcc", "scrnCnt"]
for col in numeric_cols:
    df
