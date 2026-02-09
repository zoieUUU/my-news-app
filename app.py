import streamlit as st
import requests
from bs4 import BeautifulSoup
import google.generativeai as genai
import PIL.Image
import io
import json

# 1. AI 엔진 설정 (Gemini 1.5 Flash - 비전 및 텍스트 분석 통합)
@st.cache_resource
def load_ai_model():
    try:
        genai.configure(api_key=st.secrets["GOOGLE_API_KEY"])
        return genai.GenerativeModel('models/gemini-1.5-flash')
    except Exception as e:
        st.error(f"AI 모델 로드 실패: {e}")
        return None

model = load_ai_model()

st.set_page_config(page_title="VIRAL MASTER PRO v2.6", layout="wide")

# --- CSS 스타일링 (오류 방지를 위해 안정적인 구조로 재설계) ---
st.markdown("""
    <style>
    /* S급 버튼 강조 스타일 */
    .s-class-container {
        background-color: #FFD700 !important;
        border-radius: 10px;
        padding: 5px;
        margin-bottom: 5px;
        border: 2px solid #FFA500;
    }
    
    /* 버튼 둥글게 및 호버 효과 */
    div[data-testid="stButton"] button {
        border-radius: 8px !important;
        transition: all 0.3s ease;
    }
    </style>
""", unsafe_allow_html=True)

# --- 뉴스 수집 함수 ---
@st.cache_data(ttl=600)
def get_viral_top_100():
    url = "https://news.naver.com/main/ranking/popularDay.naver"
    headers = {"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"}
    try:
        res = requests.get(url, headers=headers)
        soup = BeautifulSoup(res.text, 'html.parser')
        unique_news = []
        seen = set()
        for box in soup.select('.rankingnews_box'):
            for li in box.select('.rankingnews_list li'):
                a = li.select_one('a')
                if a and a.text.strip() not in seen:
                    unique_news.append({"title": a.text.strip(), "link": a['href']})
                    seen.add(a.text.strip())
        return unique_news
    except:
        return []

# --- AI S급 필터링 엔진 (조회수 50만~100만 타겟) ---
def filter_s_class_indices(news_list):
    if not model or not news_list: return []
    
    # 상위 50개 제목을 리스트화하여 전달
    titles = [f"{i}: {item['title']}" for i, item in enumerate(news_list[:50])]
    prompt = f"""
    당신은 조회수 100만 이상을 찍는 '국뽕/이슈' 유튜브 채널의 10년차 수석 기획자입니다.
    아래 뉴스 리스트 중 대한민국 유튜브 시장에서 폭발력이 가장 큰(방산, 반도체, 외신극찬, 해외반응, 카타르시스) 
    S급 소재 딱 5개만 엄선하십시오. 
    선정 기준: 조회수 50만~100만 보장, 클릭율 15% 이상 기대 소재.

    결과는 반드시 JSON 형식의 숫자 리스트로만 출력하세요. 
    예: [2, 5, 12, 18, 24]

    뉴스 리스트:
    {chr(10).join(titles)}
    """
    try:
        response = model.generate_content(prompt)
        raw_json = response.text.replace("```json", "").replace("```", "").strip()
        return json.loads(raw_json)
    except:
        return []

def analyze_news_content(url):
    headers = {"User-Agent": "Mozilla/5.0", "Referer": "https://news.naver.com/"}
    try:
        res = requests.get(url, headers=headers)
        soup = BeautifulSoup(res.text, 'html.parser')
        content = soup.select_one('#dic_area') or soup.select_one('#newsct_article')
        text = content.get_text(strip=True) if content else "본문 수집 불가"
        summary = "분석 실패"
        if model and len(text) > 100:
            prompt = f"이 기사가 유튜브에서 100만 조회수를 찍으려면 어떤 '분노'나 '희열' 포인트를 건드려야 할지 전략을 포함해 3줄 요약해줘:\n\n{text[:1500]}"
            summary = model.generate_content(prompt).text
        return text, summary
    except:
        return "실패", "실패"

# --- 메인 인터페이스 ---
st.title("🚀 VIRAL MASTER PRO v2.6")
st.caption("초정밀 AI 필터링 기반 떡상 소재 발굴 시스템")

tab1, tab2 = st.tabs(["👑 실시간 뉴스 탐색", "🎯 S급 소재 판별 & 대본 빌더"])

# --- 탭 1: 실시간 이슈 탐색 (S급 노란색 배경 필터 적용) ---
with tab1:
    col_l, col_r = st.columns([1, 1.2])
    with col_l:
        st.subheader("🔥 AI 선정 S급 황금 소재 (TOP 100)")
        if st.button("🔄 리스트 & S급 분석 갱신"):
            st.cache_data.clear()
            if "s_indices" in st.session_state: del st.session_state.s_indices
            st.rerun()
            
        news_data = get_viral_top_100()
        if news_data:
            # S급 인덱스 선별 (세션 유지)
            if "s_indices" not in st.session_state:
                with st.spinner('Gemini가 100만 조회수 소재를 필터링 중...'):
                    st.session_state.s_indices = filter_s_class_indices(news_data)
            
            s_list = st.session_state.s_indices
            
            for i, item in enumerate(news_data[:40]):
                is_s = i in s_list
                label = f"👑 [S급 소재] {item['title']}" if is_s else f"[{i+1}] {item['title']}"
                
                # S급 소재 버튼 배경색 입히기 (안전한 CSS 인젝션 방식)
                if is_s:
                    st.markdown(f"""
                        <style>
                        div[data-testid="column"]:nth-child(1) div[data-testid="stVerticalBlock"] > div:nth-child({i+4}) button {{
                            background-color: #FFD700 !important;
                            color: black !important;
                            border: 2px solid #FFA500 !important;
                            font-weight: bold !important;
                        }}
                        </style>
                    """, unsafe_allow_html=True)

                if st.button(label, key=f"btn_{i}", use_container_width=True):
                    with st.spinner('분석 중...'):
                        txt, smr = analyze_news_content(item['link'])
                        st.session_state.selected = {"title":item['title'], "text":txt, "summary":smr, "link":item['link'], "is_s":is_s}
        else:
            st.warning("데이터 로딩 실패")

    with col_r:
        if "selected" in st.session_state:
            res = st.session_state.selected
            if res['is_s']:
                st.warning("🏆 이 기사는 100만 조회수를 보장하는 초특급 소재입니다. 무조건 제작하세요.")
            st.subheader(f"📊 {res['title']}")
            st.success(res['summary'])
            st.markdown(f"🔗 [기사 원문]({res['link']})")
            st.divider()
            st.text_area("클로드 입력용 전문 데이터", res['text'], height=400)
        else:
            st.info("왼쪽 리스트에서 소재를 선택하세요.")

# --- 탭 2: 소재 판별 & 대본 빌더 (전문가용 프롬프트 강화) ---
with tab2:
    st.header("🎯 S급 소재 판별 및 초격차 원고 마스터링")
    c_img, c_res = st.columns([1, 1])
    
    with c_img:
        st.markdown("### 📸 캡처본 분석 (Ctrl+V)")
        files = st.file_uploader("네이버/더구루 등 리스트 캡처본을 붙여넣으세요.", accept_multiple_files=True, type=['png','jpg','jpeg'])
        if files and st.button("🔍 멀티 비전 분석 시작", use_container_width=True):
            with st.spinner("Gemini 비전 분석 중..."):
                imgs = [PIL.Image.open(f) for f in files]
                v_prompt = "이미지 내 뉴스 중 국뽕/방산/기술력 등 100만 조회수 S급 소재 5개 선정 및 선정이유 분석"
                resp = model.generate_content([v_prompt] + imgs)
                st.session_state.v_res = resp.text

    with c_res:
        if "v_res" in st.session_state:
            st.markdown("### 🏆 AI 추천 리스트")
            st.markdown(st.session_state.v_res)

    st.divider()
    
    st.header("📝 클로드 프로젝트용 하이엔드 마스터 프롬프트")
    col1, col2 = st.columns(2)
    with col1:
        t_topic = st.text_input("💎 영상 제목 (소재)")
        t_news = st.text_area("📰 팩트 데이터 (복붙)", height=250)
    with col2:
        t_yt = st.text_input("📺 벤치마킹 타겟 채널")
        t_comm = st.text_area("💬 실시간 댓글 민심 (복붙)", height=250)

    if st.button("🔥 클로드 초격차 지침 생성", use_container_width=True):
        master_prompt = f"""
# 지시사항: 100만 유튜버 메인 작가용 '초격차 원고' 집필 지침

## 1. 너의 페르소나 (ROLE)
너는 구독자 200만 명을 보유한 '이슈서치', '퍼플'급 채널의 수석 작가다. 
너의 원고는 단순한 정보 전달이 아니라 시청자의 심장을 뛰게 하고, 손가락을 댓글창으로 강제 이동시키는 '마법의 서사'다.

## 2. 입력 데이터 기반 (INPUT)
- 핵심 소재: {t_topic}
- 팩트 원본: {t_news}
- 벤치마킹 스타일: {t_yt}
- 시청자 민심: {t_comm}

## 3. 원고 집필 7단계 공식 (MANDATORY)
1) [HOOK: 0~30초]: 충격적 사실로 시작하라. "지금 전 세계가 발칵 뒤집혔습니다. 우리 정부조차 몰랐던 사실입니다."
2) [CTA 1]: 짧고 굵게. "오늘 이 상황, 끝까지 보셔야 이유를 압니다."
3) [CONTEXT]: 사건의 배경을 영화처럼 묘사하라. 
4) [FACT ATTACK]: 수집된 뉴스 팩트를 '능글맞게' 요약하라. "일본의 반응은 그야말로 코미디였습니다."
5) [EMOTION SYNC]: 댓글 민심을 인용하여 공감대를 형성하라. "국민들은 이미 꿰뚫어 보고 계셨죠."
6) [CATHARSIS]: 대한민국의 위상이나 반전의 결과를 선사하며 전율을 느끼게 하라.
7) [OUTRO/CTA 2]: 깊은 여운을 남기는 한마디와 함께 채널 구독 유도.

## 4. 나레이션 및 비주얼 가이드 (CRITICAL)
- 모든 문장에 감정 태그를 삽입하라. (예: [냉소], [경악], [진심], [비웃음])
- 화면 구성을 위해 [Visual: 구체적인 이미지/자막 설명] 가이드를 매 단락마다 넣을 것.
- 가독성을 위해 문장은 짧고 호흡이 빠르게 구성하라.

## 5. 최종 산출물 요구사항
- 총 분량 3,500자 이상 (8분 영상 타겟)
- 초 공격형 썸네일 카피 3종 및 제목 5종 제안.
        """
        st.code(master_prompt, language="markdown")
        st.success("위 지침을 복사하여 클로드 프로젝트 '지침' 또는 첫 메시지에 입력하세요.")
