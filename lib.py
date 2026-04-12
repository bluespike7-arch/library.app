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
    if not isbn:
        return "ISBN 없음"
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
        except:
            continue
    return best_region if best_count > 0 else "전국 분포"


# --- 1. 통합 데이터 가져오기 ---
def get_data(age="", gender="", lib_code="", region_code="", keyword="", size=30):
    rows = []

    if keyword:
        # ── STEP 1: srchBooks로 ISBN 목록 수집 ──
        search_title = keyword
        isbn_list = []

        for attempt in range(2):
            try:
                res = requests.get("http://data4library.kr/api/srchBooks", params={
                    'authKey': AUTH_KEY, 'title': search_title,
                    'exactMatch': 'false', 'pageSize': 30, 'format': 'json'
                }, timeout=10).json()
                book_docs = res.get('response', {}).get('docs', [])
            except:
                book_docs = []

            keyword_norm = keyword.replace(' ', '').lower()
            for i in book_docs:
                doc = i.get('doc', {})
                full_name = doc.get('bookname', '')
                clean_name = full_name.split(':')[0].strip() if ':' in full_name else full_name
                clean_norm = clean_name.replace(' ', '').lower()
                isbn = doc.get('isbn13', '')
                if isbn and (keyword_norm in clean_norm or clean_norm in keyword_norm):
                    isbn_list.append((isbn, clean_name, doc.get('authors', '-'), doc.get('publisher', '-')))

            if isbn_list:
                break
            search_title = keyword.replace(' ', '')  # 2차: 공백 제거 재시도

        if not isbn_list:
            return f"'{keyword}' 검색 결과가 없습니다.", None

        # ── STEP 2: 각 ISBN으로 loanItemSrch에서 지역/도서관 대출 데이터 조회 ──
        today = datetime.now()
        start_dt = (today - timedelta(days=60)).strftime('%Y-%m-%d')
        end_dt = today.strftime('%Y-%m-%d')

        for isbn, clean_name, authors, publisher in isbn_list:
            params = {
                'authKey': AUTH_KEY, 'startDt': start_dt, 'endDt': end_dt,
                'isbn13': isbn, 'pageSize': 1, 'format': 'json'
            }
            if lib_code:
                params['libCode'] = lib_code
            elif region_code:
                params['region'] = region_code

            try:
                raw = requests.get("http://data4library.kr/api/loanItemSrch", params=params, timeout=5).json()
                loan_docs = raw.get('response', {}).get('docs', [])
                if loan_docs:
                    d = loan_docs[0].get('doc', loan_docs[0])
                    loan_raw = d.get('loan_count') or d.get('loanCnt') or d.get('loanCount') or '0'
                    cum_raw = d.get('vol') or d.get('loan_count_total') or d.get('loanCntTotal') or '0'
                else:
                    loan_raw, cum_raw = '0', '0'
            except:
                loan_raw, cum_raw = '0', '0'

            try:
                loan_int = int(str(loan_raw).replace(',', ''))
                cum_int = int(str(cum_raw).replace(',', ''))
            except:
                loan_int, cum_int = 0, 0

            rows.append({
                '도서명': clean_name,
                '저자': authors,
                '출판사': publisher,
                '이달의 대출건수': loan_int,
                '누적 대출수': cum_int,
            })

        if not rows:
            return "해당 지역/도서관에 대출 데이터가 없습니다.", None

    else:
        # 키워드 없을 때: 인기도서 순위 조회
        url = "http://data4library.kr/api/loanItemSrch"
        today = datetime.now()
        start_dt = (today - timedelta(days=60)).strftime('%Y-%m-%d')
        end_dt = today.strftime('%Y-%m-%d')
        params = {
            'authKey': AUTH_KEY, 'startDt': start_dt, 'endDt': end_dt,
            'pageSize': size, 'format': 'json', 'age': age, 'gender': gender
        }
        if lib_code:
            params['libCode'] = lib_code
        elif region_code:
            params['region'] = region_code

        try:
            raw = requests.get(url, params=params, timeout=10).json()
            docs = raw.get('response', {}).get('docs', [])
            if not docs:
                return "데이터가 없습니다.", None

            for i in docs:
                doc = i.get('doc', i)
                loan_raw = doc.get('loan_count') or doc.get('loanCnt') or doc.get('loanCount') or '0'
                cum_raw = doc.get('vol') or doc.get('loan_count_total') or doc.get('loanCntTotal') or '0'
                try:
                    loan_int = int(str(loan_raw).replace(',', ''))
                    cum_int = int(str(cum_raw).replace(',', ''))
                except:
                    loan_int, cum_int = 0, 0

                rows.append({
                    '도서명': doc.get('bookname', '-'),
                    '저자': doc.get('authors', '-'),
                    '출판사': doc.get('publisher', '-'),
                    '이달의 대출건수': loan_int,
                    '누적 대출수': cum_int,
                })

        except Exception as e:
            return f"데이터 오류: {e}", None

    df = pd.DataFrame(rows)

    # 도서명 기준 그룹바이
    df = (
        df.groupby('도서명', as_index=False)
        .agg(
            저자=('저자', 'first'),
            출판사=('출판사', 'first'),
            이달의_대출건수=('이달의 대출건수', 'sum'),
            누적_대출수=('누적 대출수', 'sum'),
        )
        .sort_values('이달의_대출건수', ascending=False)
        .reset_index(drop=True)
    )

    df.insert(0, '순위', range(1, len(df) + 1))
    df['이달의 대출건수'] = df['이달의_대출건수'].apply(lambda x: f"{x:,}")
    df['누적 대출수'] = df['누적_대출수'].apply(lambda x: f"{x:,}")
    df = df.drop(columns=['이달의_대출건수', '누적_대출수'])

    return None, df


# --- 2. 도서 검색 함수 ---
def get_loan_count_by_region(isbn, region_code, start_dt, end_dt):
    """ISBN + 지역코드로 해당 지역 대출수 반환"""
    try:
        r = requests.get("http://data4library.kr/api/loanItemSrch", params={
            'authKey': AUTH_KEY, 'startDt': start_dt, 'endDt': end_dt,
            'isbn13': isbn, 'region': region_code, 'pageSize': 1, 'format': 'json'
        }, timeout=4).json()
        docs = r.get('response', {}).get('docs', [])
        if docs:
            d = docs[0].get('doc', docs[0])
            cnt_raw = d.get('loan_count') or d.get('loanCnt') or d.get('loanCount') or 0
            return int(str(cnt_raw).replace(',', ''))
    except:
        pass
    return 0


def search_book_by_name(book_name):
    if not book_name.strip():
        return "도서명을 입력하세요.", None
    try:
        # 1차: 원본 검색
        res = requests.get("http://data4library.kr/api/srchBooks", params={
            'authKey': AUTH_KEY, 'title': book_name,
            'exactMatch': 'false', 'pageSize': 20, 'format': 'json'
        }, timeout=10).json()
        docs = res.get('response', {}).get('docs', [])

        # 2차: 결과 없으면 공백 제거 후 재검색
        if not docs:
            no_space = book_name.replace(' ', '')
            res = requests.get("http://data4library.kr/api/srchBooks", params={
                'authKey': AUTH_KEY, 'title': no_space,
                'exactMatch': 'false', 'pageSize': 20, 'format': 'json'
            }, timeout=10).json()
            docs = res.get('response', {}).get('docs', [])

        if not docs:
            return f"'{book_name}' 검색 결과가 없습니다.", None

        # 검색어와 관련 있는 도서만 필터링
        keyword_norm = book_name.replace(' ', '').lower()
        filtered = []
        for i in docs:
            doc = i.get('doc', {})
            full_name = doc.get('bookname', '')
            clean_name = full_name.split(':')[0].strip() if ':' in full_name else full_name
            clean_norm = clean_name.replace(' ', '').lower()
            if keyword_norm in clean_norm or clean_norm in keyword_norm:
                filtered.append((doc, clean_name))

        if not filtered:
            return f"'{book_name}'와 일치하는 도서가 없습니다.", None

        # 날짜 범위 (최근 2달)
        today = datetime.now()
        start_dt = (today - timedelta(days=60)).strftime('%Y-%m-%d')
        end_dt = today.strftime('%Y-%m-%d')

        region_names = list(SEARCH_REGIONS.values())  # ['서울','경기','부산',...]
        region_codes = list(SEARCH_REGIONS.keys())

        rows = []
        total_steps = len(filtered) * len(region_codes)
        progress = st.progress(0, text="지역별 통계 분석 중...")
        step = 0

        for doc, clean_name in filtered:
            isbn = doc.get('isbn13', '')
            raw_loan = doc.get('loanCount') or doc.get('loan_count') or '0'
            try:
                total_loan = int(str(raw_loan).replace(',', ''))
            except:
                total_loan = 0

            region_counts = {}
            for code, name in SEARCH_REGIONS.items():
                cnt = get_loan_count_by_region(isbn, code, start_dt, end_dt) if isbn else 0
                region_counts[name] = cnt
                step += 1
                progress.progress(step / total_steps, text=f"지역별 통계 분석 중... ({name})")

            row = {
                '도서명': clean_name,
                '저자': doc.get('authors', '-'),
                '출판사': doc.get('publisher', '-'),
                '전국 누적 대출': total_loan,
            }
            for name in region_names:
                row[name] = region_counts.get(name, 0)
            rows.append(row)

        progress.empty()

        df = pd.DataFrame(rows)

        # 도서명 기준 그룹바이
        agg_dict = {
            '저자': ('저자', 'first'),
            '출판사': ('출판사', 'first'),
            '전국 누적 대출': ('전국 누적 대출', 'sum'),
        }
        for name in region_names:
            agg_dict[name] = (name, 'sum')

        df = (
            df.groupby('도서명', as_index=False)
            .agg(**agg_dict)
            .sort_values('전국 누적 대출', ascending=False)
            .reset_index(drop=True)
        )

        # 숫자 포맷
        df['전국 누적 대출'] = df['전국 누적 대출'].apply(lambda x: f"{x:,}")
        for name in region_names:
            df[name] = df[name].apply(lambda x: f"{x:,}" if x > 0 else "-")

        return None, df

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
        return {
            item['lib']['libName']: item['lib']['libCode']
            for item in libs
            if not sub_region_name or sub_region_name == "전체" or sub_region_name in item['lib']['address']
        }
    except:
        return {}


# --- UI 레이아웃 ---
st.title("📚 전국 도서관 데이터 통합 분석기")

REGION_DATA = {
    "서울특별시": {"code": "11", "sub": ["강남구","강동구","강북구","강서구","관악구","광진구","구로구","금천구","노원구","도봉구","동대문구","동작구","마포구","서대문구","서초구","성동구","성북구","송파구","양천구","영등포구","용산구","은평구","종로구","중구","중랑구"]},
    "경기도":     {"code": "41", "sub": ["가평군","고양시","과천시","광명시","광주시","구리시","군포시","김포시","남양주시","동두천시","부천시","성남시","수원시","시흥시","안산시","안성시","안양시","양주시","양평군","여주시","연천군","오산시","용인시","의왕시","의정부시","이천시","파주시","평택시","포천시","하남시","화성시"]},
    "인천광역시": {"code": "23", "sub": ["계양구","미추홀구","남동구","동구","부평구","서구","연수구","옹진군","중구","강화군"]},
    "대전광역시": {"code": "25", "sub": ["대덕구","동구","서구","유성구","중구"]},
    "대구광역시": {"code": "22", "sub": ["남구","달서구","달성군","동구","북구","서구","수성구","중구","군위군"]},
    "부산광역시": {"code": "21", "sub": ["강서구","금정구","기장군","남구","동구","동래구","부산진구","북구","사상구","사하구","서구","수영구","연제구","영도구","중구","해운대구"]},
    "광주광역시": {"code": "24", "sub": ["광산구","남구","동구","북구","서구"]},
}

# 사이드바
st.sidebar.header("🌟 퀵 메뉴")
if st.sidebar.button("🏆 전국 통합 인기 도서 100 조회"):
    err, df = get_data(size=100)
    if err:
        st.error(err)
    else:
        df_display = df.drop(columns=['누적 대출수'])
        st.subheader("🔥 대한민국 전체 인기 도서 (TOP 100)")
        st.dataframe(df_display, use_container_width=True, hide_index=True)

st.sidebar.markdown("---")
st.sidebar.subheader("🔍 특정 도서 누적 조회 (전국)")
search_query = st.sidebar.text_input("도서명 입력", key="global_search")
if st.sidebar.button("📖 대출수 조회"):
    err, df = search_book_by_name(search_query)
    if err:
        st.error(err)
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

local_keyword = st.sidebar.text_input("지역 내 도서 검색 (비워두면 인기순)", key="local_search")

if st.sidebar.button("🚀 지역 분석 실행"):
    use_region = REGION_DATA[main_region]["code"] if not selected_lib_code else ""
    with st.spinner("데이터 분석 중..."):
        err, df = get_data(
            age=age_dict[selected_age],
            lib_code=selected_lib_code,
            region_code=use_region,
            keyword=local_keyword
        )
    if err:
        st.error(err)
    else:
        title = f"📊 {selected_lib_name if selected_lib_code else main_region} "
        title += f"'{local_keyword}' 분석 결과" if local_keyword else "인기 도서 분석 결과"
        st.subheader(title)
        st.dataframe(df, use_container_width=True, hide_index=True)
