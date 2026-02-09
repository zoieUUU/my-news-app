import streamlit as st
import requests
from bs4 import BeautifulSoup
import google.generativeai as genai
import PIL.Image
import io
import json
import time
import re

# 1. AI 엔진 설정 - 가장 안정적인 모델명으로 고정 및 에러 제어
@st.cache_resource
def load_ai_model():
    try:
        if "GOOGLE_API_KEY" in st.secrets:
            genai.configure(api_key=st.secrets["GOOGLE_API_KEY"])
            # 가끔 발생하는 NotFound 에러 방지를 위해 최신 안정화 모델명 사용
            return genai.GenerativeModel('gemini-1.5-flash-latest')
        else:
            st.error("API 키가 설정되지 않았습니다. Secrets를 확인해주세요.")
            return None
    except Exception as e:
        st.error(f"AI 모델 로드 오류: {e}")
        return None

model = load_ai_model()

st.set_page_config(page_title="VIRAL MASTER PRO v2.6", layout="wide")

# --- UI 스타일 커스터마이징 (S급 표시 강화) ---
st.markdown("""
    <style>
    .main { background-color: #f9f9fb; }
    
    /* 뉴스 리스트 버튼 스타일 */
    div.stButton > button {
        text-align: left !important;
        justify-content: flex-start !important;
        border-radius: 12px !important;
        background-color: #ffffff !important;
        border: 1px solid #eaeaea !important;
        padding: 12px 18px !important;
        margin-bottom: 5px;
        transition: all 0.3s ease;
        font-size: 16px !important;
    }
    
    div.stButton > button:hover {
        border-color: #FFD700 !important;
        background-color: #fffef0 !important;
        transform: translateX(5px);
    }

    /* S급 전용 버튼 강조 스타일 */
    .s-class-btn {
        border: 2px solid #FFD700 !important;
        background-color: #fff9e6 !important;
        font-weight: 800 !important;
        color: #b8860b !important;
    }
    
    /* 분석창 텍스트 박스 */
    .stTextArea textarea {
        background-color: #ffffff !important;
        border: 1px solid #ddd !important;
        border-radius: 10px;
    }
    </style>
""", unsafe_allow_html=True)

# --- 뉴스 수집 및 파싱 로직 ---
def get_content_safe(url):
    headers = {"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/121.0.0.0 Safari/537.36"}
    try:
        res = requests.get(url, headers=headers, timeout=10)
        soup = BeautifulSoup(res.text, 'html.parser')
        # 네이버 뉴스 본문 추출 (다양한 클래스 대응)
        content = soup.select_one('#dic_area') or soup.select_one('#newsct_article') or soup.select_one('.article_body') or soup.select_one('article')
        if content:
            # 불필요한 태그 제거
            for s in content(['script', 'style', 'header', 'footer']): s.decompose()
            return content.get_text(separator="\n", strip=True)
        return "본문 내용을 찾을 수 없습니다. 뉴스 페이지의 구조가 변경되었을 수 있습니다."
    except Exception as e:
        return f"데이터 로딩 중 오류 발생: {e}"

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
        return news_list[:60]
    except Exception:
        return []

def get_s_class_indices(news_data):
    if not model or not news_data: return []
    titles_combined = "\n".join([f"{i}: {n['title']}" for i, n in enumerate(news_data)])
    prompt = f"""
    당신은 100만 유튜버 기획자입니다. 
    다음 뉴스 리스트 중에서 [국뽕, 방산, 반도체, 외신극찬, 삼성, 일본반응] 키워드에 부합하며 
    유튜브 영상 제작 시 조회수가 폭발할 소재 5개의 번호만 리스트 형식으로 답변하세요.
    예: [2, 5, 12, 18, 24]
    뉴스 리스트:
    {titles_combined}
    """
    try:
        response = model.generate_content(prompt)
        match = re.search(r"\[.*\]", response.text)
        if match:
            return json.loads(match.group())
        return []
    except Exception:
        return []

# --- 메인 대시보드 ---
st.title("👑 VIRAL MASTER PRO v2.6")
st.caption("실시간 뉴스 트렌드 분석 & AI 기반 초격차 원고 제작 엔진")

tab1, tab2 = st.tabs(["🔥 뉴스 리스트 탐색", "🎯 대본 마스터 빌더"])

with tab1:
    news_items = fetch_news()
    
    if news_items:
        # S급 인덱스 관리
        if "s_idx" not in st.session_state:
            with st.spinner('🚀 AI가 실시간으로 황금 소재를 선별 중입니다...'):
                st.session_state.s_idx = get_s_class_indices(news_items)
        
        s_idx = st.session_state.s_idx
        
        col1, col2 = st.columns([1.2, 1])
        
        with col1:
            st.subheader("📰 실시간 랭킹 (S급 자동 선별)")
            if st.button("🔄 리스트 새로고침 & AI 재분석"):
                st.cache_data.clear()
                if "s_idx" in st.session_state: del st.session_state.s_idx
                st.rerun()
            
            # 리스트 출력
            for i, item in enumerate(news_items):
                is_s = i in s_idx
                # S급이면 버튼 텍스트에 왕관과 뱃지 추가
                btn_label = f"🏆 [S급 소재] {item['title']}" if is_s else f"[{i+1}] {item['title']}"
                
                # 버튼 클릭 시 분석 로직
                if st.button(btn_label, key=f"news_btn_{i}", use_container_width=True):
                    with st.spinner('분석 중...'):
                        content = get_content_safe(item['link'])
                        if model:
                            try:
                                analysis_res = model.generate_content(f"""
                                다음 기사를 바탕으로 유튜브 떡상 전략을 세워줘:
                                1. 썸네일 카피 3개 (자극적이고 궁금하게)
                                2. 시청자가 열광할 핵심 포인트 3가지
                                3. 영상 스토리라인 요약
                                
                                기사 본문: {content[:2000]}
                                """).text
                            except Exception:
                                analysis_res = "AI 분석 서버 응답 오류. 다시 시도하거나 기사 데이터를 직접 확인하세요."
                        else:
                            analysis_res = "AI 모델이 정상적으로 로드되지 않았습니다."
                            
                        st.session_state.current_analysis = {
                            "title": item['title'],
                            "content": content,
                            "analysis": analysis_res,
                            "is_s": is_s
                        }

        with col2:
            if "current_analysis" in st.session_state:
                res = st.session_state.current_analysis
                header_text = "✨ [S급 황금 소재 분석 결과]" if res['is_s'] else "📊 [일반 소재 분석 결과]"
                st.markdown(f"### {header_text}")
                st.info(f"**대상 기사**: {res['title']}")
                
                with st.expander("📝 AI 추천 제작 전략", expanded=True):
                    st.write(res['analysis'])
                
                st.divider()
                st.markdown("📄 **기사 원문 데이터 (클로드/GPT 복사용)**")
                st.text_area("Full Content", res['content'], height=450)
            else:
                st.info("왼쪽 리스트에서 소재를 선택하면 100만 조회수 전략이 이곳에 표시됩니다.")

with tab2:
    st.header("🎯 초격차 원고 제작 프로젝트")
    
    st.markdown("### 1️⃣ 타 채널/커뮤니티 캡처본 분석 (Ctrl+V 지원)")
    caps = st.file_uploader("네이버, 더구루, 유튜브 커뮤니티 등의 캡처 이미지를 업로드하세요.", accept_multiple_files=True)
    if caps and st.button("🔍 비전 AI 분석 시작"):
        if model:
            with st.spinner("이미지 속 텍스트와 맥락 분석 중..."):
                try:
                    imgs = [PIL.Image.open(c) for c in caps]
                    vision_res = model.generate_content(["이 이미지들에서 다루는 주요 이슈를 파악하고, 유튜브로 제작했을 때 가장 잘 먹힐 썸네일 카피를 제안해줘.", *imgs]).text
                    st.success(vision_res)
                except Exception as e:
                    st.error(f"이미지 분석 중 오류: {e}")
        else:
            st.error("AI 엔진을 사용할 수 없습니다.")

    st.divider()
    
    st.markdown("### 2️⃣ 데이터 최종 취합 & 마스터 프롬프트 생성")
    left_in, right_in = st.columns(2)
    with left_in:
        final_title = st.text_input("💎 확정 소재 제목", placeholder="분석된 제목을 입력하세요.")
        final_news = st.text_area("📰 뉴스 기사 본문들 (여러 개 합치기)", height=300, placeholder="여러 뉴스 기사를 여기에 한꺼번에 붙여넣으세요.")
    with right_in:
        final_yt = st.text_input("📺 벤치마킹 유튜브 영상 주소", placeholder="참고할 영상 URL")
        final_comm = st.text_area("💬 실시간 시청자 반응 (댓글/여론)", height=250, placeholder="댓글창 내용을 긁어오거나 직접 입력하세요.")
        if st.button("🔗 유튜브 민심 데이터 자동 추론"):
            if model and final_yt:
                with st.spinner('민심 분석 중...'):
                    inf_comm = model.generate_content(f"이 주제({final_title})와 관련하여 한국인들이 가장 열광하거나 분노할 만한 예상 댓글 5개를 작성해줘.").text
                    st.info(inf_comm)

    if st.button("🔥 클로드 전용 초격차 프롬프트 생성", use_container_width=True):
        if not final_title or not final_news:
            st.warning("제목과 뉴스 본문 데이터는 필수입니다.")
        else:
            master_prompt = f"""
# 지시사항: 100만 조회수 보증 '초격차 유튜브 원고' 집필

## [입력 데이터]
- 확정 주제: {final_title}
- 팩트 데이터: {final_news}
- 벤치마킹 타겟: {final_yt}
- 시청자 여론: {final_comm}

## [작가 지침]
1. 당신은 대한민국 최고 이슈 채널의 메인 작가입니다.
2. 기사 본문의 팩트를 기반으로 하되, 서사는 '국뽕'과 '카타르시스'를 극대화하십시오.
3. [전율], [경악], [감동] 등의 감정 태그를 문장 앞에 적절히 섞으십시오.
4. 오프닝 30초 내에 시청자를 붙잡을 수 있는 강렬한 멘트를 작성하십시오.
5. 최소 5,000자 이상의 완성형 대본으로 출력하십시오.

지금 바로 집필을 시작하십시오.
            """
            st.markdown("### 📋 클로드(Claude)에 아래 내용을 복사해서 붙여넣으세요")
            st.code(master_prompt, language="markdown")
            st.success("프롬프트가 생성되었습니다.")
