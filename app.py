import streamlit as st
import requests
from bs4 import BeautifulSoup
import google.generativeai as genai
import PIL.Image
import io
import json

# 1. AI 엔진 설정 (Gemini 1.5 Flash)
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

# --- 초강력 CSS 스타일링 (S급 소재를 위한 특수 효과) ---
st.markdown("""
    <style>
    /* S급 버튼 전용 애니메이션: 번쩍이는 골드 효과 */
    @keyframes gold-pulse {
        0% { box-shadow: 0 0 0 0 rgba(255, 215, 0, 0.7); }
        70% { box-shadow: 0 0 0 15px rgba(255, 215, 0, 0); }
        100% { box-shadow: 0 0 0 0 rgba(255, 215, 0, 0); }
    }

    /* S급 뉴스 버튼 스타일 */
    .s-class-active {
        background: linear-gradient(90deg, #FFD700, #FF8C00) !important;
        color: black !important;
        font-weight: 900 !important;
        border: 3px solid #FF4500 !important;
        animation: gold-pulse 2s infinite;
        font-size: 1.1rem !important;
        transform: scale(1.02);
    }

    /* 일반 버튼 기본 스타일 최적화 */
    div[data-testid="stButton"] button {
        border-radius: 12px;
        transition: all 0.2s ease-in-out;
        margin-bottom: 4px;
    }
    
    /* 탭 디자인 강화 */
    .stTabs [data-baseweb="tab-list"] {
        gap: 24px;
    }
    .stTabs [data-baseweb="tab"] {
        height: 50px;
        font-size: 18px;
        font-weight: 700;
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

# --- 초정밀 S급 필터링 엔진 (유튜브 기획자 로직 적용) ---
def filter_s_class_indices(news_list):
    if not model or not news_list: return []
    
    titles = [f"{i}: {item['title']}" for i, item in enumerate(news_list[:60])]
    prompt = f"""
    당신은 100만 조회수 국뽕/이슈 채널을 운영하는 '신의 손' 기획자입니다.
    아래 뉴스 리스트 60개 중, 유튜브 시장에서 무조건 50만~100만 조회수를 보장하는 'S급 황금 소재' 딱 5개만 골라내십시오.

    [필터링 기준 (Strict)]
    1. 카테고리: 방산(무기 수출), 반도체(삼성/하이닉스 압살), 조선(독점 계약), 스포츠(손흥민/이강인 등 국위선양), 세계가 놀란 우리나라 기술/시민의식.
    2. 화제성: 외신이 극찬하거나, 일본/중국이 배 아파하거나, 미국이 당황하는 등 '카타르시스'가 느껴지는 소재.
    3. 잠재력: 제목만으로 클릭율(CTR) 15% 이상 뽑아낼 수 있는 자극적인 팩트가 포함된 소재.

    결과는 반드시 JSON 형식의 숫자 리스트로만 출력하세요. (예: [3, 7, 15, 22, 45])
    
    데이터:
    {chr(10).join(titles)}
    """
    try:
        response = model.generate_content(prompt)
        raw_json = response.text.replace("```json", "").replace("```", "").strip()
        indices = json.loads(raw_json)
        return indices[:5] # 정확히 5개만 반환
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
            prompt = f"이 기사가 유튜브에서 100만 조회수를 찍기 위한 '썸네일 문구'와 '핵심 갈등/희열 포인트'를 중심으로 3줄 요약해줘:\n\n{text[:2000]}"
            summary = model.generate_content(prompt).text
        return text, summary
    except:
        return "실패", "실패"

# --- 메인 인터페이스 ---
st.title("🚀 VIRAL MASTER PRO v2.6")
st.caption("대한민국 0.1% 이슈 큐레이터를 위한 초정밀 떡상 소재 발굴기")

tab1, tab2 = st.tabs(["👑 실시간 황금소재 탐색", "🎯 S급 빌더 & 원고 마스터"])

# --- 탭 1: 실시간 이슈 탐색 ---
with tab1:
    col_l, col_r = st.columns([1, 1.2])
    with col_l:
        st.subheader("🔥 AI 엄선: 100만 돌파 가능 소재")
        if st.button("🔄 리스트 & S급 알고리즘 갱신"):
            st.cache_data.clear()
            if "s_indices" in st.session_state: del st.session_state.s_indices
            st.rerun()
            
        news_data = get_viral_top_100()
        if news_data:
            if "s_indices" not in st.session_state:
                with st.spinner('유튜브 기획자 AI가 S급 소재를 선별하는 중...'):
                    st.session_state.s_indices = filter_s_class_indices(news_data)
            
            s_list = st.session_state.s_indices
            
            # 리스트 표시
            for i, item in enumerate(news_data[:45]):
                is_s = i in s_list
                
                # S급 소재에 대한 강력한 시각적 효과 부여
                if is_s:
                    label = f"🏆 [S급/100만+] {item['title']}"
                    # 특정 버튼에 클래스 주입을 위한 CSS (nth-child 최적화)
                    st.markdown(f"""
                        <style>
                        div[data-testid="column"]:nth-child(1) div[data-testid="stVerticalBlock"] > div:nth-child({i+4}) button {{
                            background: linear-gradient(90deg, #FFD700, #FF8C00) !important;
                            color: black !important;
                            font-weight: 900 !important;
                            border: 3px solid #FF4500 !important;
                            animation: gold-pulse 2s infinite !important;
                            transform: scale(1.02) !important;
                        }}
                        </style>
                    """, unsafe_allow_html=True)
                else:
                    label = f"[{i+1}] {item['title']}"

                if st.button(label, key=f"btn_{i}", use_container_width=True):
                    with st.spinner('전략 분석 중...'):
                        txt, smr = analyze_news_content(item['link'])
                        st.session_state.selected = {"title":item['title'], "text":txt, "summary":smr, "link":item['link'], "is_s":is_s}
        else:
            st.warning("네이버 뉴스 데이터를 가져올 수 없습니다.")

    with col_r:
        if "selected" in st.session_state:
            res = st.session_state.selected
            if res['is_s']:
                st.warning("✨ [기획자 의견] 이 소재는 '국뽕/방산/반도체' 키워드와 완벽히 결합됩니다. 100만 조회수 타겟 원고 작성을 권장합니다.")
            
            st.markdown(f"### 📊 {res['title']}")
            st.info(f"**AI 전략 분석:**\n\n{res['summary']}")
            st.markdown(f"🔗 [기사 원문 바로가기]({res['link']})")
            st.divider()
            st.markdown("**📝 클로드/GPT 입력용 팩트 전문**")
            st.text_area("기사 데이터", res['text'], height=450)
        else:
            st.info("왼쪽 리스트에서 분석할 소재를 선택하세요. 노란색 버튼은 'S급' 떡상 보증 소재입니다.")

# --- 탭 2: 소재 판별 & 대본 빌더 ---
with tab2:
    st.header("🎯 초격차 원고 제작 프로젝트")
    c_img, c_res = st.columns([1, 1])
    
    with c_img:
        st.markdown("### 📸 타 채널/커뮤니티 캡처본 분석 (Ctrl+V)")
        files = st.file_uploader("더구루, 커뮤니티 인기글, 타 채널 리스트 캡처본 업로드", accept_multiple_files=True, type=['png','jpg','jpeg'])
        if files and st.button("🔍 멀티 캡처 통합 비전 분석", use_container_width=True):
            with st.spinner("이미지 속 텍스트와 맥락을 분석 중..."):
                imgs = [PIL.Image.open(f) for f in files]
                v_prompt = """당신은 100만 유튜버 기획자입니다. 캡처된 이미지들 속 뉴스 중 
                1. 국뽕, 방산, 반도체, 세계 속 한국의 위상과 관련된 S급 소재를 찾으세요.
                2. 해당 소재가 왜 100만 조회수가 가능한지 '시청자 심리' 관점에서 분석하세요.
                3. 가장 자극적인 썸네일 제목 후보 3개를 제안하세요."""
                resp = model.generate_content([v_prompt] + imgs)
                st.session_state.v_res = resp.text

    with c_res:
        if "v_res" in st.session_state:
            st.markdown("### 🏆 비전 분석 결과")
            st.success(st.session_state.v_res)

    st.divider()
    
    st.header("📝 클로드(Claude) 전용 하이엔드 작가 지침 생성")
    col1, col2 = st.columns(2)
    with col1:
        t_topic = st.text_input("💎 확정 영상 제목")
        t_news = st.text_area("📰 팩트 데이터 (기사 전문 복붙)", height=250)
    with col2:
        t_yt = st.text_input("📺 벤치마킹 채널 (예: 이슈서치)")
        t_comm = st.text_area("💬 실시간 민심 (댓글/커뮤니티 반응)", height=250)

    if st.button("🔥 초격차 대본 지침(Master Prompt) 생성", use_container_width=True):
        master_prompt = f"""
# ROLE: 대한민국 0.1% 하이엔드 이슈 스토리텔러 (수석 작가)
너는 조회수 200만 '이슈서치'의 문법을 지배하는 작가다. 아래 데이터를 바탕으로 시청자가 8분 동안 한순간도 눈을 떼지 못할 원고를 집필하라.

## [입력 소스]
- 핵심 주제: {t_topic}
- 뉴스 데이터: {t_news}
- 벤치마킹 타겟: {t_yt}
- 시청자 민심: {t_comm}

## [필수 집필 지침 (EXTREME DETAIL)]
1. [HOOK]: 첫 15초에 시청자의 뇌를 마비시켜라. "전 세계가 지금 경악하고 있습니다. 한국이 이 정도일 줄은 몰랐던 거죠."
2. [7단계 서사구조]: 충격 오프닝 -> CTA1 -> 사건 배경 -> 심층 분석(국뽕/카타르시스) -> 실시간 민심 반영 -> 대반전 결과 -> 결론 및 CTA2.
3. [톤앤매너]: 능글맞으면서도 날카로운 풍자. "상대방 국가의 반응요? 그야말로 처참한 코미디가 따로 없습니다."
4. [나레이션 가이드]: 문장마다 감정 태그 삽입([냉소], [경악], [환호], [진심]). 
5. [비주얼 지시]: 영상 편집자가 바로 작업할 수 있게 [Visual: 0000 하는 장면 삽입] 지시어를 단락마다 포함할 것.

## [최종 결과물 구성]
- 8분 분량 (3,800자 이상의 꽉 찬 구성)
- 클릭율 20% 보장하는 초 공격형 제목 5종
- 썸네일 제작을 위한 핵심 오브제 및 자막 배치 가이드
        """
        st.code(master_prompt, language="markdown")
        st.success("지침 생성이 완료되었습니다. 클로드에 그대로 전달하세요!")
