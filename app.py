import streamlit as st
import requests
from bs4 import BeautifulSoup
import google.generativeai as genai

# 1. AI 엔진 설정
try:
    genai.configure(api_key=st.secrets["GOOGLE_API_KEY"])
    model = genai.GenerativeModel('gemini-1.5-flash')
except:
    st.error("Secrets에서 API 키를 확인해주세요.")

st.set_page_config(page_title="VIRAL RANKING MASTER", layout="wide")

# --- 뉴스 수집 및 AI 바이럴 랭킹 선정 ---
@st.cache_data(ttl=600)
def get_viral_top_100():
    url = "https://news.naver.com/main/ranking/popularDay.naver"
    headers = {"User-Agent": "Mozilla/5.0"}
    res = requests.get(url, headers=headers)
    soup = BeautifulSoup(res.text, 'html.parser')
    
    unique_news = []
    seen_titles = set()
    for box in soup.select('.rankingnews_box'):
        for li in box.select('.rankingnews_list li'):
            a_tag = li.select_one('a')
            if a_tag:
                title = a_tag.text.strip()
                if title not in seen_titles:
                    unique_news.append({"title": title, "link": a_tag['href']})
                    seen_titles.add(title)

    # AI에게 TOP 5 선정 요청
    titles_list = "\n".join([f"{i}. {d['title']}" for i, d in enumerate(unique_news[:40])])
    prompt = f"유튜브 조회수 대박날 소재 5개의 번호만 골라줘(쉼표 구분): {titles_list}"
    
    try:
        resp = model.generate_content(prompt)
        s_indices = [int(x.strip()) for x in resp.text.split(',') if x.strip().isdigit()]
    except:
        s_indices = [0, 1, 2, 3, 4] # 에러 시 상위 5개 강제 지정
    
    for i, item in enumerate(unique_news):
        item['is_s'] = i in s_indices
    return sorted(unique_news, key=lambda x: x['is_s'], reverse=True)

# --- 분석 강화 함수 ---
def get_ai_analysis(url):
    try:
        res = requests.get(url, headers={"User-Agent": "Mozilla/5.0"})
        soup = BeautifulSoup(res.text, 'html.parser')
        # 다양한 뉴스 본문 태그 대응
        content = soup.select_one('#newsct_article') or soup.select_one('#articleBodyContents') or soup.select_one('.article_body')
        text = content.text.strip() if content else ""
        
        if len(text) > 100:
            analysis_prompt = f"다음 뉴스를 [요약: 2줄], [키워드: 중요도순 5개] 양식으로 분석해줘:\n\n{text[:1500]}"
            resp = model.generate_content(analysis_prompt)
            return text, resp.text
        return "본문을 가져오는 데 실패했습니다. 링크를 직접 확인하세요.", "분석 실패"
    except Exception as e:
        return f"에러 발생: {e}", "분석 실패"

# --- 화면 구성 ---
st.title("🔥 VIRAL RANKING MASTER")
st.markdown("### 🚀 AI 선정 바이럴 S-CLASS 리스트")

l, r = st.columns([1, 1.2])

with l:
    if st.button("🔄 전체 랭킹 새로고침"):
        st.cache_data.clear()
        st.rerun()
    
    data = get_viral_top_100()
    
    for i, row in enumerate(data):
        if row['is_s']:
            # [해결책] 버튼이 배경색을 먹어버리므로, 버튼 주변에 노란색 테두리와 배경을 가진 컨테이너 사용
            with st.container():
                st.markdown(f"""
                    <div style="background-color: #FFD700; padding: 5px 10px; border-radius: 5px 5px 0 0; border: 2px solid #FF8C00; border-bottom: none;">
                        <b style="color: black; font-size: 14px;">👑 AI S-CLASS 바이럴 추천</b>
                    </div>
                """, unsafe_allow_html=True)
                if st.button(f"🔥 {row['title']}", key=f"s_{i}", use_container_width=True):
                    with st.spinner('분석 중...'):
                        st.session_state.t, st.session_state.a = get_ai_analysis(row['link'])
                        st.session_state.title = row['title']
                        st.session_state.is_s = True
                st.markdown("<div style='margin-bottom: 15px;'></div>", unsafe_allow_html=True)
        else:
            if st.button(f"[{i+1}] {row['title']}", key=f"n_{i}", use_container_width=True):
                with st.spinner('분석 중...'):
                    st.session_state.t, st.session_state.a = get_ai_analysis(row['link'])
                    st.session_state.title = row['title']
                    st.session_state.is_s = False

with r:
    st.subheader("📄 AI 인사이트 및 원문")
    if 'title' in st.session_state:
        # 분석 결과 표시
        st.markdown("#### 💡 AI 핵심 요약 & 키워드")
        st.success(st.session_state.a)
        
        st.divider()
        st.info(f"**제목: {st.session_state.title}**")
        st.text_area("뉴스 전문", st.session_state.t, height=500)
    else:
        st.info("👈 왼쪽 리스트에서 분석할 뉴스를 선택해 주세요.")
