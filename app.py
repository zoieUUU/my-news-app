import streamlit as st
import requests
from bs4 import BeautifulSoup
import google.generativeai as genai
import json
import time
import re

# 1. AI 엔진 설정 (모델명 확인 필수: gemini-1.5-flash 권장)
@st.cache_resource
def load_ai_model():
    try:
        # gemini-2.5는 아직 공식 출시 전일 수 있으므로 안정적인 1.5-flash 혹은 pro 권장
        model_name = 'gemini-1.5-flash' 
        api_key = st.secrets.get("GOOGLE_API_KEY", "")
        if api_key:
            genai.configure(api_key=api_key)
            return genai.GenerativeModel(model_name)
        return None
    except Exception as e:
        st.error(f"AI 모델 초기화 실패: {e}")
        return None

model = load_ai_model()

def call_gemini_optimized(prompt):
    if not model: return None
    try:
        response = model.generate_content(prompt)
        return response
    except Exception as e:
        st.error(f"API 호출 오류: {e}")
        return None

# --- 뉴스 수집 함수 (네이버 랭킹 뉴스 구조 대응) ---
@st.cache_data(ttl=600)
def fetch_news_data():
    url = "https://news.naver.com/main/ranking/popularDay.naver"
    try:
        res = requests.get(url, headers={"User-Agent": "Mozilla/5.0"}, timeout=10)
        soup = BeautifulSoup(res.text, 'html.parser')
        items = []
        # 네이버 랭킹 뉴스 페이지 구조에 맞게 선택자 수정
        for box in soup.select('.rankingnews_box'):
            press_name = box.select_one('strong').text.strip() if box.select_one('strong') else "언론사"
            for li in box.select('.rankingnews_list li'):
                a = li.select_one('a')
                title = li.select_one('.list_title')
                if a and title:
                    items.append({
                        "title": title.text.strip(),
                        "link": a['href'],
                        "press": press_name
                    })
        return items[:40] # 분석을 위해 40개 정도 수집
    except Exception as e:
        st.error(f"뉴스 수집 실패: {e}")
        return []

def get_content(url):
    try:
        res = requests.get(url, headers={"User-Agent": "Mozilla/5.0"}, timeout=5)
        soup = BeautifulSoup(res.text, 'html.parser')
        # 기사 본문 영역 선택자 보강
        area = soup.select_one('#dic_area') or soup.select_one('#newsct_article') or soup.select_one('#articleBodyContents')
        return area.get_text(strip=True) if area else "본문을 찾을 수 없습니다."
    except:
        return "본문 수집 중 오류 발생"

# --- UI 설정 ---
st.set_page_config(page_title="VIRAL MASTER PRO v2.6", layout="wide")

# 메인 로직 시작
st.title("👑 VIRAL MASTER PRO v2.6")

if "s_indices" not in st.session_state:
    st.session_state.s_indices = []

tab1, tab2 = st.tabs(["🔥 뉴스 이슈", "🎯 원고 빌더"])

with tab1:
    news_list = fetch_news_data()
    
    if news_list:
        # S급 선별 로직 (최초 1회 실행)
        if not st.session_state.s_indices:
            with st.spinner("🚀 AI가 S급 황금 소재를 선별 중입니다..."):
                titles_context = "\n".join([f"{i}:{n['title']}" for i, n in enumerate(news_list)])
                prompt = f"""다음 뉴스 제목 중 유튜브에서 '조회수 100만'이 터질법한 국뽕, 기술력, 반전, 충격 소재 5개를 골라줘.
                답변은 반드시 딱 숫자만 포함된 JSON 리스트 형식으로 해줘. 예: [1, 5, 12, 18, 20]
                뉴스트리:\n{titles_context}"""
                
                resp = call_gemini_optimized(prompt)
                if resp:
                    try:
                        # 정규식으로 숫자 리스트 추출 보강
                        nums = re.findall(r'\d+', resp.text)
                        st.session_state.s_indices = [int(n) for n in nums if int(n) < len(news_list)]
                    except:
                        st.session_state.s_indices = []

        col1, col2 = st.columns([1, 1])

        with col1:
            st.subheader("📰 실시간 랭킹 뉴스")
            if st.button("🔄 데이터 새로고침"):
                st.cache_data.clear()
                st.session_state.s_indices = []
                st.rerun()

            for i, item in enumerate(news_list):
                is_s = i in st.session_state.s_indices
                # S급은 노란색 버튼과 왕관 아이콘으로 강조
                btn_label = f"🏆 [S급 황금] {item['title']}" if is_s else f"[{i+1}] {item['title']}"
                
                if st.button(btn_label, key=f"news_btn_{i}", use_container_width=True):
                    with st.spinner("⚡ 기사 분석 및 썸네일 전략 수립 중..."):
                        content = get_content(item['link'])
                        analysis_prompt = f"""이 기사를 분석해서 다음을 출력해줘:
                        1. 유튜브 썸네일 카피 3개 (자극적이고 클릭하고 싶게)
                        2. 핵심 내용 1줄 요약
                        기사내용: {content[:1000]}"""
                        
                        ana_resp = call_gemini_optimized(analysis_prompt)
                        st.session_state.current_view = {
                            "title": item['title'],
                            "link": item['link'],
                            "content": content,
                            "analysis": ana_resp.text if ana_resp else "AI 분석 실패",
                            "is_s": is_s
                        }

        with col2:
            if "current_view" in st.session_state:
                v = st.session_state.current_view
                st.markdown(f"### {'🔥 S급 황금소재 분석' if v['is_s'] else '📊 일반소재 분석'}")
                st.info(v['analysis'])
                
                # 기사 원문 보기 버튼 추가
                st.link_button("🔗 네이버 뉴스 원문 보기", v['link'])
                
                st.subheader("📝 기사 본문 추출")
                st.text_area("본문 내용 (복사 가능)", v['content'], height=400)
            else:
                st.info("왼쪽 뉴스 리스트에서 분석할 기사를 선택하세요.")

# (Tab2 원고 빌더 로직은 기존과 동일하되 위 지침을 복사할 수 있는 기능을 유지하면 됩니다.)
