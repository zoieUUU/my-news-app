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

st.set_page_config(page_title="VIRAL RANKING MASTER", layout="wide")

# CSS: S급 노란색 블록 강조 및 리스트 디자인
st.markdown("""
    <style>
    /* S급 노란색 블록 강조 */
    div.stButton > button:first-child[aria-label*="🚨"] {
        background-color: #FFD700 !important;
        color: #000000 !important;
        border: 2px solid #FFA500 !important;
        font-weight: 800 !important;
        font-size: 16px !important;
    }
    /* 일반 기사 블록 */
    div.stButton > button:first-child {
        background-color: #f0f2f6;
        border: 1px solid #d1d5db;
        text-align: left !important;
        display: block;
    }
    </style>
""", unsafe_allow_html=True)

# --- 전체 100개 뉴스 통합 수집 및 AI TOP 5 선별 ---
@st.cache_data(ttl=600)
def get_viral_top_100():
    url = "https://news.naver.com/main/ranking/popularDay.naver"
    headers = {"User-Agent": "Mozilla/5.0"}
    res = requests.get(url, headers=headers)
    soup = BeautifulSoup(res.text, 'html.parser')
    
    all_news = []
    # 네이버 모든 언론사의 랭킹 뉴스를 싹 긁어 모음
    for box in soup.select('.rankingnews_box'):
        press = box.select_one('.rankingnews_name').text.strip()
        for li in box.select('.rankingnews_list li'):
            a_tag = li.select_one('a')
            if a_tag:
                all_news.append({
                    "press": press,
                    "title": a_tag.text.strip(),
                    "link": a_tag['href']
                })
    
    # 중복 제거 및 100개 제한
    unique_news = list({v['title']:v for v in all_news}.values())[:100]
    
    # AI에게 전체 리스트 중 바이럴 TOP 5 선정 요청
    titles_chunk = "\n".join([f"{i}. {d['title']}" for i, d in enumerate(unique_news[:50])])
    prompt = f"""
    너는 100만 유튜버 기획자야. 다음 뉴스 50개 중 유튜브 썸네일로 만들었을 때 
    클릭률이 미친듯이 터질 소재(S급) 5개만 골라줘.
    답변은 오직 선택한 번호만 쉼표로 써라. 예: 1, 10, 15, 22, 30
    뉴스 리스트:
    {titles_chunk}
    """
    
    try:
        response = model.generate_content(prompt)
        s_indices = [int(x.strip()) for x in response.text.split(',') if x.strip().isdigit()]
    except:
        s_indices = []
    
    for i, item in enumerate(unique_news):
        item['is_s'] = i in s_indices
        
    # S급(노란색 블록)이 무조건 맨 위로 오게 정렬
    return sorted(unique_news, key=lambda x: x['is_s'], reverse=True)

def get_content(url):
    try:
        res = requests.get(url, headers={"User-Agent": "Mozilla/5.0"})
        soup = BeautifulSoup(res.text, 'html.parser')
        content = soup.select_one('#newsct_article') or soup.select_one('#articleBodyContents')
        return content.text.strip() if content else "본문을 가져올 수 없습니다."
    except: return "연결 실패"

# --- 메인 화면 ---
st.title("🔥 VIRAL RANKING MASTER")
st.subheader("언론사 통합 TOP 100 분석 : AI가 선정한 S급 바이럴 소재")

l_col, r_col = st.columns([1, 1.2])

with l_col:
    if st.button("🔄 전체 데이터 새로고침 (TOP 100 다시 읽기)"):
        st.cache_data.clear()
        st.rerun()
    
    final_list = get_viral_top_100()
    
    # 뉴스 리스트 출력
    for i, row in enumerate(final_list):
        # S급은 🚨 아이콘을 붙여 CSS에서 노란색 블록으로 인식하게 함
        prefix = "🚨 [VIRAL S-CLASS] " if row['is_s'] else f"[{i+1}] "
        btn_label = f"{prefix} {row['title']}"
        
        if st.button(f"{btn_label}", key=f"news_{i}", use_container_width=True):
            st.session_state.title = row['title']
            st.session_state.content = get_content(row['link'])
            st.session_state.is_s = row['is_s']

with r_col:
    if 'title' in st.session_state:
        if st.session_state.is_s:
            st.warning("⚡ 이 소재는 AI가 검증한 '돈 되는' 소재입니다. 지금 바로 제작하세요.")
        st.info(f"**제목: {st.session_state.title}**")
        st.text_area("뉴스 전문 텍스트", st.session_state.content, height=600)
    else:
        st.write("👈 왼쪽 리스트에서 노란색 [S-CLASS] 블록을 먼저 확인하세요.")
