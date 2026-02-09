import streamlit as st
import requests
from bs4 import BeautifulSoup
import google.generativeai as genai
import json
import time
import re

# --- 1. AI 엔진 설정 (404 에러 방지용 다중 모델 시도) ---
@st.cache_resource
def load_ai_model():
    api_key = st.secrets.get("GOOGLE_API_KEY", "")
    if not api_key:
        st.error("⚠️ API 키가 설정되지 않았습니다. Streamlit Secrets를 확인하세요.")
        return None
    
    genai.configure(api_key=api_key)
    
    # 지원 가능한 모델 목록 (안정적인 순서대로)
    model_candidates = ['gemini-1.5-flash', 'gemini-1.5-pro', 'gemini-pro']
    
    for m_name in model_candidates:
        try:
            temp_model = genai.GenerativeModel(m_name)
            # 모델 작동 여부 테스트 (최소 토큰)
            temp_model.generate_content("ping", generation_config={"max_output_tokens": 1})
            return temp_model
        except Exception:
            continue
    return None

model = load_ai_model()

def call_gemini_optimized(prompt):
    if not model:
        return None
    try:
        response = model.generate_content(prompt)
        return response
    except Exception as e:
        st.error(f"❌ API 호출 오류: {e}")
        return None

# --- 2. 뉴스 데이터 수집 및 본문 추출 ---
@st.cache_data(ttl=600)
def fetch_news_data():
    url = "https://news.naver.com/main/ranking/popularDay.naver"
    headers = {"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"}
    try:
        res = requests.get(url, headers=headers, timeout=10)
        soup = BeautifulSoup(res.text, 'html.parser')
        items = []
        
        # 네이버 랭킹 뉴스 섹션 탐색
        for box in soup.select('.rankingnews_box'):
            press = box.select_one('strong.rankingnews_name').text.strip() if box.select_one('strong.rankingnews_name') else "언론사"
            for li in box.select('.rankingnews_list li'):
                a_tag = li.select_one('a')
                title_tag = li.select_one('.list_title')
                if a_tag and title_tag:
                    items.append({
                        "title": title_tag.text.strip(),
                        "link": a_tag['href'],
                        "press": press
                    })
        return items[:40] # 상위 40개 수집
    except Exception as e:
        st.error(f"뉴스 수집 실패: {e}")
        return []

def get_content(url):
    headers = {"User-Agent": "Mozilla/5.0"}
    try:
        res = requests.get(url, headers=headers, timeout=5)
        soup = BeautifulSoup(res.text, 'html.parser')
        # 네이버 뉴스 본문 선택자 (여러 버전 대응)
        area = soup.select_one('#dic_area') or soup.select_one('#newsct_article') or soup.select_one('#articleBodyContents')
        return area.get_text(strip=True) if area else "기사 본문을 추출할 수 없습니다."
    except:
        return "본문 수집 중 오류가 발생했습니다."

# --- 3. Streamlit UI 설정 ---
st.set_page_config(page_title="VIRAL MASTER PRO v2.6", layout="wide")

st.markdown("""
    <style>
    div.stButton > button {
        text-align: left !important;
        border-radius: 8px !important;
        padding: 10px !important;
        width: 100%;
        transition: 0.3s;
    }
    div.stButton > button:hover {
        border-color: #ff4b4b !important;
        color: #ff4b4b !important;
    }
    .s-class-btn {
        background-color: #fff9e6 !important;
        border: 2px solid #FFD700 !important;
        font-weight: bold !important;
    }
    </style>
""", unsafe_allow_html=True)

st.title("👑 VIRAL MASTER PRO v2.6")

# 세션 상태 초기화
if "s_indices" not in st.session_state:
    st.session_state.s_indices = []
if "current_view" not in st.session_state:
    st.session_state.current_view = None

tab1, tab2 = st.tabs(["🔥 뉴스 이슈 분석", "🎯 초격차 원고 빌더"])

# --- Tab 1: 뉴스 이슈 분석 ---
with tab1:
    news_list = fetch_news_data()
    
    if news_list:
        # S급 선별 로직
        if not st.session_state.s_indices and model:
            with st.spinner("🚀 AI가 100만뷰 황금 소재를 선별 중..."):
                titles_str = "\n".join([f"{i}:{n['title']}" for i, n in enumerate(news_list)])
                prompt = f"""다음 뉴스 목록 중 유튜브 '국뽕/기술력/충격/폭로' 소재로 적합한 5개를 골라줘.
                형식은 반드시 숫자만 있는 JSON 리스트로만 답해. 예: [0, 3, 5, 10, 12]
                목록:
                {titles_str}"""
                resp = call_gemini_optimized(prompt)
                if resp:
                    try:
                        # 정규식으로 숫자만 추출하여 안전하게 로드
                        nums = re.findall(r'\d+', resp.text)
                        st.session_state.s_indices = [int(n) for n in nums if int(n) < len(news_list)]
                    except:
                        st.session_state.s_indices = []

        col1, col2 = st.columns([1, 1.2])

        with col1:
            st.subheader("📰 실시간 이슈 랭킹")
            if st.button("🔄 리스트 새로고침"):
                st.cache_data.clear()
                st.session_state.s_indices = []
                st.session_state.current_view = None
                st.rerun()

            for i, item in enumerate(news_list):
                is_s = i in st.session_state.s_indices
                label = f"🏆 [S급 황금] {item['title']}" if is_s else f"[{i+1}] {item['title']}"
                
                if st.button(label, key=f"btn_{i}"):
                    with st.spinner("⚡ 기사 심층 분석 중..."):
                        txt = get_content(item['link'])
                        ana_prompt = f"이 기사를 기반으로 '자극적인 썸네일 문구 3개'와 '내용 1줄 요약'을 작성해줘:\n{txt[:1000]}"
                        ana_resp = call_gemini_optimized(ana_prompt)
                        st.session_state.current_view = {
                            "title": item['title'],
                            "press": item['press'],
                            "link": item['link'],
                            "content": txt,
                            "analysis": ana_resp.text if ana_resp else "분석 실패 (API 한도 초과 등)",
                            "is_s": is_s
                        }

        with col2:
            if st.session_state.current_view:
                v = st.session_state.current_view
                st.markdown(f"### {'🔥 S급 황금소재 전략' if v['is_s'] else '📊 일반 뉴스 분석'}")
                st.success(f"**[{v['press']}]** {v['title']}")
                
                with st.expander("🎯 AI 썸네일 & 요약 전략", expanded=True):
                    st.write(v['analysis'])
                
                st.link_button("🔗 네이버 뉴스 원문 보기", v['link'])
                
                st.subheader("📄 기사 데이터 (원고용)")
                st.text_area("본문 내용", v['content'], height=350)
            else:
                st.info("왼쪽에서 분석할 뉴스를 선택해 주세요.")

# --- Tab 2: 원고 빌더 ---
with tab2:
    st.header("🎯 초격차 원고 빌더")
    st.caption("클로드 프로젝트에 입력할 프롬프트를 생성합니다.")
    
    col_a, col_b = st.columns(2)
    with col_a:
        v_title = st.text_input("💎 영상 메인 제목", value=st.session_state.current_view['title'] if st.session_state.current_view else "")
        v_fact = st.text_area("📰 핵심 팩트 및 뉴스 내용", value=st.session_state.current_view['content'] if st.session_state.current_view else "", height=200)
    with col_b:
        v_target = st.text_input("📺 참고 벤치마킹 URL (이슈서치 등)")
        v_vibe = st.text_area("💬 시청자 민심 (댓글 반응 등)", placeholder="예: 우리나라 기술력 대단하다, 일본은 이제 끝났다 등", height=200)

    if st.button("🚀 클로드 전용 초격차 프롬프트 생성"):
        if v_title and v_fact:
            final_p = f"""# 데이터 기반 대본 작성 요청
            제목: {v_title}
            팩트자료: {v_fact[:2000]}
            벤치마킹: {v_target}
            민심(댓글): {v_vibe}
            
            위 데이터를 바탕으로 설정된 '100만 바이럴 유튜브 콘텐츠 공정 엔진' 지침에 따라 8분 분량의 초격차 대본을 작성하라."""
            
            st.code(final_p, language="markdown")
            st.success("위 내용을 복사하여 클로드 프로젝트 대화창에 붙여넣으세요!")
        else:
            st.warning("제목과 팩트 내용은 필수입니다.")
