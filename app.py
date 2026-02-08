import streamlit as st
import requests
from bs4 import BeautifulSoup
import google.generativeai as genai

# 1. AI 엔진 설정 (가장 안정적인 호출 방식)
try:
    genai.configure(api_key=st.secrets["GOOGLE_API_KEY"])
    # 404 에러 방지를 위해 가장 범용적인 gemini-1.5-flash 사용
    model = genai.GenerativeModel('gemini-1.5-flash')
except Exception as e:
    st.error(f"설정 에러: {e}")

st.set_page_config(page_title="유메이커 MASTER", layout="wide")

# --- 뉴스 수집 함수 ---
@st.cache_data(ttl=600)
def get_ranked_news():
    url = "https://news.naver.com/main/ranking/popularDay.naver"
    headers = {"User-Agent": "Mozilla/5.0"}
    res = requests.get(url, headers=headers)
    soup = BeautifulSoup(res.text, 'html.parser')
    
    raw_data = []
    for box in soup.select('.rankingnews_box')[:12]:
        press = box.select_one('.rankingnews_name').text.strip()
        for li in box.select('.rankingnews_list li')[:5]:
            a_tag = li.select_one('a')
            if a_tag:
                raw_data.append({"언론사": press, "제목": a_tag.text.strip(), "링크": a_tag['href']})
    
    # S급 선별 (에러 방지용 단순 매칭)
    try:
        titles_block = "\n".join([f"- {d['제목']}" for d in raw_data[:20]])
        pick_prompt = f"유튜브 조회수 대박 날 뉴스 제목 5개만 골라줘:\n{titles_block}"
        resp = model.generate_content(pick_prompt)
        s_titles = resp.text
        for d in raw_data:
            d['is_s'] = d['제목'] in s_titles
    except:
        for d in raw_data: d['is_s'] = False
        
    return raw_data

def get_content(url):
    try:
        res = requests.get(url, headers={"User-Agent": "Mozilla/5.0"})
        soup = BeautifulSoup(res.text, 'html.parser')
        content = soup.select_one('#newsct_article') or soup.select_one('#articleBodyContents')
        return content.text.strip() if content else "본문 추출 실패"
    except: return "연결 실패"

# --- 화면 레이아웃 ---
st.title("🚀 유메이커 MASTER : S급 선별 및 초벌 빌더")
tab1, tab2 = st.tabs(["📊 1단계: S급 소재 발굴", "✍️ 2단계: 멀티 링크 초벌 원고"])

with tab1:
    l_col, r_col = st.columns([1, 1.2])
    with l_col:
        news_list = get_ranked_news()
        # S급을 위로 올림
        sorted_list = sorted(news_list, key=lambda x: x.get('is_s', False), reverse=True)
        for i, row in enumerate(sorted_list):
            label = f"🔥 [S급] {row['제목']}" if row.get('is_s') else row['제목']
            if st.button(f"[{row['언론사']}] {label}", key=f"news_{i}", use_container_width=True):
                st.session_state.sel_title = row['제목']
                st.session_state.sel_url = row['링크']
                st.session_state.sel_content = get_content(row['링크'])
                st.session_state.is_s = row.get('is_s', False)
    with r_col:
        if 'sel_title' in st.session_state:
            if st.session_state.is_s:
                st.error("🎯 AI 판정: 유튜브 100만 조회수 후보입니다!")
            st.info(f"**{st.session_state.sel_title}**")
            st.text_area("기사 원문 (순수 텍스트)", st.session_state.sel_content, height=450)
        else:
            st.write("👈 왼쪽 리스트에서 뉴스를 클릭해 주세요.")

with tab2:
    st.subheader("🛠️ 멀티 링크 통합 초바이럴 원고 빌더")
    multi_urls = st.text_area("🔗 뉴스 링크들을 입력하세요 (한 줄에 하나씩)", value=st.session_state.get('sel_url', ''), height=150)
    
    if st.button("🚀 클로드 가공용 초벌 원고 생성", type="primary", use_container_width=True):
        if not multi_urls.strip():
            st.warning("링크를 먼저 입력해주세요.")
        else:
            with st.spinner('여러 기사를 분석하여 통합 원고 집필 중...'):
                try:
                    combined_raw = ""
                    url_list = multi_urls.split('\n')
                    for u in url_list:
                        if u.strip():
                            combined_raw += f"\n\n--- 기사내용 ---\n{get_content(u.strip())}"
                    
                    final_prompt = f"다음 뉴스 기사들을 분석해서 유튜브 대본용 1차 초벌 원고를 3,500자 이상 아주 상세하게 작성해줘:\n{combined_raw}"
                    result = model.generate_content(final_prompt)
                    st.success("✅ 완성! 이 내용을 복사해서 클로드로 가져가세요.")
                    st.code(result.text, language="markdown")
                except Exception as e:
                    st.error(f"오류가 발생했습니다: {str(e)}")
