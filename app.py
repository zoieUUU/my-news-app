import streamlit as st
import requests
from bs4 import BeautifulSoup
import google.generativeai as genai

# 1. AI 엔진 설정 (보안 강화)
try:
    genai.configure(api_key=st.secrets["GOOGLE_API_KEY"])
    model = genai.GenerativeModel('gemini-1.5-flash')
except:
    st.error("Streamlit Cloud 설정에서 GOOGLE_API_KEY를 확인해주세요.")

st.set_page_config(page_title="유메이커 MASTER", layout="wide")

# --- 뉴스 수집 및 S급 선별 함수 (로직 강화) ---
@st.cache_data(ttl=600)
def get_ranked_news():
    url = "https://news.naver.com/main/ranking/popularDay.naver"
    headers = {"User-Agent": "Mozilla/5.0"}
    res = requests.get(url, headers=headers)
    soup = BeautifulSoup(res.text, 'html.parser')
    
    raw_data = []
    # 랭킹 뉴스 박스에서 데이터 수집
    for box in soup.select('.rankingnews_box')[:12]:
        press = box.select_one('.rankingnews_name').text.strip()
        for li in box.select('.rankingnews_list li')[:5]:
            a_tag = li.select_one('a')
            if a_tag:
                raw_data.append({"언론사": press, "제목": a_tag.text.strip(), "링크": a_tag['href']})
    
    # [개선] AI에게 번호가 아닌 '핵심 키워드'를 뽑게 하여 정확도 향상
    titles_block = "\n".join([f"- {d['제목']}" for d in raw_data[:50]]) # 상위 50개 집중 분석
    pick_prompt = f"""
    너는 100만 유튜브 채널 '유메이커'의 메인 피디다. 
    다음 뉴스 제목들 중 시청자 클릭률(CTR)이 가장 높을 것 같은 'S급 소재' 5개를 선정해라.
    결과는 반드시 선정된 뉴스 제목과 똑같이 한 줄에 하나씩만 써라. 
    불필요한 설명은 하지 마라.
    
    [뉴스 리스트]
    {titles_block}
    """
    try:
        resp = model.generate_content(pick_prompt)
        s_titles = resp.text.split('\n')
        # 수집된 리스트와 AI가 고른 제목 매칭
        for d in raw_data:
            d['is_s'] = any(stitle.strip() in d['제목'] for stitle in s_titles if stitle.strip())
    except:
        for d in raw_data: d['is_s'] = False
        
    return raw_data

def get_content(url):
    try:
        res = requests.get(url, headers={"User-Agent": "Mozilla/5.0"})
        soup = BeautifulSoup(res.text, 'html.parser')
        content = soup.select_one('#newsct_article') or soup.select_one('#articleBodyContents')
        return content.text.strip() if content else "본문을 가져올 수 없습니다."
    except: return "연결 실패"

# --- 메인 화면 레이아웃 ---
st.title("🚀 유메이커 MASTER : S급 선별 및 초벌 빌더")
tab1, tab2 = st.tabs(["📊 1단계: S급 선별 및 본문 확인", "✍️ 2단계: 멀티 링크 초벌 원고"])

with tab1:
    l_col, r_col = st.columns([1, 1.2])
    
    with l_col:
        st.subheader("🔥 실시간 랭킹 (AI S급 필터)")
        news_list = get_ranked_news()
        
        # S급을 리스트 최상단으로 정렬하여 배치
        sorted_list = sorted(news_list, key=lambda x: x['is_s'], reverse=True)
        
        for i, row in enumerate(sorted_list):
            # S급은 버튼 스타일과 아이콘으로 강조
            if row['is_s']:
                btn_label = f"🔥 [S급 유력] {row['제목']}"
                btn_type = "secondary" # 스트림릿 특성상 색상 직접 지정은 제한적이나 아이콘으로 구분
            else:
                btn_label = f"{row['제목']}"
                btn_type = "secondary"
                
            if st.button(f"[{row['언론사']}] {btn_label}", key=f"news_{i}", use_container_width=True):
                st.session_state.sel_title = row['제목']
                st.session_state.sel_url = row['링크']
                st.session_state.sel_content = get_content(row['링크'])
                st.session_state.is_s = row['is_s']

    with r_col:
        if 'sel_title' in st.session_state:
            st.subheader("📄 뉴스 원문 확인")
            if st.session_state.is_s:
                st.error(f"🎯 AI 분석 결과: 이 뉴스({st.session_state.sel_title})는 대박 소재입니다!")
            
            st.info(f"**{st.session_state.sel_title}**")
            st.text_area("기사 내용 (복사 가능)", st.session_state.sel_content, height=450)
            st.caption("내용이 마음에 든다면 '2단계' 탭으로 이동하세요.")
        else:
            st.write("👈 왼쪽에서 뉴스 소재를 클릭하면 원문이 여기에 나타납니다.")

with tab2:
    st.subheader("🛠️ 초바이럴 1차 원고 생성 (통합 가공)")
    st.write("선택된 뉴스 외에도 관련된 다른 기사 링크를 추가하면 AI가 하나로 합쳐서 클로드용 초벌 원고를 씁니다.")
    
    # 여러 링크 입력창
    multi_urls = st.text_area("🔗 뉴스 링크 입력 (한 줄에 하나씩)", 
                              value=st.session_state.get('sel_url', ''), height=150)
    
    if st.button("🚀 클로드용 초벌 원고 집필 시작", type="primary", use_container_width=True):
        with st.spinner('여러 기사의 데이터를 분석하고 3,500자 분량의 뼈대를 잡는 중...'):
            combined_raw = ""
            urls = multi_urls.split('\n')
            for u in urls:
                if u.strip():
                    combined_raw += f"\n\n--- 기사내용 ---\n{get_content(u.strip())}"
            
            final_prompt = f"""
            너는 100만 유튜버의 전문 시나리오 작가다. 다음 통합 뉴스 데이터를 바탕으로 
            나중에 클로드(Claude)에서 2차 가공할 '초바이럴 1차 원고'를 작성하라.

            [통합 데이터]
            {combined_raw}

            [작성 지침]
            1. 분량: 최소 3,000자 이상의 정보량을 확보할 것.
            2. 도입부(0~25초): 시청자의 뒤통수를 때리는 듯한 충격적인 팩트와 의문 제기.
            3. 전개: 기사 {len(urls)}개의 내용을 교차 검증하여 사건의 입체적인 전개를 서술할 것.
            4. 타겟: 2030 남성이 분노하거나 열광할 포인트를 짚을 것.
            5. 결론: 클로드에서 감정적인 말투로 덮어씌우기 좋게 '팩트 덩어리' 형태로 전달할 것.
            """
            result = model.generate_content(final_prompt)
            st.success("✅ 초벌 원고가 완성되었습니다! 아래 코드를 복사해서 클로드에 붙여넣으세요.")
            st.code(result.text, language="markdown")
