import streamlit as st
import requests
from bs4 import BeautifulSoup
import google.generativeai as genai

# 1. AI 엔진 설정 (404 에러 방지용 표준 모델명 사용)
try:
    genai.configure(api_key=st.secrets["GOOGLE_API_KEY"])
    # 가장 범용적인 gemini-1.5-flash 모델로 고정
    model = genai.GenerativeModel('gemini-1.5-flash')
except Exception as e:
    st.error(f"설정 에러: {e}")

st.set_page_config(page_title="VIRAL RANKING MASTER", layout="wide")

# --- 뉴스 수집 함수 ---
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

    # TOP 5 소재 선별
    try:
        titles_list = "\n".join([f"{i}. {d['title']}" for i, d in enumerate(unique_news[:40])])
        prompt = f"유튜브 조회수 대박날 소재 5개의 번호만 골라줘(쉼표 구분): {titles_list}"
        resp = model.generate_content(prompt)
        s_indices = [int(x.strip()) for x in resp.text.split(',') if x.strip().isdigit()]
    except:
        s_indices = [0, 1, 2, 3, 4]
    
    for i, item in enumerate(unique_news):
        item['is_s'] = i in s_indices
    return sorted(unique_news, key=lambda x: x['is_s'], reverse=True)

# --- [중요] AI 분석 함수 (에러 방지 강화) ---
def get_ai_analysis(url):
    try:
        res = requests.get(url, headers={"User-Agent": "Mozilla/5.0"})
        soup = BeautifulSoup(res.text, 'html.parser')
        # 네이버 뉴스 본문 태그들 정밀 타격
        content = soup.select_one('#newsct_article') or soup.select_one('#articleBodyContents') or soup.select_one('.article_body')
        
        if not content:
            return "본문을 수집할 수 없는 기사 형식입니다.", "분석 불가"
            
        text = content.text.strip()
        
        # AI에게 분석 요청 (모델명 재확인 불필요, 위에서 선언된 model 사용)
        analysis_prompt = f"""
        다음 뉴스 기사를 보고 유튜브 쇼츠/롱폼 제작을 위한 핵심 정보를 뽑아줘:
        1. 핵심 요약 (2줄 이내)
        2. 중요 키워드 5개 (중요도 순서대로)
        
        기사내용: {text[:1500]}
        """
        resp = model.generate_content(analysis_prompt)
        return text, resp.text
    except Exception as e:
        return f"데이터 수집 중 오류: {str(e)}", "AI 분석 도중 연결이 끊겼습니다."

# --- 메인 화면 구성 ---
st.title("🔥 VIRAL RANKING MASTER")
st.markdown("### 🚀 AI 선정 바이럴 S-CLASS 리스트")

l, r = st.columns([1, 1.2])

with l:
    if st.button("🔄 전체 랭킹 새로고침"):
        st.cache_data.clear()
        st.rerun()
    
    data = get_viral_top_100()
    
    for i, row in enumerate(data):
        if row['is_s']:
            # 뱃지 디자인 유지
            st.markdown(f"""
                <div style="background-color: #FFD700; padding: 5px 10px; border-radius: 5px; border: 2px solid #FF8C00; margin-bottom: -10px;">
                    <b style="color: black; font-size: 13px;">👑 AI S-CLASS 바이럴 추천</b>
                </div>
            """, unsafe_allow_html=True)
            if st.button(f"🔥 {row['title']}", key=f"s_{i}", use_container_width=True):
                with st.spinner('AI가 떡상 포인트를 분석 중입니다...'):
                    # 세션 상태에 저장하여 우측 화면 유지
                    full_text, analysis = get_ai_analysis(row['link'])
                    st.session_state.current_title = row['title']
                    st.session_state.current_full_text = full_text
                    st.session_state.current_analysis = analysis
            st.write("") # 간격 조절
        else:
            if st.button(f"[{i+1}] {row['title']}", key=f"n_{i}", use_container_width=True):
                with st.spinner('분석 중...'):
                    full_text, analysis = get_ai_analysis(row['link'])
                    st.session_state.current_title = row['title']
                    st.session_state.current_full_text = full_text
                    st.session_state.current_analysis = analysis

with r:
    st.subheader("📄 AI 인사이트 및 원문")
    if 'current_title' in st.session_state:
        # 1. AI 요약 & 키워드 노출
        st.markdown("#### 💡 AI 핵심 요약 & 키워드")
        st.success(st.session_state.current_analysis)
        
        st.divider()
        
        # 2. 원문 노출
        st.info(f"**원본 제목: {st.session_state.current_title}**")
        st.text_area("뉴스 전문 (복사용)", st.session_state.current_full_text, height=550)
    else:
        st.warning("👈 왼쪽 리스트에서 분석할 기사를 클릭해 주세요.")
