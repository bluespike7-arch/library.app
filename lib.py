import requests
import pandas as pd
import streamlit as st
from datetime import datetime, timedelta

# 1. 초기 설정
st.set_page_config(page_title="우리 동네 도서관 분석", layout="wide", initial_sidebar_state="expanded")

# ==========================================
# 🔐 API 인증키 설정
# ==========================================
AUTH_KEY = "aca93962ef754c864256700d5130f3b3df3c490354ec911bfcdf42773fbfc355"
# ==========================================

# ✅ 고정 8개 지역 (도서 검색용)
SEARCH_REGIONS = {
    "11": "서울", "41": "경기", "21": "부산", "22": "대구",
    "23": "인천", "24": "광주", "25": "대전", "26": "울산",
}

def get_top_region_by_isbn(isbn):
    """ISBN으로 8개 주요 지역 중 최다 대출 지역 반환"""
    if not isbn: return "ISBN 없음"
    last_month = datetime.now().replace(day=1) - timedelta(days=1)
    start_dt = last_month.replace(day=1).strftime('%Y-%m-%d')
    end_dt = last_month.strftime('%Y-%m-%d')
    best_region, best_count = "확인 불가", 0
    for code, name in SEARCH_REGIONS.items():
        try:
            r = requests.get("http://data4library.kr/api/loanItemSrch", params={
                'authKey': AUTH_KEY, 'startDt': start_dt, 'endDt': end_dt,
                'isbn13': isbn, 'region': code, 'pageSize': 1, 'format': 'json'
            }, timeout=3).json()
            docs = r.get('response', {}).get('docs', [])
            if docs:
                d = docs[0]['doc']
                cnt_raw = d.get('loan_count') or d.get('loanCnt') or d.get('loanCount') or 0
                cnt = int(str(cnt_raw).replace(',', ''))
                if cnt > best_count:
                    best_count, best_region = cnt, name
        except: continue
    return best_region if best_count > 0 else "전국 분포"

# --- 1. 통합 데이터 가져오기 (도서명 검색 조건 추가) ---
def get_data(age="", gender="", lib_code="", region_code="", keyword="", size=30):
    # 키워드가 있을 때는 srchBooks API를 사용하고, 없을 때는 loanItemSrch(인기도서) 사용
    if keyword:
        url = "http://data4library.kr/api/srchBooks"
        params = {
            'authKey': AUTH_KEY, 'title': keyword, 'pageSize': size, 'format': 'json'
        }
    else:
        url = "http://data4library.kr/api/loanItemSrch"
        today = datetime.now()
        start_dt = (today - timedelta(days=60)).strftime('%Y-%m-%d')
        end_dt = today.strftime('%Y-%m-%d')
        params = {
            'authKey': AUTH_KEY, 'startDt': start_dt, 'endDt': end_dt,
            'pageSize': size, 'format': 'json', 'age': age, 'gender': gender
        }

    if lib_code: params['libCode'] = lib_code
    elif region_code: params['region'] = region_code

    try:
        raw = requests.get(url, params=params, timeout=10).json()
        docs = raw.get('response', {}).get('docs', [])
        if not docs: return "데이터가 없습니다.", None

        rows = []
        for i in docs:
            doc = i.get('doc', i)
            
            # 대출건수 통합 추출
            loan_raw = doc.get('loan_count') or doc.get('loanCnt') or doc.get('loanCount') or '0'
            # 누적 대출수 통합 추출
            cum_raw = doc.get('vol') or doc.get('loan_count_total') or doc.get('loanCntTotal') or '0'
            
            try:
                loan_int = int(str(loan_raw).replace(',', ''))
                cum_int = int(str(cum_raw).replace(',', ''))
                loan_display = f"{loan_int:,}"
                cum_display = f"{cum_int:,}"
            except:
                loan_display, cum_display = "0", "0"

            rows.append({
                '순위': doc.get('ranking', '-'),
                '도서명': doc.get('bookname', '-'),
                '저자': doc.get('authors', '-'),
                '이달의 대출건수': loan_display,
                '누적 대출수': cum_display,
                '출판사': doc.get('publisher', '-'),
            })
        return None, pd.DataFrame(rows)
    except Exception as e:
        return f"데이터 오류: {e}", None

# --- 2. 도서 검색 함수 (기존 좌측 메뉴용) ---
def search_book_by_name(book_name):
    if not book_name.strip(): return "도서명을 입력하세요.", None
    try:
        res = requests.get("http://data4library.kr/api/srchBooks", params={
            'authKey': AUTH_KEY, 'title': book_name, 'exactMatch': 'false', 'pageSize': 10, 'format': 'json'
        }, timeout=10).json()
        docs = res.get('response', {}).get('docs', [])
        if not docs: return f"'{book_name}' 검색 결과가 없습니다.", None

        rows = []
        progress = st.progress(0, text="지역별 통계 분석 중...")
        for idx, i in enumerate(docs):
            doc = i.get('doc', {})
            isbn = doc.get('isbn13', '')
            raw_loan = doc.get('loanCount') or doc.get('loan_count') or '0'
            
            progress.progress((idx + 1) / len(docs))
            top_region = get_top_region_by_isbn(isbn)

            rows.append({
                '도서명': doc.get('bookname', '-'),
                '저자': doc.get('authors', '-'),
                '출판사': doc.get('publisher', '-'),
                '전국 누적 대출': f"{int(str(raw_loan).replace(',','')):,}",
                '최다 대출 지역': top_region,
            })
        progress.empty()
        return None, pd.DataFrame(rows)
    except Exception as e:
        return f"분석 오류: {e}", None

# --- 3. 도서관 목록 가져오기 ---
@st.cache_data
def get_library_list(region_code, sub_region_name=None):
    try:
        r = requests.get("http://data4library.kr/api/libSrch", params={
            'authKey': AUTH_KEY, 'region': region_code, 'format': 'json', 'pageSize': 1000
        }, timeout=10).json()
        libs = r.get('response', {}).get('libs', [])
        return {item['lib']['libName']: item['lib']['libCode'] for item in libs 
                if not sub_region_name or sub_region_name == "전체" or sub_region_name in item['lib']['address']}
    except: return {}

# --- UI 레이아웃 ---
st.title("📚 전국 도서관 데이터 통합 분석기")

REGION_DATA = {
    "서울특별시": {"code": "11", "sub": ["강남구","강동구","강북구","강서구","관악구","광진구","구로구","금천구","노원구","도봉구","동대문구","동작구","마포구","서대문구","서초구","성동구","성북구","송파구","양천구","영등포구","용산구","은평구","종로구","중구","중랑구"]},
    "경기도": {"code": "41", "sub": ["가평군","고양시","과천시","광명시","광주시","구리시","군포시","김포시","남양주시","동두천시","부천시","성남시","수원시","시흥시","안산시","안성시","안양시","양주시","양평군","여주시","연천군","오산시","용인시","의왕시","의정부시","이천시","파주시","평택시","포천시","하남시","화성시"]},
    "인천광역시": {"code": "23", "sub": ["계양구","미추홀구","남동구","동구","부평구","서구","연수구","옹진군","중구","강화군"]},
}

# 사이드바
st.sidebar.header("🌟 퀵 메뉴")
if st.sidebar.button("🏆 전국 통합 인기 도서 100 조회"):
    err, df = get_data(size=100)
    if err: st.error(err)
    else:
        df_display = df.drop(columns=['누적 대출수']) # 요청하신 대로 전국은 누적 제거
        st.subheader("🔥 대한민국 전체 인기 도서 (TOP 100)")
        st.dataframe(df_display, use_container_width=True, hide_index=True)

st.sidebar.markdown("---")
st.sidebar.subheader("🔍 특정 도서 누적 조회 (전국)")
search_query = st.sidebar.text_input("도서명 입력", key="global_search")
if st.sidebar.button("📖 대출수 조회"):
    err, df = search_book_by_name(search_query)
    if err: st.error(err)
    else:
        st.subheader(f"✅ '{search_query}' 전국 검색 결과")
        st.dataframe(df, use_container_width=True, hide_index=True)

st.sidebar.markdown("---")
st.sidebar.subheader("📍 상세 지역 분석 (필터)")
main_region = st.sidebar.selectbox("광역시/도 선택", list(REGION_DATA.keys()))
selected_sub = st.sidebar.selectbox(f"{main_region} 세부 지역", ["전체"] + REGION_DATA[main_region]["sub"])
lib_list = get_library_list(REGION_DATA[main_region]["code"], selected_sub)
selected_lib_name = st.sidebar.selectbox("도서관 선택", ["해당 지역 전체"] + list(lib_list.keys()))
selected_lib_code = lib_list.get(selected_lib_name, "")

age_dict = {"전체": "", "20대": "20", "30대": "30", "40대": "40", "50대": "50"}
selected_age = st.sidebar.selectbox("연령대 선택", list(age_dict.keys()))

# ✅ [수정 포인트] 상세 지역 분석에 도서명 필터 추가
local_keyword = st.sidebar.text_input("지역 내 도서 검색 (비워두면 인기순)", key="local_search")

if st.sidebar.button("🚀 지역 분석 실행"):
    use_region = REGION_DATA[main_region]["code"] if not selected_lib_code else ""
    with st.spinner("데이터 분석 중..."):
        # 도서명(local_keyword)을 인자로 전달하여 필터링된 결과 유도
        err, df = get_data(
            age=age_dict[selected_age], 
            lib_code=selected_lib_code, 
            region_code=use_region,
            keyword=local_keyword
        )
    if err: st.error(err)
    else:
        title = f"📊 {selected_lib_name if selected_lib_code else main_region} "
        title += f"'{local_keyword}' 분석 결과" if local_keyword else "인기 도서 분석 결과"
        st.subheader(title)
        st.dataframe(df, use_container_width=True, hide_index=True)
