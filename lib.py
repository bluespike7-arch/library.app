import requests
import pandas as pd
import streamlit as st
from datetime import datetime, timedelta

# 초기 사이드바 상태를 'expanded'(펼침)로 설정
st.set_page_config(
    page_title="우리 동네 도서관 분석", 
    layout="wide", 
    initial_sidebar_state="expanded"  # 이 부분을 추가했습니다.
)

# ==========================================
# 🔐 API 인증키 설정 (여기에 직접 입력)
# ==========================================
AUTH_KEY = "여기에_발급받은_인증키를_붙여넣으세요"
# ==========================================

# --- 1. 인기도서 가져오기 함수 ---
def get_data(age="", gender="", lib_code="", region_code="", size=30):
    url = "http://data4library.kr/api/loanItemSrch"
    last_month = datetime.now().replace(day=1) - timedelta(days=1)
    params = {
        'authKey': AUTH_KEY, 
        'startDt': last_month.replace(day=1).strftime('%Y-%m-%d'),
        'endDt': last_month.strftime('%Y-%m-%d'), 
        'pageSize': size, 'format': 'json',
        'age': age, 'gender': gender, 'libCode': lib_code, 'region': region_code
    }
    try:
        res = requests.get(url, params=params).json()
        docs = res.get('response', {}).get('docs', [])
        if not docs: return "데이터가 없습니다.", None
        df = pd.DataFrame([{
            '순위': i['doc']['ranking'], '도서명': i['doc']['bookname'], 
            '저자': i['doc']['authors'], '이달의 대출건수': i['doc']['loan_count'],
            '누적 대출수': i['doc'].get('vol', '0'), '출판사': i['doc']['publisher']
        } for i in docs])
        return None, df
    except: return "오류가 발생했습니다.", None

# --- 2. 도서 명칭으로 누적 대출수 검색 함수 ---
def search_book_by_name(book_name):
    url = "http://data4library.kr/api/srchBooks"
    params = {
        'authKey': AUTH_KEY, 'title': book_name, 'exactMatch': 'false',
        'pageSize': 10, 'format': 'json'
    }
    try:
        res = requests.get(url, params=params).json()
        docs = res.get('response', {}).get('docs', [])
        if not docs: return "검색 결과가 없습니다.", None
        
        search_results = []
        for i in docs:
            search_results.append({
                '도서명': i['doc']['bookname'],
                '저자': i['doc']['authors'],
                '출판사': i['doc']['publisher'],
                '출판년도': i['doc']['publication_year'],
                '전국 누적 대출수': i['doc']['loanCount']
            })
        return None, pd.DataFrame(search_results)
    except: return "검색 중 오류가 발생했습니다.", None

@st.cache_data
def get_library_list(region_code, sub_region_name=None):
    url = "http://data4library.kr/api/libSrch"
    params = {'authKey': AUTH_KEY, 'region': region_code, 'format': 'json', 'pageSize': 1000}
    try:
        response = requests.get(url, params=params).json()
        libs = response.get('response', {}).get('libs', [])
        lib_dict = {item['lib']['libName']: item['lib']['libCode'] for item in libs 
                    if not sub_region_name or sub_region_name == "전체" or sub_region_name in item['lib']['address']}
        return lib_dict
    except: return {}

# --- UI 레이아웃 ---
st.title("📚 전국 도서관 데이터 통합 분석기")

# 사이드바 설정 (인증키 입력란 삭제)
st.sidebar.header("🌟 퀵 메뉴")

if st.sidebar.button("🏆 전국 통합 인기 도서 100 조회"):
    err, df = get_data(size=100)
    if err: st.error(err)
    else:
        st.subheader("🔥 대한민국 전체 도서관 인기 도서 (TOP 100)")
        st.dataframe(df, use_container_width=True, hide_index=True)

st.sidebar.markdown("---")
st.sidebar.subheader("🔍 특정 도서 누적 조회")
search_query = st.sidebar.text_input("조회할 도서명을 입력하세요")
if st.sidebar.button("📖 대출수 조회"):
    if search_query:
        err, df = search_book_by_name(search_query)
        if err: st.error(err)
        else:
            st.subheader(f"✅ '{search_query}' 검색 결과 (누적 대출수)")
            st.dataframe(df, use_container_width=True, hide_index=True)

st.sidebar.markdown("---")
st.sidebar.subheader("📍 상세 지역 분석")
REGION_DATA = {
    "서울특별시": {"code": "11", "sub": ["강남구", "강동구", "강북구", "강서구", "관악구", "광진구", "구로구", "금천구", "노원구", "도봉구", "동대문구", "동작구", "마포구", "서대문구", "서초구", "성동구", "성북구", "송파구", "양천구", "영등포구", "용산구", "은평구", "종로구", "중구", "중랑구"]},
    "부산광역시": {"code": "21", "sub": ["강서구", "금정구", "기장군", "남구", "동구", "동래구", "부산진구", "북구", "사상구", "사하구", "서구", "수영구", "연제구", "영도구", "중구", "해운대구"]},
    "경기도": {"code": "41", "sub": ["가평군", "고양시", "과천시", "광명시", "광주시", "구리시", "군포시", "김포시", "남양주시", "동두천시", "부천시", "성남시", "수원시", "시흥시", "안산시", "안성시", "안양시", "양주시", "양평군", "여주시", "연천군", "오산시", "용인시", "의왕시", "의정부시", "이천시", "파주시", "평택시", "포천시", "하남시", "화성시"]},
}

main_region = st.sidebar.selectbox("광역시/도 선택", list(REGION_DATA.keys()))
selected_sub = st.sidebar.selectbox(f"{main_region} 세부 지역", ["전체"] + REGION_DATA[main_region]["sub"])
lib_list = get_library_list(REGION_DATA[main_region]["code"], selected_sub)
selected_lib_name = st.sidebar.selectbox("도서관 선택", ["해당 지역 전체"] + list(lib_list.keys()))
selected_lib_code = lib_list.get(selected_lib_name, "")

age_dict = {"전체": "", "20대": "20", "30대": "30", "40대": "40", "50대": "50"}
selected_age = st.sidebar.selectbox("연령대 선택", list(age_dict.keys()))

if st.sidebar.button("🚀 지역 분석 실행"):
    err, df = get_data(age_dict[selected_age], "", selected_lib_code, size=30)
    if err: st.error(err)
    else:
        st.subheader(f"✅ {main_region} {selected_sub} 결과")
        st.dataframe(df, use_container_width=True, hide_index=True)
