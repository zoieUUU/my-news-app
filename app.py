import streamlit as st
import requests
from bs4 import BeautifulSoup
import google.generativeai as genai

# 1. AI 엔진 설정
try:
    genai.configure(api_key=st.secrets["GOOGLE_API_KEY"])
    model = genai.GenerativeModel('gemini-1.5-flash')
except:
    st.error("Secrets에 API 키를 먼저 등록해주세요!")

st.set_page_config(page_title="유메이커 MASTER", layout="wide")

# --- 뉴스 수집 및 S급 선별 함수 ---
@st.cache_data(ttl=600)
def get_ranked_news():
    url = "https://news.naver.com/main/ranking/popularDay.naver"
    headers = {"User-Agent": "Mozilla/5.0"}
    res = requests.get(url, headers=headers)
    soup = BeautifulSoup(res.text, 'html.parser')
    
    raw_data = []
    for box in soup.select('.rankingnews_box')[:10]:
        press = box.select_one('.rankingnews_name').text.strip()
        for li in box.select('.rankingnews_list li')[:5]:
            a_tag = li.select_one('a')
            if a_tag:
                raw_data.append({"언론사": press, "제목": a_tag.text.strip(), "링크": a_tag['href']})
    
    # AI에게 S급 소재 5개 추천 요청
    titles = "\n".join([f"{i}. {d['제목']}" for i, d in enumerate(raw_data)])
    pick_prompt = f"유튜브 기획자로서 다음 뉴스 중 가장 터질 소재 5개의 번호만 골라줘: {titles}"
    try:
        resp = model.generate_content(pick_prompt)
        s_picks = [int(i.strip()) for i in resp.text.split(',') if i.strip().isdigit()]
    except: s_picks = []
    return raw_data, s_picks

def get_content(url):
    try:
        res = requests.get(url, headers={"User-Agent": "Mozilla/5.0"})
        soup = BeautifulSoup(res.text, 'html.parser')
        content = soup.select_one('#newsct_article') or soup.select_one('#articleBodyContents')
        return content.text.strip() if content else "본문 추출 실패"
    except: return "연결 오류"

# --- 메인 화면 레이아웃 ---
tab1, tab2 = st.tabs(["🔥 1단계: S급 소재 발굴", "🎯 2단계: 멀티 링크 통합 원고"])

with tab1:
    st.subheader("실시간 TOP 100 (AI S급 자동 필터링)")
    l_col, r_col = st.columns([1, 1])
    
    with l_col:
        news_list, s_picks = get_ranked_news()
        for i, row in enumerate(news_list):
            is_s = i in s_picks
            btn_label = f"🔥 [S급] {row['제목']}" if is_s else row['제목']
            # S급 소재는 눈에 띄게 표시
            if st.button(f"[{row['언론사']}] {btn_label}", key=f"list_{i}", use_container_width=True):
                st.session_state.sel_title = row['제목']
                st.session_state.sel_url = row['링크']
                st.session_state.sel_content = get_content(row['링크'])
                st.session_state.is_s = is_s

    with r_col:
        if 'sel_title' in st.session_state:
            if st.session_state.is_s: st.error("🎯 AI 판정: 이 소재는 무조건 터지는 S급입니다!")
            st.info(f"**선택된 뉴스: {st.session_state.sel_title}**")
            st.text_area("순수 원문 텍스트", st.session_state.sel_content, height=400)
            st.write("👉 원고 작성을 원하시면 위쪽 '2단계' 탭으로 이동하세요!")
        else:
            st.write("👈 왼쪽에서 뉴스 소재를 클릭하면 원문이 나타납니다.")

with tab2:
    st.subheader("🛠️ 멀티 링크 통합 초바이럴 원고 빌더")
    st.write("선택한 소재와 관련된 추가 뉴스 링크들을 넣어주세요. AI가 하나로 합쳐서 초벌 원고를 만듭니다.")
    
    target_urls = st.text_area("🔗 관련 뉴스 링크 입력 (한 줄에 하나씩)", 
                              value=st.session_state.get('sel_url', ''), height=150)
    
    if st.button("🚀 초바이럴 1차 원고 생성 (클로드 가공용)", type="primary", use_container_width=True):
        with st.spinner('여러 기사의 팩트를 통합하여 최강의 초벌 원고 집필 중...'):
            combined_content = ""
            for url in target_urls.split('\n'):
                if url.strip():
                    combined_content += f"\n\n[참고기사]\n{get_content(url.strip())}"
            
            final_prompt = f"""
            너는 100만 유튜버 '유메이커'의 메인 작가야. 
            다음 통합된 뉴스 데이터를 바탕으로 '클로드 가공용' 1차 초벌 원고를 작성해.
            
            [통합 데이터]
            {combined_content}
            
            [작성 지침]
            1. 모든 기사의 핵심 팩트를 누락 없이 논리적으로 연결하라.
            2. 0~25초: 시청자가 못 빠져나가게 하는 '공격적 훅'을 배치하라.
            3. 클로드에서 2차 가공할 때 '분노'나 '감동'을 극대화할 수 있도록 팩트 위주로 묵직하게 써라.
            4. 3,500자 이상의 충분한 정보를 담아라.
            """
            response = model.generate_content(final_prompt)
            st.divider()
            st.success("✅ 1차 초벌 원고 완성! 아래 내용을 복사해서 클로드로 가져가세요.")
            st.code(response.text, language="markdown")
