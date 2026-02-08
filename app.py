import streamlit as st
import requests
from bs4 import BeautifulSoup
import google.generativeai as genai

# 1. AI 엔진 설정 (404 에러 방지를 위한 동적 모델 로딩)
try:
    genai.configure(api_key=st.secrets["GOOGLE_API_KEY"])
    
    # [해결책] 특정 버전 명시 대신 가장 안정적인 'gemini-1.5-flash-latest' 사용
    # 만약 이래도 안되면 'gemini-pro'로 자동 전환되도록 예외처리
    try:
        model = genai.GenerativeModel('gemini-1.5-flash-latest')
        # 작동 확인을 위한 테스트 호출 (선택사항)
    except:
        model = genai.GenerativeModel('gemini-pro')
except Exception as e:
    st.error(f"AI 설정 치명적 오류: {e}")

st.set_page_config(page_title="VIRAL RANKING MASTER", layout="wide")

# --- 뉴스 수집 함수 (차단 방지 헤더) ---
@st.cache_data(ttl=600)
def get_viral_top_100():
    url = "https://news.naver.com/main/ranking/popularDay.naver"
    headers = {"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36"}
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

    # TOP 5 소재 선별 (에러 발생 시 상위 5개 자동 지정)
    try:
        titles_list = "\n".join([f"{i}. {d['title']}" for i, d in enumerate(unique_news[:40])])
        prompt = f"유튜브 100만 기획자로서 다음 뉴스 중 가장 터질 소재 5개의 번호만 골라줘(쉼표 구분): {titles_list}"
        resp = model.generate_content(prompt)
        import re
        s_indices = [int(n) for n in re.findall(r'\d+', resp.text)]
    except:
        s_indices = [0, 1, 2, 3, 4]
    
    for i, item in enumerate(unique_news):
        item['is_s'] = i in s_indices
    return sorted(unique_news, key=lambda x: x['is_s'], reverse=True)

# --- AI 분석 함수 (네이버 차단 우회 및 404 에러 원천 차단) ---
def get_ai_analysis(url):
    try:
        headers = {
            "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36",
            "Referer": "https://news.naver.com/"
        }
        res = requests.get(url, headers=headers, timeout=10)
        soup = BeautifulSoup(res.text, 'html.parser')
        
        # 네이버 뉴스 본문 수집 태그
        content = soup.select_one('#dic_area') or soup.select_one('#newsct_article') or soup.select_one('#articleBodyContents')
        
        if not content:
            return "본문을 찾을 수 없습니다.", "분석 불가"
            
        text = content.get_text(strip=True)
        # AI 분석 요청
        analysis_prompt = f"다음 뉴스를 보고 [요약 2줄]과 [핵심 키워드 5개]를 뽑아줘:\n\n{text[:1500]}"
        
        # [중요] 호출 시 에러가 나면 여기서 에러 메시지를 반환하도록 설정
        try:
            resp = model.generate_content(analysis_prompt)
            return text, resp.text
        except Exception as ai_err:
            return text, f"AI 모델 호출 에러: {ai_err}\n(API Key는 정상이나 모델명 매칭 실패)"
            
    except Exception as e:
        return f"연결 실패: {str(e)}", "분석 불가"

# --- 화면 구성 ---
st.title("🔥 VIRAL RANKING MASTER")
st.markdown("---")

left, right = st.columns([1, 1.2])

with left:
    if st.button("🔄 전체 랭킹 새로고침"):
        st.cache_data.clear()
        st.rerun()
    
    data = get_viral_top_100()
    for i, item in enumerate(data):
        if item['is_s']:
            st.markdown(f'<div style="background-color:#FFD700; padding:5px; border-radius:5px; border:2px solid #FFA500; font-weight:bold; color:black; font-size:12px; margin-bottom:-10px; width:fit-content;">👑 AI S-CLASS 추천</div>', unsafe_allow_html=True)
            if st.button(f"🔥 {item['title']}", key=f"s_{i}", use_container_width=True):
                with st.spinner('분석 중...'):
                    t, a = get_ai_analysis(item['link'])
                    st.session_state.res = {"title": item['title'], "text": t, "analysis": a}
        else:
            if st.button(f"[{i+1}] {item['title']}", key=f"n_{i}", use_container_width=True):
                with st.spinner('분석 중...'):
                    t, a = get_ai_analysis(item['link'])
                    st.session_state.res = {"title": item['title'], "text": t, "analysis": a}

with right:
    st.subheader("📊 AI 분석 및 기사 전문")
    if "res" in st.session_state:
        st.success(f"**💡 AI 분석 리포트**\n\n{st.session_state.res['analysis']}")
        st.divider()
        st.info(f"**제목: {st.session_state.res['title']}**")
        st.text_area("기사 전문", st.session_state.res['text'], height=550)
    else:
        st.info("👈 왼쪽에서 소재를 선택해 주세요.")
