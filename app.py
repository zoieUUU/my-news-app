import streamlit as st
import requests
from bs4 import BeautifulSoup
import google.generativeai as genai

# 1. AI 보안 및 엔진 설정
try:
    genai.configure(api_key=st.secrets["GOOGLE_API_KEY"])
    model = genai.GenerativeModel('gemini-1.5-flash')
except:
    st.error("Secrets에 API 키를 먼저 등록해주세요!")

st.set_page_config(page_title="유메이커 MASTER", layout="wide")

# --- 뉴스 수집 및 AI S급 자동 선별 ---
@st.cache_data(ttl=600)
def get_and_rank_news():
    url = "https://news.naver.com/main/ranking/popularDay.naver"
    headers = {"User-Agent": "Mozilla/5.0"}
    res = requests.get(url, headers=headers)
    soup = BeautifulSoup(res.text, 'html.parser')
    
    raw_data = []
    # 상위 10개 언론사에서 5개씩 총 50개 수집
    for box in soup.select('.rankingnews_box')[:10]:
        press = box.select_one('.rankingnews_name').text.strip()
        for li in box.select('.rankingnews_list li')[:5]:
            a_tag = li.select_one('a')
            if a_tag:
                raw_data.append({"언론사": press, "제목": a_tag.text.strip(), "링크": a_tag['href']})
    
    # [핵심] AI가 리스트를 보고 S급(조회수 폭발) 5개 미리 점지
    all_titles = "\n".join([f"{i}. {d['제목']}" for i, d in enumerate(raw_data)])
    pick_prompt = f"""너는 유튜브 100만 기획자야. 다음 뉴스 중 유튜브 조회수 5만~10만 이상 무조건 터질 소재(S급) 5개를 골라 번호만 써줘. 예: 1, 5, 10, 15, 20\n{all_titles}"""
    
    try:
        response = model.generate_content(pick_prompt)
        s_picks = [int(i.strip()) for i in response.text.split(',') if i.strip().isdigit()]
    except:
        s_picks = []
    return raw_data, s_picks

def get_content(url):
    res = requests.get(url, headers={"User-Agent": "Mozilla/5.0"})
    soup = BeautifulSoup(res.text, 'html.parser')
    content = soup.select_one('#newsct_article') or soup.select_one('#articleBodyContents')
    return content.text.strip() if content else "본문을 가져올 수 없습니다."

# --- 화면 레이아웃 ---
st.title("🚀 유메이커 MASTER : S급 소재 판별기")
left_col, right_col = st.columns([1, 1.2])

with left_col:
    st.subheader("🔥 실시간 TOP 100 (AI S급 추천)")
    news_list, s_picks = get_and_rank_news()
    
    for i, row in enumerate(news_list):
        is_s = i in s_picks
        # S급은 빨간색 배경 효과 (Streamlit의 버튼 스타일링 제한으로 아이콘 활용)
        label = f"🔥 [S급 유력] {row['제목']}" if is_s else f"{row['제목']}"
        
        if st.button(f"[{row['언론사']}] {label}", key=f"n_{i}", use_container_width=True):
            st.session_state.url = row['링크']
            st.session_state.title = row['제목']
            st.session_state.content = get_content(row['링크'])
            st.session_state.is_s = is_s

with right_col:
    if 'title' in st.session_state:
        # S급 하이라이트 박스
        if st.session_state.is_s:
            st.error("🎯 AI 판정: 이 소재는 유튜브 황금 키워드(조회수 10만 예상)입니다!")
        
        st.subheader("📄 뉴스 원문 텍스트")
        st.info(f"**제목: {st.session_state.title}**")
        st.text_area("본문", st.session_state.content, height=250)
        
        # [수정된 분석 버튼]
        if st.button("🚀 S급 마스터 대본 생성", type="primary", use_container_width=True):
            with st.spinner('실시간 검색량 및 시의성 반영 대본 집필 중...'):
                prompt = f"""너는 유메이커 채널 작가야. 다음 뉴스를 분석해.
                제목: {st.session_state.title}
                본문: {st.session_state.content}
                
                1. 소재 등급 판정 (S, A, B) 및 근거 (검색량 5만건 이상 분석)
                2. 타겟 감정 분석 (분노/공감/충격 %)
                3. 100만 조회수 어그로 제목 3가지
                4. 3,500자 분량의 공격적 대본 (0~25초 훅 필수 포함)
                5. 썸네일 구도 레퍼런스 및 문구"""
                response = model.generate_content(prompt)
                st.markdown("---")
                st.markdown(response.text)
    else:
        st.write("👈 왼쪽 리스트에서 🔥 표시된 뉴스부터 클릭해 보세요!")
