import streamlit as st
import requests
from bs4 import BeautifulSoup
import google.generativeai as genai

# 1. AI 엔진 설정
try:
    genai.configure(api_key=st.secrets["GOOGLE_API_KEY"])
    model = genai.GenerativeModel('gemini-1.5-flash')
except:
    st.error("Secrets에서 GOOGLE_API_KEY를 확인해주세요.")

st.set_page_config(page_title="유메이커 소재 발굴기", layout="wide")

# --- 뉴스 수집 및 AI 랭킹 분석 ---
@st.cache_data(ttl=600)
def get_ranked_news_system():
    url = "https://news.naver.com/main/ranking/popularDay.naver"
    headers = {"User-Agent": "Mozilla/5.0"}
    res = requests.get(url, headers=headers)
    soup = BeautifulSoup(res.text, 'html.parser')
    
    raw_data = []
    # 네이버 랭킹 뉴스 섹션에서 데이터 추출
    for box in soup.select('.rankingnews_box')[:12]:
        press = box.select_one('.rankingnews_name').text.strip()
        for li in box.select('.rankingnews_list li')[:5]:
            a_tag = li.select_one('a')
            if a_tag:
                # 데이터를 담을 때 키값을 'link'로 통일
                raw_data.append({"press": press, "title": a_tag.text.strip(), "link": a_tag['href']})
    
    # AI에게 S급 소재 5개 추천 요청
    titles_for_ai = "\n".join([f"{i}. {d['title']}" for i, d in enumerate(raw_data[:40])])
    prompt = f"유튜브 100만 기획자로서 다음 뉴스 중 가장 터질 소재 5개의 번호만 골라줘(쉼표 구분): {titles_for_ai}"
    
    try:
        response = model.generate_content(prompt)
        s_indices = [int(x.strip()) for x in response.text.split(',') if x.strip().isdigit()]
    except:
        s_indices = []
    
    for i, item in enumerate(raw_data):
        item['is_s'] = i in s_indices
        
    return sorted(raw_data, key=lambda x: x['is_s'], reverse=True)

def get_content(url):
    try:
        res = requests.get(url, headers={"User-Agent": "Mozilla/5.0"})
        soup = BeautifulSoup(res.text, 'html.parser')
        content = soup.select_one('#newsct_article') or soup.select_one('#articleBodyContents')
        return content.text.strip() if content else "본문 내용을 가져올 수 없습니다."
    except:
        return "뉴스 연결에 실패했습니다."

# --- 화면 레이아웃 ---
st.title("🔥 유메이커 MASTER : 소재 발굴기")

left_col, right_col = st.columns([1, 1.2])

with left_col:
    st.subheader("📊 실시간 랭킹 (AI S급 필터)")
    if st.button("🔄 리스트 새로고침"):
        st.cache_data.clear()
        st.rerun()

    news_list = get_ranked_news_system()
    
    for i, row in enumerate(news_list):
        # S급 표시 가시성 극대화
        label = f"🚨 [S급 추천] {row['title']}" if row['is_s'] else row['title']
        
        if st.button(f"[{row['press']}] {label}", key=f"btn_{i}", use_container_width=True):
            st.session_state.current_title = row['title']
            st.session_state.current_content = get_content(row['link'])
            st.session_state.current_url = row['link']
            st.session_state.is_s_class = row['is_s']

with right_col:
    st.subheader("📄 뉴스 원문 전문")
    if 'current_title' in st.session_state:
        if st.session_state.is_s_class:
            st.error("🎯 이 소재는 유튜브용 S급 소재입니다! 링크와 본문을 복사해 활용하세요.")
        
        st.info(f"**제목: {st.session_state.current_title}**")
        st.caption(f"링크: {st.session_state.current_url}")
        # 높이를 넉넉히 주어 읽기 편하게 설정
        st.text_area("기사 본문 텍스트", st.session_state.current_content, height=550)
    else:
        st.write("👈 리스트에서 뉴스를 선택하면 본문이 나옵니다.")
