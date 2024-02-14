import requests
import time
import random
import re

from tqdm import tqdm
import pandas as pd
from bs4 import BeautifulSoup
from datetime import datetime, timedelta

from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.chrome.service import Service

random_number = random.uniform(3, 5)
now = datetime.now()


def web_driver(IS_COLAB):
    options = webdriver.ChromeOptions()
    options.add_argument("--verbose")
    options.add_argument("--no-sandbox")
    options.add_argument("--headless")
    options.add_argument("--disable-gpu")  # 가속 사용 x
    options.add_argument("--window-size=1920, 1200")
    options.add_argument("--disable-dev-shm-usage")

    options.add_argument("lang=ko_KR")  # 가짜 플러그인 탑재
    options.add_argument(
        "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/121.0.0.0 Safari/537.36"
    )  # user-agent 이름 설정

    if IS_COLAB:
        driver = webdriver.Chrome(options=options)

    else:
        from webdriver_manager.chrome import ChromeDriverManager

        driver = webdriver.Chrome(
            service=Service(ChromeDriverManager().install()), options=options
        )
    return driver


def get_data(keyword, startdate, enddate):
    # 직접입력 url
    url = f"https://search.naver.com/search.naver?where=news&query={keyword}&sm=tab_opt&sort=0&photo=0&field=0&pd=3&ds={startdate}&de={enddate}"

    print(url)
    driver = web_driver()
    driver.get(url)

    last_height = driver.execute_script("return document.body.scrollHeight")

    count = 0

    while True:
        # 끝까지 스크롤
        driver.execute_script("window.scrollTo(0, document.body.scrollHeight);")

        # 페이지 로드를 기다림
        time.sleep(random_number)
        count += 1
        print(f"{count}번째 페이지 수집 중")

        # 새로운 스크롤 높이 계산 및 비교
        new_height = driver.execute_script("return document.body.scrollHeight")
        if new_height == last_height:
            break

        last_height = new_height

        if count >= 1000:
            print("기사가 10000개 이상입니다. 수집을 종료합니다.")
            break

    # 일단 스코롤 모두 내림 -> 파싱 시작

    soup = BeautifulSoup(driver.page_source, "html.parser")

    driver.quit()
    return soup


# 정렬 순서를 지키려면


def parse_data(soup):
    dic_news = {"title": [], "date": [], "media": [], "url": []}

    for bx in tqdm(soup.select("ul.list_news li.bx")):
        # 원래 페이지 박스별 뉴스 기사 수집
        dic_news["title"].append(bx.select_one("a.news_tit").text)
        dic_news["date"].append(bx.select("span.info")[-1].text)
        dic_news["media"].append(
            bx.select_one("a.info").text.replace("언론사 선정", "")
        )
        dic_news["url"].append(bx.select_one("a.news_tit")["href"])

        # 더보기 페이지 박스별 뉴스 기사 수집
        if bx.select("a.news_more"):
            url_more = (
                "https://search.naver.com/search.naver"
                + bx.select("a.news_more")[0]["href"]
            )

            resp_more = requests.get(url_more)
            soup_more = BeautifulSoup(resp_more.content, "html.parser")

            for div in soup_more.select("div.news_area"):
                dic_news["title"].append(div.select_one("a.news_tit").text)
                dic_news["date"].append(div.select("span.info")[-1].text)
                dic_news["media"].append(
                    div.select_one("a.info").text.replace("언론사 선정", "")
                )
                dic_news["url"].append(div.select_one("a.news_tit")["href"])

    df = pd.DataFrame(dic_news)
    return df


# 현재 날짜와 시간


def convert_date(date_str):
    # YYYY.MM.DD 형식 확인 및 변환
    if re.match(r"\d{4}\.\d{2}\.\d{2}\.", date_str):
        return date_str  # 이미 YYYY.MM.DD 형식이므로 그대로 반환

    # 시간 및 분 확인 및 변환
    hours_ago = re.search(r"(\d+)시간 전", date_str)
    minutes_ago = re.search(r"(\d+)분 전", date_str)
    if hours_ago:
        calculated_date = now - timedelta(hours=int(hours_ago.group(1)))
        return calculated_date.strftime("%Y.%m.%d")
    elif minutes_ago:
        calculated_date = now - timedelta(minutes=int(minutes_ago.group(1)))
        return calculated_date.strftime("%Y.%m.%d")

    # 일 확인 및 변환
    days_ago = re.search(r"(\d+)일 전", date_str)
    if days_ago:
        calculated_date = now - timedelta(days=int(days_ago.group(1)))
        return calculated_date.strftime("%Y.%m.%d")

    # 주 확인 - 변환하지 않고 그대로 반환
    weeks_ago = re.search(r"(\d+)주 전", date_str)
    if weeks_ago:
        return date_str  # 주는 변환하지 않고 그대로 유지

    # 위의 경우에 해당하지 않는 경우 원래 문자열 반환
    return date_str


def clean_data(df):
    # 1. 날짜
    df["date"] = df["date"].apply(convert_date)

    # 2. 중복 데이터 삭제
    df.drop_duplicates(inplace=True, ignore_index=True)

    return df


if __name__ == "__main__":
    keyword = "레노버"
    startdate = "2024.01.01"
    enddate = "2024.02.28"

    print("입력하신 검색어 : ", keyword)
    print("입력하신 검색 기간 : ", f"{startdate} ~ {enddate}")

    soup = get_data(keyword, startdate, enddate)
    df = parse_data(soup)
    df_clean = clean_data(df)

    name = f"네이버뉴스_{keyword}_{startdate}-{enddate}.xlsx"
    df_clean.to_excel(name, index=False)
