import requests
import pandas as pd
import streamlit as st
from datetime import datetime, timedelta

st.set_page_config(page_title="내 집 앞 도서관 트렌드", layout="wide")

# 1. 지역별 도서관 목록 가져오기 함수
@st.cache_data # 동일 지역 조회 시 속도 향상
def get_library_list(api_key, region_code):
    url = "http://data4library.kr/api/libSrch"
    params = {
        'authKey': api_key,
        'region': region_code,
        'format': 'json',
        'pageSize': 500
    }
    try:
        response = requests.get(url, params=params)
        data = response.json()
        libs = data.get('response', {}).get('libs', [])
        lib_dict = {item['lib']['libName']: item['lib']['libCode'] for item in libs}
        return lib_dict
    except:
        return {}

# 2. 대출 데이터 가져오기 함수
def get_data(api_key, age, gender, lib_code):
    url = "http://data4library.kr/api/loanItemSrch"
    last_month = datetime.now().replace(day=1) - timedelta(days=1)
    
    params = {
        'authKey': api_key,
        'startDt': last_month.replace(day=1).strftime('%Y-%m-%d'),
        'endDt': last_month.strftime('%Y-%m-%d'),
        'pageSize': 30,
        'format': 'json',
        'age': age,
        'gender': gender,
        'libCode': lib_code  # 도서관 코드 적용
    }

    try:
        response = requests.get(url, params=params)
        data = response.json()
        docs = data.get('response', {}).get('docs', [])
        if not docs: return "데이터가 없습니다.", None
            
        book_list = [{'순위': i['doc']['ranking'], '도서명': i['doc']['bookname'], 
                      '저자': i['doc']['authors'], '대출건수': i['doc']['loan_count']} for i in docs]
        return None, pd.DataFrame(book_list)
    except Exception as e:
        return f"오류: {e}", None

# --- UI ---
st.title("📍 우리 동네 도서관 인기 도서 분석")
st.sidebar.header("🔍 상세 필터")

api_key = st.sidebar.text_input("API 인증키", type="password")

# 지역 코드 (강동구 추가)
region_dict = {"서울 전체": "11", "강동구": "11250", "강남구": "11230", "송파구": "11240", "경기 전체": "41"}
selected_region = st.sidebar.selectbox("1. 지역 선택", list(region_dict.keys()))

# 도서관 선택 (지역 선택에 따라 연동)
lib_list = {}
if api_key:
    lib_list = get_library_list(api_key, region_dict[selected_region])
    
selected_lib_name = st.sidebar.selectbox("2. 도서관 선택", ["해당 지역 전체"] + list(lib_list.keys()))
selected_lib_code = lib_list.get(selected_lib_name, "")

age_dict = {"전체": "", "20대": "20", "30대": "30", "40대": "40", "50대": "50"}
selected_age = st.sidebar.selectbox("3. 연령대", list(age_dict.keys()))

if st.sidebar.button("분석 실행"):
    if not api_key:
        st.warning("API 키를 입력하세요.")
    else:
        err, df = get_data(api_key, age_dict[selected_age], "", selected_lib_code)
        if err: st.error(err)
        else:
            st.success(f"✅ {selected_lib_name}의 인기 도서 결과입니다.")
            st.table(df)
