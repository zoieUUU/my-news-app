import streamlit as st
import requests
from bs4 import BeautifulSoup
import google.generativeai as genai

# 1. AI 엔진 설정 (404 에러 방지를 위한 최후의 수단)
try:
    genai.configure(api_key=st.secrets["GOOGLE_API_KEY"])
    # 경로 문제를 방지하기 위해 models/ 를 포함한 전체 경로를 명시적으로 작성
    model = genai.GenerativeModel('models/gemini-1.5-flash')
except Exception as e:
    st.error(f"API 설정 오류: {e}")

st.set_page_config(page_title="VIRAL RANKING MASTER", layout="wide")

# --- 뉴스 수집 함수 (차단 방지 로직 강화) ---
@st.cache_data(ttl=600)
def get_viral_top_100():
    url = "https://news.naver.com/main/ranking/popularDay.naver"
    headers = {
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"
    }
    try:
        res = requests.get(url, headers=headers, timeout=10)
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
        
        # S급 소재 선별 (상위 40개 분석)
        titles_chunk = "\n".join([f"{i}. {d['title']}" for i, d in enumerate(unique_news[:40])])
        prompt = f"다음 뉴스 중 유튜브 조회수가 터질 S급 소재 5개의 번호만 골라줘: {titles_chunk}"
        resp = model.generate_content(prompt)
        # 응답에서 숫자만 추출하는 안전한 로직
        import re
        s_indices = [int(n) for n in re.findall(r'\d+', resp.text)]
    except:
        s_indices = [0, 1, 2, 3, 4]
    
    for i, item in enumerate(unique_news):
        item['is_s'] = i in s_indices
    return sorted(unique_news, key=lambda x: x['is_s'], reverse=True)

# --- AI 분석 함수 (네이버 차단 우회 및 404 에러 방지) ---
def get_ai_analysis(url):
    try:
        headers = {
            "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
            "Referer": "https://news.naver.com/"
        }
        res = requests.get(url, headers=headers, timeout=10)
        soup = BeautifulSoup(res.text, 'html.parser')
        
        # 네이버 뉴스 본문 수집 태그 (최신순)
        content = soup.select_one('#dic_area') or soup.select_one('#newsct_article') or soup.select_one('#articleBodyContents')
        
        if not content:
            return "기사 본문을 찾을 수 없습니다.", "분석 불가"
            
        text = content.get_text(strip=True)
        # AI 분석 요청 (핵심 요약 및 키워드)
        analysis_prompt = f"다음 뉴스를 분석해서 [요약 2줄]과 [핵심 키워드 5개]를 출력해:\n\n{text[:1800]}"
        resp = model.generate_content(analysis_prompt)
        return text, resp.text
    except Exception as e:
        # 에러 메시지를 사용자 친화적으로 출력
        return f"연결 실패: {str(e)}", f"에러가 발생했습니다. (모델 호출 또는 네트워크 문제)"

# --- UI 구성 ---
st.title("🔥 VIRAL RANKING MASTER")

left_col, right_col = st.columns([1, 1.2])

with left_col:
    if st.button("🔄 리스트 새로고침"):
        st.cache_data.clear()
        st.rerun()
    
    data = get_viral_top_100()
    for i, item in enumerate(data):
        if item['is_s']:
            # S급 강조 디자인
            st.markdown(f'<div style="background-color:#FFD700; padding:4px 8px; border-radius:4px; border:2px solid #FFA500; font-weight:bold; color:black; font-size:12px; margin-bottom:-10px; width:fit-content;">👑 AI S-CLASS</div>', unsafe_allow_html=True)
            if st.button(f"🔥 {item['title']}", key=f"s_{i}", use_container_width=True):
                with st.spinner('AI 분석 중...'):
                    t, a = get_ai_analysis(item['link'])
                    st.session_state.result = {"title": item['title'], "text": t, "analysis": a}
        else:
            if st.button(f"[{i+1}] {item['title']}", key=f"n_{i}", use_container_width=True):
                with st.spinner('분석 중...'):
                    t, a = get_ai_analysis(item['link'])
                    st.session_state.result = {"title": item['title'], "text": t, "analysis": a}

with right_col:
    st.subheader("📊 AI 소재 분석 리포트")
    if "result" in st.session_state:
        # AI 요약 및 키워드 출력
        st.success(f"**💡 AI 인사이트**\n\n{st.session_state.result['analysis']}")
        st.divider()
        st.info(f"**제목: {st.session_state.result['title']}**")
        st.text_area("기사 전문", st.session_state.result['text'], height=550)
    else:
        st.info("👈 왼쪽 리스트에서 분석할 기사를 클릭해 주세요.")
