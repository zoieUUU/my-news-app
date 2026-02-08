import streamlit as st
import requests
from bs4 import BeautifulSoup
import google.generativeai as genai

# AI 설정
genai.configure(api_key=st.secrets["GOOGLE_API_KEY"])
model = genai.GenerativeModel('gemini-1.5-flash')

st.set_page_config(page_title="유메이커 MASTER", layout="wide")

# --- 뉴스 수집 및 AI S급 자동 선별 ---
@st.cache_data(ttl=600)
def get_and_rank_news():
    url = "https://news.naver.com/main/ranking/popularDay.naver"
    headers = {"User-Agent": "Mozilla/5.0"}
    res = requests.get(url, headers=headers)
    soup = BeautifulSoup(res.text, 'html.parser')
    
    raw_data = []
    for box in soup.select('.rankingnews_box')[:10]:
        press = box.select_one('.rankingnews_name').text.strip()
        for li in box.select('.rankingnews_list li')[:5]:
            a_tag = li.select_one('a')
            if a_tag:
                raw_data.append({"언론사": press, "제목": a_tag.text.strip(), "링크": a_tag['href']})
    
    # AI에게 떡상 소재 5개만 골라달라고 요청
    all_titles = "\n".join([f"{i}. {d['제목']}" for i, d in enumerate(raw_data)])
    pick_prompt = f"""
    너는 유튜브 이슈 채널 대형 기획자야. 
    다음 네이버 뉴스 리스트 중에서 유튜브 조회수가 폭발할(S급 소재) 5가지를 골라줘.
    [뉴스 리스트]
    {all_titles}
    
    결과는 오직 선택된 번호만 쉼표로 구분해서 말해줘. (예: 1, 5, 12, 20, 31)
    """
    try:
        response = model.generate_content(pick_prompt)
        s_class_indices = [int(i.strip()) for i in response.text.split(',')]
    except:
        s_class_indices = []
        
    return raw_data, s_class_indices

def get_content(url):
    res = requests.get(url, headers={"User-Agent": "Mozilla/5.0"})
    soup = BeautifulSoup(res.text, 'html.parser')
    content = soup.select_one('#newsct_article') or soup.select_one('#articleBodyContents')
    return content.text.strip() if content else "본문 추출 실패"

# --- 화면 구성 ---
st.title("🚀 유메이커 MASTER : S급 소재 판별기")
left_col, right_col = st.columns([1, 1.2])

with left_col:
    st.subheader("🔥 실시간 TOP 100 (AI S급 추천)")
    news_list, s_picks = get_and_rank_news()
    
    for i, row in enumerate(news_list):
        is_s_class = i in s_picks
        # S급인 경우 빨간색 버튼과 불꽃 아이콘 표시
        label = f"🔥 [S급 유력] {row['제목']}" if is_s_class else f"{row['제목']}"
        
        if st.button(f"[{row['언론사']}] {label}", key=f"n_{i}", use_container_width=True):
            st.session_state.url = row['링크']
            st.session_state.title = row['제목']
            st.session_state.content = get_content(row['링크'])
            st.session_state.is_s = is_s_class

with right_col:
    if 'title' in st.session_state:
        # S급 하이라이트 박스
        if st.session_state.get('is_s'):
            st.error(f"🎯 AI 판단: 이 소재는 유튜브 100만 조회수 가능성이 매우 높습니다!")
        
        st.subheader("📄 뉴스 원문 텍스트")
        st.info(f"**{st.session_state.title}**")
        st.text_area("본문", st.session_state.content, height=250)
        
        if st.button("🚀 S급 마스터 대본 생성", type="primary", use_container_width=True):
            # ... (대본 생성 프롬프트 로직 - 기존과 동일) ...
            pass
