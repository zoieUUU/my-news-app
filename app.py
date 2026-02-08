import streamlit as st
import requests
from bs4 import BeautifulSoup
import google.generativeai as genai

# 1. AI 엔진 설정 (가장 안전한 모델 호출 방식)
try:
    genai.configure(api_key=st.secrets["GOOGLE_API_KEY"])
    # 'models/'를 빼고 라이브러리가 알아서 찾도록 설정
    model = genai.GenerativeModel('gemini-1.5-flash')
except Exception as e:
    st.error(f"API 설정 오류: {e}")

st.set_page_config(page_title="VIRAL RANKING MASTER", layout="wide")

# --- 뉴스 수집 함수 (헤더 보강으로 차단 방지) ---
@st.cache_data(ttl=600)
def get_viral_top_100():
    url = "https://news.naver.com/main/ranking/popularDay.naver"
    headers = {
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/110.0.0.0 Safari/537.36"
    }
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

    # TOP 5 소재 선별
    try:
        titles_list = "\n".join([f"{i}. {d['title']}" for i, d in enumerate(unique_news[:40])])
        prompt = f"유튜브 조회수 대박날 소재 5개의 번호만 골라줘(쉼표 구분): {titles_list}"
        resp = model.generate_content(prompt)
        s_indices = [int(x.strip()) for x in resp.text.split(',') if x.strip().isdigit()]
    except:
        s_indices = [0, 1, 2, 3, 4]
    
    for i, item in enumerate(unique_news):
        item['is_s'] = i in s_indices
    return sorted(unique_news, key=lambda x: x['is_s'], reverse=True)

# --- AI 분석 함수 (네이버 차단 우회 및 태그 정밀화) ---
def get_ai_analysis(url):
    try:
        # 헤더에 Referer 추가 (네이버 차단 우회 핵심)
        headers = {
            "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/110.0.0.0 Safari/537.36",
            "Referer": "https://news.naver.com/"
        }
        res = requests.get(url, headers=headers, timeout=10)
        soup = BeautifulSoup(res.text, 'html.parser')
        
        # 네이버 뉴스 최신 본문 태그 순위별 수집
        content = soup.select_one('#dic_area') or \
                  soup.select_one('#newsct_article') or \
                  soup.select_one('#articleBodyContents') or \
                  soup.select_one('article')
        
        if not content:
            return "본문을 찾을 수 없습니다. (비로그인 제한 또는 특수 기사)", "분석 실패"
            
        text = content.get_text(separator="\n", strip=True)
        
        # AI 요약
        analysis_prompt = f"다음 뉴스를 [요약 2줄], [키워드 5개]로 분석해줘:\n\n{text[:2000]}"
        resp = model.generate_content(analysis_prompt)
        return text, resp.text
    except Exception as e:
        return f"연결 에러: {str(e)}", "분석 실패"

# --- 화면 구성 ---
st.title("🔥 VIRAL RANKING MASTER")
st.markdown("### 🚀 실시간 통합 랭킹 : AI 선정 바이럴 S-CLASS")

l, r = st.columns([1, 1.2])

with l:
    if st.button("🔄 리스트 새로고침"):
        st.cache_data.clear()
        st.rerun()
    
    data = get_viral_top_100()
    
    for i, row in enumerate(data):
        if row['is_s']:
            st.markdown(f"""
                <div style="background-color: #FFD700; padding: 5px 10px; border-radius: 5px; border: 2px solid #FF8C00; margin-bottom: -10px;">
                    <b style="color: black; font-size: 13px;">👑 AI S-CLASS 바이럴 추천</b>
                </div>
            """, unsafe_allow_html=True)
            if st.button(f"🔥 {row['title']}", key=f"s_{i}", use_container_width=True):
                with st.spinner('분석 중...'):
                    t, a = get_ai_analysis(row['link'])
                    st.session_state.cur_title, st.session_state.cur_text, st.session_state.cur_analysis = row['title'], t, a
            st.write("")
        else:
            if st.button(f"[{i+1}] {row['title']}", key=f"n_{i}", use_container_width=True):
                with st.spinner('분석 중...'):
                    t, a = get_ai_analysis(row['link'])
                    st.session_state.cur_title, st.session_state.cur_text, st.session_state.cur_analysis = row['title'], t, a

with r:
    st.subheader("📄 AI 분석 리포트")
    if 'cur_title' in st.session_state:
        st.markdown("#### 💡 핵심 요약 및 키워드")
        # 분석 실패 시 에러 문구 대신 가이드 출력
        if "분석 실패" in st.session_state.cur_analysis:
            st.error("⚠️ AI가 본문을 읽지 못했습니다. 기사 원문을 직접 확인해주세요.")
        else:
            st.success(st.session_state.cur_analysis)
        
        st.divider()
        st.info(f"**제목: {st.session_state.cur_title}**")
        st.text_area("기사 본문", st.session_state.cur_text, height=500)
    else:
        st.info("👈 왼쪽에서 뉴스를 선택하세요.")
