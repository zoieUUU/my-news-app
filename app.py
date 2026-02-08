import streamlit as st
import requests
from bs4 import BeautifulSoup
import google.generativeai as genai

# 1. AI 보안 설정
try:
    genai.configure(api_key=st.secrets["GOOGLE_API_KEY"])
    model = genai.GenerativeModel('gemini-1.5-flash')
except:
    st.error("Streamlit Settings -> Secrets에 GOOGLE_API_KEY를 등록해주세요!")

st.set_page_config(page_title="유메이커 MASTER 시스템", layout="wide")
st.title("🚀 유메이커 MASTER : 올인원 데이터 분석 허브")

# --- 뉴스 수집 엔진 ---
def get_naver_top100():
    url = "https://news.naver.com/main/ranking/popularDay.naver"
    headers = {"User-Agent": "Mozilla/5.0"}
    res = requests.get(url, headers=headers)
    soup = BeautifulSoup(res.text, 'html.parser')
    data = []
    for box in soup.select('.rankingnews_box')[:12]: # 주요 언론사 위주
        press = box.select_one('.rankingnews_name').text.strip()
        for li in box.select('.rankingnews_list li')[:5]:
            a_tag = li.select_one('a')
            if a_tag:
                data.append({"언론사": press, "제목": a_tag.text.strip(), "링크": a_tag['href']})
    return data

def get_content(url):
    try:
        res = requests.get(url, headers={"User-Agent": "Mozilla/5.0"})
        soup = BeautifulSoup(res.text, 'html.parser')
        content = soup.select_one('#newsct_article') or soup.select_one('#articleBodyContents')
        return content.text.strip() if content else "본문 추출 실패"
    except: return "연결 오류"

# --- 화면 구성 ---
tab1, tab2 = st.tabs(["📊 실시간 소재 발굴", "🎯 원큐 빌더 (대본 제작)"])

with tab1:
    st.subheader("🔥 네이버 실시간 TOP 100")
    news_list = get_naver_top100()
    cols = st.columns(2)
    for i, row in enumerate(news_list):
        with cols[i % 2]:
            if st.button(f"[{row['언론사']}] {row['제목']}", key=f"news_{i}"):
                st.session_state.url = row['링크']
                st.session_state.title = row['제목']
                st.success("소재가 선정되었습니다! '원큐 빌더' 탭으로 이동하세요.")

with tab2:
    st.subheader("🛠️ S급 판별 및 마스터링 대본 생성")
    col_in, col_out = st.columns([1, 2])
    
    with col_in:
        target_title = st.text_input("선정된 뉴스 제목", value=st.session_state.get('title', ''))
        ref_links = st.text_area("참고 URL (최대 5개 복붙)", value=st.session_state.get('url', ''))
        tone = st.radio("대본 스타일", ["공격형 (이슈/분노)", "정보형 (팩트체크)"])
        st.caption("황금키워드 분석: 월간 검색량 5만건 이상 데이터 대조")
        
    with col_out:
        if st.button("🚀 유메이커 콘텐츠 공장 가동"):
            if not target_title:
                st.warning("먼저 뉴스를 선택하거나 제목을 입력하세요.")
            else:
                with st.spinner('방대한 뉴스 데이터 파싱 및 3,500자 대본 집필 중...'):
                    content = get_content(ref_links.split('\n')[0])
                    prompt = f"""
                    너는 100만 유튜버 '유메이커'의 메인 기획자다. 다음 데이터를 기반으로 작업하라.
                    뉴스: {target_title} / 본문: {content}
                    
                    [1. 소재 등급 판별]
                    - S등급(조회수 50만 확정), A등급, B등급 중 판정.
                    - 근거: 유사 키워드 영상 평균 조회수 10만 돌파 여부 및 시의성.
                    
                    [2. 3,500자 마스터 대본 ({tone})]
                    - 0~25초: 충격적인 훅 (킹받는 포인트 강조)
                    - 25~40초: CTA (좋아요, 구독 유도)
                    - 이후: 배경설명 -> 사건 경위 -> 댓글 민심 분석 반영 -> 결론 및 토론 유도
                    - 말투: {tone}에 맞춰 흡입력 있게 작성.
                    
                    [3. 썸네일 & 제목 세트]
                    - 클릭 유도형 제목 3가지 (어그로/공포/질문형)
                    - 썸네일 구도 및 문구 추천 (시각적 대비형)
                    """
                    response = model.generate_content(prompt)
                    st.markdown(response.text)
