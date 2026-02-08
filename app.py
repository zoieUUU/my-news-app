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

st.set_page_config(page_title="VIRAL RANKING MASTER", layout="wide")

# --- 뉴스 수집 및 AI 바이럴 랭킹 선정 ---
@st.cache_data(ttl=600)
def get_viral_top_100():
    url = "https://news.naver.com/main/ranking/popularDay.naver"
    headers = {"User-Agent": "Mozilla/5.0"}
    res = requests.get(url, headers=headers)
    soup = BeautifulSoup(res.text, 'html.parser')
    
    unique_news = []
    seen_titles = set()
    
    for box in soup.select('.rankingnews_box'):
        for li in box.select('.rankingnews_list li'):
            a_tag = li.select_one('a')
            if a_tag:
                title = a_tag.text.strip()
                if title not in seen_titles:
                    unique_news.append({"title": title, "link": a_tag['href']})
                    seen_titles.add(title)

    # AI에게 TOP 5 선정 요청 (상위 40개 중)
    titles_list = "\n".join([f"{i}. {d['title']}" for i, d in enumerate(unique_news[:40])])
    prompt = f"유튜브 조회수 대박날 소재 5개의 번호만 골라줘(쉼표 구분): {titles_list}"
    
    try:
        resp = model.generate_content(prompt)
        s_indices = [int(x.strip()) for x in resp.text.split(',') if x.strip().isdigit()]
    except:
        s_indices = []
    
    for i, item in enumerate(unique_news):
        item['is_s'] = i in s_indices
        item['rank'] = i + 1
        
    return sorted(unique_news, key=lambda x: x['is_s'], reverse=True)

# --- 뉴스 본문 추출 및 AI 요약/키워드 생성 ---
def get_ai_analysis(url):
    try:
        res = requests.get(url, headers={"User-Agent": "Mozilla/5.0"})
        soup = BeautifulSoup(res.text, 'html.parser')
        content = soup.select_one('#newsct_article') or soup.select_one('#articleBodyContents')
        text = content.text.strip() if content else "본문 추출 실패"
        
        if text != "본문 추출 실패":
            analysis_prompt = f"""
            아래 기사를 분석해서 다음 양식으로 출력해줘:
            1. 요약: (기사 내용을 2줄로 요약)
            2. 키워드: (중요도 순으로 키워드 5개, 쉼표 구분)
            
            기사 내용: {text[:2000]}
            """
            resp = model.generate_content(analysis_prompt)
            return text, resp.text
        return text, "분석 불가"
    except:
        return "연결 실패", "분석 불가"

# --- 화면 구성 ---
st.title("🔥 VIRAL RANKING MASTER")
st.markdown("### 🚀 실시간 통합 랭킹 : AI 선정 바이럴 S급")

l, r = st.columns([1, 1.2])

with l:
    if st.button("🔄 전체 랭킹 새로고침"):
        st.cache_data.clear()
        st.rerun()
    
    data = get_viral_top_100()
    
    for i, row in enumerate(data):
        if row['is_s']:
            # S급 기사는 강제로 노란색 카드 안에 배치
            st.markdown(f"""
                <div style="background-color: #FFD700; padding: 12px; border-radius: 10px; border: 3px solid #FF8C00; margin-bottom: -40px; position: relative; z-index: 1;">
                    <b style="color: black; font-size: 16px;">👑 AI 선정 바이럴 S-CLASS</b>
                </div>
            """, unsafe_allow_html=True)
            if st.button(f"{row['title']}", key=f"n_{i}", use_container_width=True):
                with st.spinner('AI 분석 중...'):
                    st.session_state.t, st.session_state.a = get_ai_analysis(row['link'])
                    st.session_state.title = row['title']
                    st.session_state.is_s = True
        else:
            # 일반 기사
            if st.button(f"[{row['rank']}] {row['title']}", key=f"n_{i}", use_container_width=True):
                with st.spinner('AI 분석 중...'):
                    st.session_state.t, st.session_state.a = get_ai_analysis(row['link'])
                    st.session_state.title = row['title']
                    st.session_state.is_s = False

with r:
    st.subheader("📄 뉴스 분석 및 원문")
    if 'title' in st.session_state:
        # AI 요약 및 키워드 섹션
        st.markdown("### 💡 AI 인사이트")
        st.success(st.session_state.a)
        
        st.divider()
        st.info(f"**원본 제목: {st.session_state.title}**")
        st.text_area("기사 전문 (복사용)", st.session_state.t, height=450)
    else:
        st.write("👈 왼쪽 리스트에서 노란색 카드가 붙은 S급 소재를 클릭해 보세요.")
