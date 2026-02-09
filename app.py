import streamlit as st
import requests
from bs4 import BeautifulSoup
import google.generativeai as genai
import PIL.Image
import io
import json
import time
import re

# 1. AI 엔진 설정 - 모델명 오류 및 에러 수정
@st.cache_resource
def load_ai_model():
    try:
        if "GOOGLE_API_KEY" in st.secrets:
            genai.configure(api_key=st.secrets["GOOGLE_API_KEY"])
            # 가장 범용적이고 안정적인 모델명 사용
            return genai.GenerativeModel('gemini-1.5-flash')
        else:
            st.error("API 키가 설정되지 않았습니다. Secrets를 확인해주세요.")
            return None
    except Exception as e:
        st.error(f"AI 모델 로드 중 오류가 발생했습니다: {e}")
        return None

model = load_ai_model()

st.set_page_config(page_title="VIRAL MASTER PRO v2.6", layout="wide")

# --- UI 스타일 (뉴스 리스트 통합 강조 및 레이아웃 복구) ---
st.markdown("""
    <style>
    .main { background-color: #f8f9fa; }
    
    /* S급 뱃지 스타일 */
    .s-badge {
        background-color: #FFD700;
        color: #000000;
        font-weight: bold;
        padding: 2px 8px;
        border-radius: 4px;
        margin-right: 8px;
        font-size: 0.8em;
        box-shadow: 0 2px 4px rgba(255, 215, 0, 0.4);
    }
    
    /* 리스트 버튼 스타일 */
    div.stButton > button {
        text-align: left !important;
        justify-content: flex-start !important;
        border-radius: 8px !important;
        background-color: white !important;
        border: 1px solid #e0e0e0 !important;
        padding: 10px 15px !important;
        transition: all 0.2s;
    }
    
    div.stButton > button:hover {
        border-color: #FFD700 !important;
        background-color: #fffdf0 !important;
    }

    /* S급 버튼 특수 배경 */
    .s-item-active {
        background-color: #fff9e6 !important;
        border: 1px solid #FFD700 !important;
    }
    
    .stTextArea textarea {
        background-color: #ffffff !important;
        border: 1px solid #ddd !important;
    }
    </style>
""", unsafe_allow_html=True)

# --- 유틸리티 함수 ---
def get_content_safe(url):
    headers = {"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"}
    try:
        res = requests.get(url, headers=headers, timeout=5)
        soup = BeautifulSoup(res.text, 'html.parser')
        # 선택자 다양화 (실패 방지)
        content = soup.select_one('#dic_area') or soup.select_one('#newsct_article') or soup.select_one('.article_body') or soup.select_one('article')
        if content:
            return content.get_text(strip=True)
        return "본문 수집에 실패했습니다. (URL 직접 확인 권장)"
    except Exception as e:
        return f"데이터 수집 에러: {e}"

@st.cache_data(ttl=300)
def fetch_news():
    url = "https://news.naver.com/main/ranking/popularDay.naver"
    headers = {"User-Agent": "Mozilla/5.0"}
    try:
        res = requests.get(url, headers=headers)
        soup = BeautifulSoup(res.text, 'html.parser')
        news_list = []
        for box in soup.select('.rankingnews_box'):
            for li in box.select('.rankingnews_list li'):
                a = li.select_one('a')
                if a and a.text.strip():
                    news_list.append({"title": a.text.strip(), "link": a['href']})
        return news_list[:50] # 상위 50개만
    except:
        return []

def get_s_class_indices(news_data):
    if not model or not news_data: return []
    titles = [f"{i}: {n['title']}" for i, n in enumerate(news_data)]
    prompt = f"""
    당신은 대한민국 최고의 유튜브 전략가입니다.
    다음 뉴스 리스트 중 [국뽕, 방산, 반도체, 외신반응, 삼성, 일본비교] 테마로 떡상할 소재 5개의 번호만 리스트 형식으로 보내세요.
    예: [1, 3, 10, 15, 22]
    뉴스:
    {chr(10).join(titles)}
    """
    try:
        response = model.generate_content(prompt)
        match = re.search(r"\[.*\]", response.text)
        if match:
            return json.loads(match.group())
        return []
    except Exception as e:
        print(f"AI 선별 에러: {e}")
        return []

# --- 메인 화면 구성 ---
st.title("👑 VIRAL MASTER PRO v2.6")
st.caption("AI 기반 실시간 뉴스 트렌드 분석 및 초격차 대본 빌더")

tab1, tab2 = st.tabs(["🔥 실시간 뉴스 리스트", "🎯 대본 마스터 빌더"])

with tab1:
    news_items = fetch_news()
    
    if news_items:
        # S급 인덱스 추출 (세션 상태 저장)
        if "s_idx" not in st.session_state:
            with st.spinner('💎 AI가 S급 황금 소재를 판별하고 있습니다...'):
                st.session_state.s_idx = get_s_class_indices(news_items)
        
        s_idx = st.session_state.s_idx
        
        col1, col2 = st.columns([1.2, 1])
        
        with col1:
            st.subheader("📰 실시간 인기 뉴스 (S급 자동 표시)")
            if st.button("🔄 리스트 & AI 알고리즘 갱신"):
                st.cache_data.clear()
                if "s_idx" in st.session_state: del st.session_state.s_idx
                st.rerun()
            
            # 리스트 렌더링
            for i, item in enumerate(news_items):
                is_s_class = i in s_idx
                label = f"[{i+1}] {item['title']}"
                if is_s_class:
                    # 텍스트 앞에 S급 표시
                    btn_label = f"🏆 [S급] {item['title']}"
                else:
                    btn_label = label
                
                if st.button(btn_label, key=f"news_{i}", use_container_width=True):
                    with st.spinner('🚀 소재 심층 분석 및 팩트 추출 중...'):
                        content = get_content_safe(item['link'])
                        if model:
                            try:
                                analysis_prompt = f"""
                                다음 기사를 분석하여 유튜브 제작 전략을 짜줘:
                                기사: {content[:2000]}
                                
                                1. 썸네일 카피(어그로 강) 3개
                                2. 시청자 열광 포인트 3가지
                                3. 핵심 요약
                                """
                                analysis = model.generate_content(analysis_prompt).text
                            except:
                                analysis = "AI 분석 일시적 오류. 기사 데이터를 직접 확인하세요."
                        else:
                            analysis = "AI 모델이 로드되지 않았습니다."
                            
                        st.session_state.current_news = {
                            "title": item['title'],
                            "content": content,
                            "analysis": analysis,
                            "is_s": is_s_class
                        }

        with col2:
            if "current_news" in st.session_state:
                res = st.session_state.current_news
                title_prefix = "🏆 [S급 전략 분석]" if res['is_s'] else "📊 [일반 소재 분석]"
                st.markdown(f"### {title_prefix}\n**{res['title']}**")
                
                with st.expander("✨ AI 추천 전략 (클릭하여 열기)", expanded=True):
                    st.write(res['analysis'])
                
                st.divider()
                st.markdown("📝 **클로드 입력용 기사 데이터**")
                st.text_area("기본 데이터 (복사 가능)", res['content'], height=450)
            else:
                st.info("왼쪽 뉴스 리스트에서 분석할 소재를 선택하세요.")

with tab2:
    st.header("🎯 초격차 원고 제작 프로젝트")
    
    st.markdown("### 1️⃣ 캡처본 업로드 (네이버/더구루 등)")
    caps = st.file_uploader("이미지 파일을 올리면 소재를 추출합니다.", accept_multiple_files=True)
    if caps and st.button("🔍 이미지 분석 시작"):
        if model:
            with st.spinner("비전 AI 가동 중..."):
                try:
                    imgs = [PIL.Image.open(c) for c in caps]
                    v_res = model.generate_content(["이 이미지들에서 유튜브 대박 소재를 찾고 썸네일 전략을 세워줘.", *imgs]).text
                    st.success(v_res)
                except Exception as e:
                    st.error(f"이미지 분석 실패: {e}")
        else:
            st.error("AI 모델이 로드되지 않았습니다.")

    st.divider()
    
    st.markdown("### 2️⃣ 데이터 최종 입력 & 프롬프트 생성")
    c1, c2 = st.columns(2)
    with c1:
        f_title = st.text_input("💎 확정 소재 제목")
        f_news = st.text_area("📰 뉴스 기사 본문 합치기", height=300)
    with c2:
        f_yt = st.text_input("📺 벤치마킹 유튜브 URL")
        f_comm = st.text_area("💬 시청자 반응 데이터", height=250)
        if st.button("🔗 유튜브 민심 자동 생성"):
            if model and f_yt:
                with st.spinner('분석 중...'):
                    inf = model.generate_content(f"이 영상 주제와 관련된 한국 시청자들의 열광적인 댓글 5개를 가상으로 만들어줘.").text
                    st.info(inf)

    if st.button("🔥 클로드 전용 마스터 프롬프트 생성", use_container_width=True):
        if not f_title or not f_news:
            st.warning("제목과 본문을 입력해주세요.")
        else:
            prompt = f"""
당신은 유튜브 메인 작가입니다. 아래 데이터를 바탕으로 8분 분량의 '국뽕/이슈' 대본을 작성하세요.
- 주제: {f_title}
- 팩트: {f_news}
- 벤치마킹: {f_yt}
- 여론: {f_comm}

[지침]
1. 오프닝에서 "지금 전 세계가 발칵 뒤집혔습니다" 류의 강력한 후킹 사용.
2. 반전 구조(비난하던 외신이 찬사로 바뀌는 등) 필수 포함.
3. 5,000자 이상의 상세한 완성형 대본으로 출력할 것.
            """
            st.code(prompt, language="markdown")
            st.success("위 내용을 클로드에 붙여넣으세요!")
