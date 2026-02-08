import streamlit as st
import requests
from bs4 import BeautifulSoup
import google.generativeai as genai

# 1. AI 엔진 설정
try:
    genai.configure(api_key=st.secrets["GOOGLE_API_KEY"])
    model = genai.GenerativeModel('gemini-1.5-flash')
except:
    st.error("Secrets에서 API 키를 확인해주세요.")

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
                raw_data.append({"언론사": press, "제목": a_tag.text.strip(), "링크": a_tag['href']})
    
    # AI에게 상위 30개 중 S급 5개만 골라달라고 요청 (정확도 위해 30개로 압축)
    titles_for_ai = "\n".join([f"{i}. {d['제목']}" for i, d in enumerate(raw_data[:40])])
    prompt = f"""
    너는 유튜브 조회수 100만 기획자야. 다음 뉴스 리스트 중 
    유튜브에서 '초바이럴'이 될 소재(S급) 5개의 번호만 골라줘.
    번호만 쉼표로 구분해서 답변해. 예: 1, 5, 12, 18, 25
    
    [뉴스 리스트]
    {titles_for_ai}
    """
    try:
        response = model.generate_content(prompt)
        s_indices = [int(x.strip()) for x in response.text.split(',') if x.strip().isdigit()]
    except:
        s_indices = []
    
    # 데이터에 S급 표시 추가 및 정렬 (S급을 최상단으로)
    for i, item in enumerate(raw_data):
        item['is_s'] = i in s_indices
        
    # S급이 위로 오도록 정렬
    sorted_data = sorted(raw_data, key=lambda x: x['is_s'], reverse=True)
    return sorted_data

def get_content(url):
    try:
        res = requests.get(url, headers={"User-Agent": "Mozilla/5.0"})
        soup = BeautifulSoup(res.text, 'html.parser')
        content = soup.select_one('#newsct_article') or soup.select_one('#articleBodyContents')
        return content.text.strip() if content else "본문 내용을 가져올 수 없습니다."
    except:
        return "뉴스 연결에 실패했습니다."

# --- 화면 레이아웃 ---
st.title("🔥 유메이커 MASTER : S급 소재 발굴기")
st.subheader("실시간 네이버 TOP 100 중 유튜브 떡상 소재만 골라드립니다.")

left_col, right_col = st.columns([1, 1.2])

with left_col:
    st.write("### 📊 실시간 뉴스 랭킹")
    if st.button("🔄 리스트 새로고침"):
        st.cache_data.clear()
        st.rerun()

    news_list = get_ranked_news_system()
    
    for i, row in enumerate(news_list):
        # S급 소재는 빨간색 강조 및 불꽃 아이콘
        if row['is_s']:
            btn_label = f"🚨 [S급 초바이럴] {row['제목']}"
        else:
            btn_label = f"{row['제목']}"
            
        if st.button(f"[{row['언론사']}] {btn_label}", key=f"btn_{i}", use_container_width=True):
            st.session_state.current_title = row['제목']
            st.session_state.current_content = get_content(row['リンク'])
            st.session_state.current_url = row['링크']
            st.session_state.is_s_class = row['is_s']

with right_col:
    st.write("### 📄 뉴스 원문 전문")
    if 'current_title' in st.session_state:
        if st.session_state.is_s_class:
            st.error(f"🎯 AI 기획자 판단: 이 소재는 무조건 'S급'입니다. 클로드로 가져가세요!")
        
        st.info(f"**제목: {st.session_state.current_title}**")
        st.caption(f"출처: {st.session_state.current_url}")
        st.text_area("내용", st.session_state.current_content, height=600)
    else:
        st.write("👈 왼쪽 리스트에서 분석하고 싶은 뉴스를 클릭하세요.")
