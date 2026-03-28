import requests
import pandas as pd
import streamlit as st
from datetime import datetime, timedelta

st.set_page_config(page_title="우리 동네 도서관 분석", layout="wide")

# --- 데이터 가져오기 함수 (pageSize를 100으로 변경) ---
def get_data(api_key, age="", gender="", lib_code="", region_code="", size=30):
    if not api_key: return "API 키를 먼저 입력해주세요.", None
    url = "http://data4library.kr/api/loanItemSrch"
    
    # 지난달 기준 데이터 조회
    last_month = datetime.now().replace(day=1) - timedelta(days=1)
    
    params = {
        'authKey': api_key,
        'startDt': last_month.replace(day=1).strftime('%Y-%m-%d'),
        'endDt': last_month.strftime('%Y-%m-%d'),
        'pageSize': size,  # 요청하신 대로 데이터 개수 조절 가능
        'format': 'json',
        'age': age,
        'gender': gender,
        'libCode': lib_code,
        'region': region_code
    }
    
    try:
        response = requests.get(url, params=params)
        res = response.json()
        docs = res.get('response', {}).get('docs', [])
        if not docs: return "데이터가 없습니다.", None
        
        df = pd.DataFrame([
            {
                '순위': i['doc']['ranking'], 
                '도서명': i['doc']['bookname'], 
                '저자': i['doc']['authors'], 
                '대출건수': i['doc']['loan_count'],
                '출판사': i['doc']['publisher']
            } for i in docs
        ])
        return None, df
    except:
        return "데이터를 가져오는 중 오류가 발생했습니다.", None

@st.cache_data
def get_library_list(api_key, region_code, sub_region_name=None):
    if not api_key: return {}
    url = "http://data4library.kr/api/libSrch"
    params = {'authKey': api_key, 'region': region_code, 'format': 'json', 'pageSize': 1000}
    try:
        response = requests.get(url, params=params)
        data = response.json()
        libs = data.get('response', {}).get('libs', [])
        lib_dict = {}
        for item in libs:
            name, code, addr = item['lib']['libName'], item['lib']['libCode'], item['lib']['address']
            if sub_region_name and sub_region_name != "전체":
                if sub_region_name in addr: lib_dict[name] = code
            else: lib_dict[name] = code
        return lib_dict
    except: return {}

# --- 전국 지자체 데이터 ---
REGION_DATA = {
    "서울특별시": {"code": "11", "sub": ["강남구", "강동구", "강북구", "강서구", "관악구", "광진구", "구로구", "금천구", "노원구", "도봉구", "동대문구", "동작구", "마포구", "서대문구", "서초구", "성동구", "성북구", "송파구", "양천구", "영등포구", "용산구", "은평구", "종로구", "중구", "중랑구"]},
    "부산광역시": {"code": "21", "sub": ["강서구", "금정구", "기장군", "남구", "동구", "동래구", "부산진구", "북구", "사상구", "사하구", "서구", "수영구", "연제구", "영도구", "중구", "해운대구"]},
    "대구광역시": {"code": "22", "sub": ["남구", "달서구", "달성군", "동구", "북구", "서구", "수성구", "중구", "군위군"]},
    "인천광역시": {"code": "23", "sub": ["계양구", "미추홀구", "남동구", "동구", "부평구", "서구", "연수구", "옹진군", "중구", "강화군"]},
    "경기도": {"code": "41", "sub": ["가평군", "고양시", "과천시", "광명시", "광주시", "구리시", "군포시", "김포시", "남양주시", "동두천시", "부천시", "성남시", "수원시", "시흥시", "안산시", "안성시", "안양시", "양주시", "양평군", "여주시", "연천군", "오산시", "용인시", "의왕시", "의정부시", "이천시", "파주시", "평택시", "포천시", "하남시", "화성시"]},
}

# --- UI 레이아웃 ---
st.title("📚 전국 도서관 대출 데이터 분석")

# 사이드바 설정
st.sidebar.header("🔑 인증 및 빠른 조회")
api_key = st.sidebar.text_input("API 인증키 입력", type="password")

# --- 수정된 부분: 인기도서 100 버튼 ---
st.sidebar.markdown("---")
st.sidebar.subheader("🌟 퀵 메뉴")
if st.sidebar.button("🏆 전국 통합 인기 도서 100"):
    err, df = get_data(api_key, size=100) # size를 100으로 전달
    if err: st.error(err)
    else:
        st.subheader("🔥 대한민국 전체 도서관 인기 도서 (TOP 100)")
        st.dataframe(df, use_container_width=True, hide_index=True)

st.sidebar.markdown("---")
st.sidebar.subheader("📍 상세 지역 분석")

main_region = st.sidebar.selectbox("1. 광역시/도 선택", list(REGION_DATA.keys()))
sub_regions = ["전체"] + REGION_DATA[main_region]["sub"]
selected_sub = st.sidebar.selectbox(f"2. {main_region} 세부 지역", sub_regions)

lib_list = get_library_list(api_key, REGION_DATA[main_region]["code"], selected_sub) if api_key else {}
selected_lib_name = st.sidebar.selectbox("3. 도서관 선택", ["해당 지역 전체"] + list(lib_list.keys()))
selected_lib_code = lib_list.get(selected_lib_name, "")

age_dict = {"전체": "", "영유아(0-5세)": "0", "유아(6-7세)": "6", "초등(8-13세)": "8", "청소년(14-19세)": "14", "20대": "20", "30대": "30", "40대": "40", "50대": "50", "60대 이상": "60"}
selected_age = st.sidebar.selectbox("4. 연령대 선택", list(age_dict.keys()))

gender_dict = {"전체": "", "남성": "0", "여성": "1"}
selected_gender = st.sidebar.selectbox("5. 성별 선택", list(gender_dict.keys()))

if st.sidebar.button("🚀 지역 맞춤 분석 실행"):
    err, df = get_data(api_key, age_dict[selected_age], gender_dict[selected_gender], selected_lib_code, size=30)
    if err: st.error(err)
    else:
        st.subheader(f"✅ {main_region} {selected_sub} - {selected_lib_name} ({selected_age}/{selected_gender}) 결과")
        st.dataframe(df, use_container_width=True, hide_index=True)
