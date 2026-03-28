import requests
import pandas as pd
import streamlit as st
from datetime import datetime, timedelta

st.set_page_config(page_title="도서관 빅데이터 분석", layout="wide")

def get_data(api_key, age, gender, region):
    url = "http://data4library.kr/api/loanItemSrch"
    
    # 분석 기간: 지난달 1일 ~ 말일 (안전한 데이터 확보)
    last_month = datetime.now().replace(day=1) - timedelta(days=1)
    start_dt = last_month.replace(day=1).strftime('%Y-%m-%d')
    end_dt = last_month.strftime('%Y-%m-%d')

    params = {
        'authKey': api_key,
        'startDt': start_dt,
        'endDt': end_dt,
        'pageSize': 30,
        'format': 'json',
        'age': age,      # 연령대
        'gender': gender # 성별 (0: 남성, 1: 여성)
    }
    if region != "전국":
        params['region'] = region

    try:
        response = requests.get(url, params=params)
        data = response.json()
        
        if 'response' in data and 'error' in data['response']:
            return f"API 에러: {data['response']['error']}", None

        docs = data.get('response', {}).get('docs', [])
        if not docs:
            return "조회된 데이터가 없습니다.", None
            
        book_list = []
        for item in docs:
            book = item.get('doc')
            book_list.append({
                '순위': book.get('ranking'),
                '도서명': book.get('bookname'),
                '저자': book.get('authors'),
                '출판사': book.get('publisher'),
                '대출건수': book.get('loan_count')
            })
        return None, pd.DataFrame(book_list)
    except Exception as e:
        return f"시스템 오류: {e}", None

# --- UI 구성 ---
st.title("📊 전국 도서관 맞춤형 대출 트렌드")
st.sidebar.header("🔍 검색 필터")

api_key = st.sidebar.text_input("API 인증키 입력", type="password", help="도서관 정보나루에서 발급받은 키")

# 필터 옵션
region_dict = {"전국": "", "서울": "11", "경기": "41", "인천": "23", "부산": "21", "대구": "22"}
selected_region = st.sidebar.selectbox("지역 선택", list(region_dict.keys()))

age_dict = {"전체": "", "영유아(0-5)": "0", "유아(6-7)": "6", "초등(8-13)": "8", "청소년(14-19)": "14", 
            "20대": "20", "30대": "30", "40대": "40", "50대": "50", "60대 이상": "60"}
selected_age = st.sidebar.selectbox("연령대 선택", list(age_dict.keys()))

gender_dict = {"전체": "", "남성": "0", "여성": "1"}
selected_gender = st.sidebar.selectbox("성별 선택", list(gender_dict.keys()))

if st.sidebar.button("분석 실행"):
    if api_key:
        with st.spinner('데이터 분석 중...'):
            err, df = get_data(api_key, age_dict[selected_age], gender_dict[selected_gender], region_dict[selected_region])
            
            if err:
                st.error(err)
            else:
                st.success(f"✅ {selected_region} / {selected_age} / {selected_gender} 대출 순위입니다.")
                st.table(df) # 깔끔한 표로 출력
                
                # 다운로드 기능
                csv = df.to_csv(index=False).encode('utf-8-sig')
                st.download_button("결과를 엑셀(CSV)로 저장", data=csv, file_name=f"library_{datetime.now().strftime('%Y%m%d')}.csv")
    else:
        st.warning("왼쪽 사이드바에 API 키를 입력해 주세요.")