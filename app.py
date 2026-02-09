import streamlit as st
import requests
from bs4 import BeautifulSoup
import google.generativeai as genai
import PIL.Image
import io

# 1. AI 엔진 설정 (Gemini 1.5 Flash - 비전 인식 특화)
@st.cache_resource
def load_ai_model():
    try:
        # Streamlit secrets에 GOOGLE_API_KEY가 설정되어 있어야 합니다.
        genai.configure(api_key=st.secrets["GOOGLE_API_KEY"])
        return genai.GenerativeModel('models/gemini-1.5-flash')
    except Exception as e:
        st.error(f"AI 모델 로드 실패: {e}")
        return None

model = load_ai_model()

st.set_page_config(page_title="VIRAL MASTER PRO v2.6", layout="wide")

# --- 뉴스 수집 함수 (네이버 랭킹 뉴스) ---
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

def analyze_news_content(url):
    headers = {"User-Agent": "Mozilla/5.0", "Referer": "https://news.naver.com/"}
    try:
        res = requests.get(url, headers=headers)
        soup = BeautifulSoup(res.text, 'html.parser')
        content = soup.select_one('#dic_area') or soup.select_one('#newsct_article')
        text = content.get_text(strip=True) if content else "본문을 가져올 수 없습니다."
        
        summary = "분석 중..."
        if model and len(text) > 100:
            prompt = f"다음 뉴스 기사의 핵심 내용을 2줄로 요약하고, 이슈 분석 채널에 적합한 태그 3개를 뽑아줘:\n\n{text[:1500]}"
            summary = model.generate_content(prompt).text
        return text, summary
    except:
        return "수집 실패", "분석 실패"

# --- 메인 인터페이스 ---
st.title("🚀 VIRAL MASTER PRO v2.6")
st.caption("실시간 트렌드 분석부터 초격차 대본 빌더까지 (Multi-Capture Ctrl+V 지원)")

# 탭 제목에 아이콘을 추가하여 시각적 직관성을 높임 (왕관 아이콘 복구)
tab1, tab2 = st.tabs(["👑 실시간 뉴스 탐색", "🎯 S급 소재 판별 & 대본 빌더"])

# --- 탭 1: 실시간 이슈 탐색 ---
with tab1:
    col_l, col_r = st.columns([1, 1.2])
    with col_l:
        st.subheader("🔥 네이버 실시간 TOP 100")
        if st.button("🔄 뉴스 리스트 새로고침"):
            st.cache_data.clear()
            st.rerun()
            
        news_data = get_viral_top_100()
        if news_data:
            for i, item in enumerate(news_data[:40]):
                if st.button(f"[{i+1}] {item['title']}", key=f"news_{i}", use_container_width=True):
                    with st.spinner('AI가 기사 분석 중...'):
                        txt, sum_res = analyze_news_content(item['link'])
                        st.session_state.selected_news = {
                            "title": item['title'],
                            "text": txt,
                            "summary": sum_res,
                            "link": item['link']
                        }
        else:
            st.warning("뉴스를 불러올 수 없습니다. 잠시 후 다시 시도해주세요.")

    with col_r:
        if "selected_news" in st.session_state:
            res = st.session_state.selected_news
            st.subheader("📊 AI 기사 분석 리포트")
            st.success(res['summary'])
            st.markdown(f"🔗 [원문 기사 바로가기]({res['link']})")
            st.divider()
            st.markdown("### 📝 기사 전문 (복사용)")
            st.text_area("본문 데이터", res['text'], height=450)
        else:
            st.info("왼쪽 뉴스 리스트에서 분석할 기사를 클릭하세요.")

# --- 탭 2: 소재 선별 & 대본 생성 (핵심 기능) ---
with tab2:
    st.header("🎯 S급 떡상 소재 선별기")
    st.markdown("네이버 뉴스, 더구루, 커뮤니티 등의 캡처본을 한꺼번에 붙여넣어 분석하세요.")

    # 1. 멀티 캡처 분석 섹션
    up_col, res_col = st.columns([1, 1])
    
    with up_col:
        st.markdown("### 📸 캡처본 붙여넣기 (Ctrl+V)")
        # accept_multiple_files=True로 설정하여 여러 장의 이미지를 순차적으로 붙여넣기 가능
        captured_images = st.file_uploader(
            "이 영역을 클릭한 뒤 Ctrl+V로 이미지를 붙여넣으세요 (여러 장 가능)", 
            type=['png', 'jpg', 'jpeg'], 
            accept_multiple_files=True
        )
        
        if captured_images and st.button("🔍 통합 소재 등급 분석 시작", use_container_width=True):
            with st.spinner("Gemini AI가 모든 이미지를 교차 분석 중..."):
                img_list = [PIL.Image.open(img) for img in captured_images]
                
                vision_prompt = """
                당신은 100만 유튜버의 메인 기획자입니다. 제공된 모든 이미지(캡처본) 속의 기사 제목과 화제성을 분석하십시오.
                
                1. 이 중 조회수 50만~100만 이상을 보장하는 'S급 소재' 5개를 선정하십시오.
                2. 선정 이유를 '시청자 분노', '카타르시스', '애국심', '최초 정보' 등의 관점에서 상세히 기술하십시오.
                3. 해당 소재로 영상을 만들었을 때 시청자가 반응할 '민심 포인트'를 예측하십시오.
                
                [형식]
                - 순위: 제목 (잠재력 등급)
                - 이유: 
                - 공략 포인트:
                """
                
                # 이미지 리스트와 프롬프트를 함께 전달
                response = model.generate_content([vision_prompt] + img_list)
                st.session_state.s_class_result = response.text

    with res_col:
        if "s_class_result" in st.session_state:
            st.markdown("### 🏆 AI 추천 S급 소재 리스트")
            st.markdown(st.session_state.s_class_result)
        else:
            st.info("이미지를 업로드하고 분석 버튼을 눌러주세요.")

    st.divider()

    # 2. 클로드 마스터 프롬프트 빌더
    st.header("📝 클로드 프로젝트용 마스터 프롬프트 생성")
    
    c1, c2 = st.columns(2)
    with c1:
        final_topic = st.text_input("💎 확정 소재 (제목)")
        final_news = st.text_area("📰 참고 뉴스 데이터 (최대 5개 링크 또는 본문 복붙)", height=250)
    with c2:
        final_yt = st.text_input("📺 벤치마킹 채널 URL (예: 이슈서치)")
        final_comments = st.text_area("💬 실시간 댓글 민심 (유튜브/커뮤니티 댓글 복붙)", height=250)

    if st.button("🔥 클로드 초격차 원고 프롬프트 생성", use_container_width=True):
        master_instruction = f"""
# ROLE: 대한민국 0.1% 하이엔드 이슈 스토리텔러
너는 단순 작가가 아닌, 시청자의 멱살을 잡고 끝까지 끌고 가는 '서사의 지배자'다. 
'이슈서치' 채널의 문법을 완벽히 재현하라.

[재료 데이터]
- 소재: {final_topic}
- 뉴스 팩트: {final_news}
- 벤치마킹: {final_yt}
- 댓글 민심: {final_comments}

[미션: 8~9분 분량(3,500자 이상) 초몰입형 대본 집필]
1. 현장감 극대화: "뉴스가 떴습니다"가 아닌 "지금 현장은 비명이 터집니다" 같은 현장 묘사 위주로 시작하라.
2. 유머러스한 비꼼: "상황이 안 좋습니다" 대신 "상대방 낯빛이 흙빛이 됐네요. 참 기묘한 코미디입니다"라며 풍자하라.
3. 7단계 서사: 훅(충격 오프닝) -> CTA1 -> 배경 -> 심층분석 -> 민심공감 -> 카타르시스 반전 -> 결론/CTA2.
4. 나레이션용 감정 태그([분노], [비웃음], [진지])와 이미지 생성을 위한 [Visual 프롬프트] 가이드를 문장 사이에 삽입하라.
5. 초 공격형 제목 3종과 썸네일 카피를 제안하라.
        """
        st.markdown("### 📋 클로드 지침 칸에 붙여넣으세요")
        st.code(master_instruction, language="markdown")
        st.success("프롬프트가 생성되었습니다! 클로드 프로젝트 대화창에 던지세요.")
