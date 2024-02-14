import streamlit as st
from datetime import datetime, timedelta
import modules
import pandas as pd
import random
import time
from bs4 import BeautifulSoup


#### 파라미터
IS_COLAB = True 

random_number = random.uniform(3, 5)
now = datetime.now()

# 현재 날짜를 구하고, 시작 날짜를 오늘로부터 30일 전으로 설정
today = datetime.now().date()
start_date_default = today - timedelta(days=3)

#### 상태 구성
if "searchable" not in st.session_state:
    st.session_state.searchable = False
    
if "clicked" not in st.session_state:
    st.session_state.clicked = False
    
if "file_ready" not in st.session_state:
    st.session_state.file_ready = False
    

def click_button():
    st.session_state.error_message = ''
    st.session_state.result_message = ''

    if not keyword: # 검색어가 비어있다면
        st.session_state.searchable = False 
        st.session_state.error_message = "검색어를 입력해주세요."
    elif (not start_date) or (not end_date):
        st.session_state.searchable = False 
        st.session_state.error_message = "시작 날짜와 종료 날짜를 선택해주세요."
    
    elif (0 > int((end_date - start_date).days)) or (int((end_date - start_date).days) > 30):
        st.session_state.searchable = False 
        st.session_state.error_message = "기간을 수정해주세요. 최대 30일까지 가능합니다."
        
    else:
        st.session_state.result_message = f"""\n검색어 : {keyword}
                                             \n기간 : {start_date}부터 {end_date}까지"""   
        st.session_state.searchable = True
        st.session_state.clicked = True
    
    
def click_download():
    st.session_state.searchable = False
    st.session_state.clicked = False 
    st.session_state.file_ready = False
    st.session_state.result_message = ''
    st.session_state.error_message = ''


    
#####  화면 구성
# 화면 제목
st.title("네이버 뉴스 기사 수집")

# 검색어 입력창
keyword = st.text_input("검색어를 입력하세요!")

# 시작 날짜 입력창
start_date = st.date_input(
    "시작 날짜 선택",
    value=start_date_default,
    help="시작 날짜를 선택하세요. 기본값은 오늘로부터 3일 전입니다.",
)

# 종료 날짜 입력창
end_date = st.date_input(
    "종료 날짜 선택", value=today, help="종료 날짜를 선택하세요. 기본값은 오늘입니다."
)

# 검색 버튼 
btn_search = st.button("검색", key = 'btn_search', 
                       disabled = (st.session_state.searchable == True),
                       on_click = click_button
                       )

# 경고창 
con = st.container()
con.caption("Result")
if 'error_message' in st.session_state and st.session_state.error_message:
    con.error(st.session_state.error_message)
if 'result_message' in st.session_state and st.session_state.result_message:
    con.info(st.session_state.result_message)



###### 데이터 동작 함수 

def get_data(keyword, startdate, enddate):
    # 직접 입력한 URL
    url = f"https://search.naver.com/search.naver?where=news&query={keyword}&sm=tab_opt&sort=0&photo=0&field=0&pd=3&ds={startdate}&de={enddate}"
    st.info(f'수집 대상 네이버 페이지 : {url}')  # 화면에 URL 표시
    print(f'수집 대상 네이버 페이지 : {url}')  # 콘솔에 URL 표시

    driver = modules.web_driver(IS_COLAB)
    driver.get(url)

    last_height = driver.execute_script("return document.body.scrollHeight")
    count = 0
    max_count = 1000  # 예시로 설정한 최대 카운트 값

    with st.status("데이터 수집 중입니다"):
        while True:
            driver.execute_script("window.scrollTo(0, document.body.scrollHeight);")
            time.sleep(random.uniform(3, 5))  # 페이지 로드를 기다림
            
            count += 1  # 예시로 설정한 카운트 증가량

            # 진행 상황 업데이트
            
            progress_text = f"{count}번째 페이지 수집 중"
            st.write(progress_text)

            new_height = driver.execute_script("return document.body.scrollHeight")
            if new_height == last_height or count >= max_count :
                break
            last_height = new_height
        
    # 스크롤 완료 후 파싱 시작
    soup = BeautifulSoup(driver.page_source, "html.parser")
    driver.quit()
    return soup


#### 버튼 클릭 (실제 동작)
if st.session_state.clicked:

    # The message and nested widget will remain on the page
    msg_success = st.success("수집을 시작합니다!")

    # 입력된 날짜를 문자열로 변환 (YYYY.mm.dd 형식)
    start_date_str = start_date.strftime("%Y.%m.%d")
    end_date_str = end_date.strftime("%Y.%m.%d")

    # get_data 함수 실행
    soup = get_data(keyword, start_date_str, end_date_str)
    df = modules.parse_data(soup)
    df_clean = modules.clean_data(df)

    msg_success.empty()
    st.success("작업이 완료되었습니다. CSV파일을 다운로드하세요.")
    
    name = f"네이버뉴스_{keyword}_{start_date}-{end_date}.csv"
    df_clean.to_csv(name, index=False)
    st.session_state.file_ready = True
    st.session_state.clicked = False




######## 데이터 다운로드 
@st.cache_data
def convert_df(df):
    # IMPORTANT: Cache the conversion to prevent computation on every rerun
    try:
        return df.to_csv(index=False).encode("utf-8-sig")
    except :
        return df.to_csv(index=False).encode("cp949")
    
if st.session_state.file_ready: 
    csv = convert_df(df_clean)

    st.download_button(
        label="Download data as CSV",
        data=csv,
        file_name=name,
        mime="text/csv",
        on_click = click_download
    )
    
    
    

