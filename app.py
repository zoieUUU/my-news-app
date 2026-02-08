import streamlit as st
import requests
from bs4 import BeautifulSoup
import pandas as pd

# 1. 화면을 넓게 쓰고 제목 설정
st.set_page_config(page_title="유메이커 MASTER", layout="wide")

# 디자인 살짝 가미
st.markdown("<style>div.block-container{padding-top:2rem;}</style>", unsafe_allow_html=True)

st.title("🔴 네이버 뉴스 실시간 분석기")

# 2. 뉴스 데이터 가져오기 함수
def get_news():
    url = "https://news.naver.com/main/ranking/popularDay.naver"
    headers = {"User-Agent": "Mozilla/5.0"}
    res = requests.get(url, headers=headers)
    soup = BeautifulSoup(res.text, 'html.parser')
    data = []
    for box in soup.select('.rankingnews_box'):
        press = box.select_one('.rankingnews_name').text.strip()
        for li in box.select('.rankingnews_list li'):
            a_tag = li.select_one('a')
            if a_tag:
                data.append({"언론사": press, "제목": a_tag.text.strip(), "링크": a_tag['href']})
    return data

# 뉴스 본문 긁어오기 함수
def get_article_content(url):
    try:
        headers = {"User-Agent": "Mozilla/5.0"}
        res = requests.get(url, headers=headers)
        soup = BeautifulSoup(res.text, 'html.parser')
        # 네이버 기사 본문 태그 찾기
        content = soup.select_one('#newsct_article') or soup.select_one('#articleBodyContents')
        return content.text.strip() if content else "본문을 가져올 수 없는 링크입니다."
    except:
        return "오류가 발생했습니다."

# 3. 화면 레이아웃 나누기 (왼쪽 1 : 오른쪽 1 비율)
left_col, right_col = st.columns(2)

news_list = get_news()
df = pd.DataFrame(news_list)

# --- 왼쪽 영역: 뉴스 리스트 ---
with left_col:
    st.subheader("📊 실시간 TOP 100")
    if st.button('🔄 새로고침'):
        st.rerun()
    
    # 클릭 가능한 리스트 만들기
    for i, row in df.iterrows():
        if st.button(f"{i}. [{row['언론사']}] {row['제목']}", key=f"btn_{i}"):
            st.session_state.current_url = row['링크']
            st.session_state.current_title = row['제목']

# --- 오른쪽 영역: 본문 텍스트 ---
with right_col:
    st.subheader("📄 뉴스 본문 텍스트")
    if 'current_url' in st.session_state:
        st.info(f"**선택된 뉴스:** {st.session_state.current_title}")
        content = get_article_content(st.session_state.current_url)
        
        # 본문을 박스 안에 이쁘게 넣기
        st.text_area("순수 텍스트", content, height=500)
        
        # 여기서 다음 단계 버튼
        if st.button("🎯 이 뉴스로 S급 소재 판별하기"):
            st.write("AI 분석 엔진 가동 중... (다음 단계에서 연결)")
    else:
        st.write("왼쪽에서 뉴스를 클릭하면 여기에 내용이 뜹니다.")