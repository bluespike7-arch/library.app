import requests
import pandas as pd
import streamlit as st
from datetime import datetime, timedelta

st.set_page_config(page_title="우리 동네 도서관 분석", layout="wide")

# 1. 광역/기초 지자체 코드 데이터 (전국 광역시 및 구 포함)
REGION_DATA = {
    "서울특별시": {"code": "11", "sub": ["종로구", "중구", "용산구", "성동구", "광진구", "동대문구", "중랑구", "성북구", "강북구", "도봉구", "노원구", "은평구", "서대문구", "마포구", "양천구", "강서구", "구로구", "금천구", "영등포구", "동작구", "관악구", "서초구", "강남구", "송파구", "강동구"]},
    "부산광역시": {"code": "21", "sub": ["중구", "서구", "동구", "영도구", "부산진구", "동래구", "남구", "북구", "해운대구", "사하구", "금정구", "강서구", "연제구", "수영구", "사상구", "기장군"]},
    "대구광역시": {"code": "22", "sub": ["중구", "동구", "서구", "남구", "북구", "수성구", "달서구", "달성군", "군위군"]},
    "인천광역시": {"code": "23", "sub": ["중구", "동구", "미추홀구", "연수구", "남동구", "부평구", "계양구", "서구", "강화군", "옹진군"]},
    "광주광역시": {"code": "24", "sub": ["동구", "서구", "남구", "북구", "광산구"]},
    "대전광역시": {"code": "25", "sub": ["동구", "중구", "서구", "유성구", "대덕구"]},
    "울산광역시": {"code": "26", "sub": ["중구", "남구", "동구", "북구", "울주군"]},
    "세종특별자치시": {"code": "29", "sub": ["세종시"]},
    "경기도": {"code": "41", "sub": ["수원시", "용인시", "고양시", "화성시", "성남시", "부천시", "남양주시", "안산시", "평택시", "안양시", "시흥시", "파주시", "김포시", "의정부시", "광주시", "하남시", "광명시", "군포시", "양주시", "오산시", "이천시", "안성시", "구리시", "의왕시", "포천시", "양평군", "여주시", "동두천시", "가평군", "과천시", "연천군"]},
    "강원특별자치도": {"code": "42", "sub": ["춘천시", "원주시", "강릉시", "동해시", "태백시", "속초시", "삼척시", "홍천군", "횡성군", "영월군", "평창군", "정선군", "철원군", "화천군", "양구군", "인제군", "고성군", "양양양"]},
} # 다른 도(충청, 전라, 경상, 제주)도 동일한 방식으로 추가 가능합니다.

# 2. 도서관 목록 가져오기 함수
@st.cache_data
def get_library_list(api_key, region_code, sub_region_name=None):
    url = "http://data4library.kr/api/libSrch"
    # 구 단위 검색이 지원되지 않는 경우를 대비해 region만 사용하거나 상세 검색 로직 필요
    # 여기서는 선택한 광역 단위 내의 모든 도서관을 가져온 후 파이썬으로 필터링합니다.
    params = {'authKey': api_key, 'region': region_code, 'format': 'json', 'pageSize': 1000}
    try:
        response = requests.get(url, params=params)
        data = response.json()
        libs = data.get('response', {}).get('libs', [])
        
        # 구(sub_region)가 선택되었다면 해당 구가 주소에 포함된 도서관만 필터링
        lib_dict = {}
        for item in libs:
            name = item['lib']['libName']
            code = item['lib']['libCode']
            address = item['lib']['address']
            if sub_region_name and sub_region_name != "전체":
                if sub_region_name in address:
                    lib_dict[name] = code
            else:
                lib_dict[name] = code
        return lib_dict
    except:
        return {}

# 3. 대출 데이터 가져오기 함수 (기존과 동일)
def get_data(api_key, age, gender, lib_code):
    url = "http://data4library.kr/api/loanItemSrch"
    last_month = datetime.now().replace(day=1) - timedelta(days=1)
    params = {
        'authKey': api_key, 'startDt': last_month.replace(day=1).strftime('%Y-%m-%d'),
        'endDt': last_month.strftime('%Y-%m-%d'), 'pageSize': 30, 'format': 'json',
        'age': age, 'gender': gender, 'libCode': lib_code
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

# --- UI 레이아웃 ---
st.title("📊 전국 도서관 맞춤형 대출 트렌드")
st.sidebar.header("📍 지역 및 필터 설정")

api_key = st.sidebar.text_input("1. API 인증키 입력", type="password")

# 광역 지역 선택
main_region = st.sidebar.selectbox("2. 광역시/도 선택", list(REGION_DATA.keys()))

# 기초 지역(구/시/군) 선택
sub_regions = ["전체"] + REGION_DATA[main_region]["sub"]
selected_sub = st.sidebar.selectbox(f"3. {main_region} 세부 지역", sub_regions)

# 도서관 선택 (API 키가 있을 때만 작동)
lib_list = {}
if api_key:
    with st.spinner('해당 지역 도서관 목록을 불러오는 중...'):
        lib_list = get_library_list(api_key, REGION_DATA[main_region]["code"], selected_sub)
    
    if not lib_list:
        st.sidebar.warning("선택한 지역에 조회 가능한 도서관이 없습니다.")
else:
    st.sidebar.info("💡 API 키를 입력하면 도서관 목록이 나타납니다.")

selected_lib_name = st.sidebar.selectbox("4. 도서관 선택", ["해당 지역 전체"] + list(lib_list.keys()))
selected_lib_code = lib_list.get(selected_lib_name, "")

age_dict = {"전체": "", "영유아(0-5세)": "0", "유아(6-7세)": "6", "초등(8-13세)": "8", "청소년(14-19세)": "14", "20대": "20", "30대": "30", "40대": "40", "50대": "50", "60대 이상": "60"}
selected_age = st.sidebar.selectbox("5. 연령대 선택", list(age_dict.keys()))

if st.sidebar.button("🚀 분석 실행"):
    if not api_key:
        st.error("API 키를 입력해주세요.")
    else:
        err, df = get_data(api_key, age_dict[selected_age], "", selected_lib_code)
        if err: st.error(err)
        else:
            st.success(f"✅ {main_region} {selected_sub} - {selected_lib_name} 결과")
            st.dataframe(df, use_container_width=True)
