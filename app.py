import streamlit as st
from googleapiclient.discovery import build
from youtube_transcript_api import YouTubeTranscriptApi
import pandas as pd
from datetime import datetime, timedelta
import re

# --- 1. 화면 설정 (HTML/CSS 디자인 영역) ---
st.set_page_config(layout="wide", page_title="YouTube Pro Analyzer")

st.markdown("""
<style>
    /* 전체 배경 */
    .main { background-color: #f8f9fa; }
    
    /* 카드 디자인 (HTML 스타일) */
    .video-card {
        background: white;
        border-radius: 12px;
        box-shadow: 0 4px 6px rgba(0,0,0,0.05);
        overflow: hidden;
        margin-bottom: 20px;
        border: 1px solid #e1e3e6;
        transition: transform 0.2s;
    }
    .video-card:hover { transform: translateY(-5px); box-shadow: 0 10px 15px rgba(0,0,0,0.1); }
    
    /* 썸네일 영역 */
    .thumb-wrap { position: relative; height: 180px; overflow: hidden; }
    .thumb-img { width: 100%; height: 100%; object-fit: cover; }
    
    /* 오른쪽 상단 배지 (스티커처럼 붙이기) */
    .rank-badge {
        position: absolute; top: 10px; right: 10px;
        padding: 5px 10px; border-radius: 6px;
        color: white; font-size: 0.8rem; font-weight: 800;
        text-shadow: 0 1px 2px rgba(0,0,0,0.5);
        box-shadow: 0 2px 4px rgba(0,0,0,0.3);
        z-index: 10;
        backdrop-filter: blur(2px);
    }
    .score-legendary { background: linear-gradient(135deg, #6a11cb 0%, #2575fc 100%); border: 1px solid rgba(255,255,255,0.3); }
    .score-hero { background: linear-gradient(135deg, #11998e 0%, #38ef7d 100%); border: 1px solid rgba(255,255,255,0.3); }
    .score-strong { background-color: #f39c12; }
    .score-normal { background-color: #7f8c8d; }
    
    /* 텍스트 영역 */
    .card-body { padding: 15px; }
    .card-title { font-weight: bold; font-size: 1rem; margin-bottom: 5px; line-height: 1.4; height: 44px; overflow: hidden; display: -webkit-box; -webkit-line-clamp: 2; -webkit-box-orient: vertical; }
    .card-info { font-size: 0.8rem; color: #666; margin-bottom: 3px; }
    .stat-text { font-size: 0.85rem; color: #333; font-weight: 600; }
</style>
""", unsafe_allow_html=True)

# --- 2. 파이썬 기능 영역 (로직) ---

def get_channel_stats(youtube, channel_ids):
    try:
        res = youtube.channels().list(part='statistics', id=','.join(channel_ids)).execute()
        stats = {}
        for item in res['items']:
            stats[item['id']] = int(item['statistics']['subscriberCount'])
        return stats
    except: return {}

def parse_duration(duration):
    match = re.match(r'PT(\d+H)?(\d+M)?(\d+S)?', duration)
    if not match: return 0
    hours = int(match.group(1)[:-1]) if match.group(1) else 0
    minutes = int(match.group(2)[:-1]) if match.group(2) else 0
    seconds = int(match.group(3)[:-1]) if match.group(3) else 0
    return hours * 3600 + minutes * 60 + seconds

def get_transcript(video_id):
    try:
        transcript_list = YouTubeTranscriptApi.get_transcript(video_id, languages=['ko', 'en'])
        full_text = " ".join([t['text'] for t in transcript_list])
        return full_text
    except: return None

def calculate_grade(views, subs):
    if subs == 0: return "데이터 없음", "score-normal"
    ratio = views / subs
    if ratio >= 5.0: return "전설 5.0배+", "score-legendary"
    if ratio >= 3.0: return "전설 3.0배+", "score-legendary"
    if ratio >= 2.0: return "영웅 2.0배+", "score-hero"
    if ratio >= 1.0: return "강자 1.0배+", "score-strong"
    return "평범 0.5배+", "score-normal"

# --- 3. 사이드바 (입력창) ---
with st.sidebar:
    st.title("🎥 유튜브 분석기 v11")
    st.markdown("---")
    
    api_key = st.text_input("🔑 Google API Key", type="password")
    
    st.markdown("### 🔎 검색 설정")
    keyword = st.text_input("검색어 입력", "동기부여")
    
    c1, c2 = st.columns(2)
    min_views = c1.number_input("최소 조회수", 0, step=1000)
    min_subs = c2.number_input("최소 구독자", 0, step=1000)
    
    date_opt = st.selectbox("📅 기간", ["전체", "최근 30일", "최근 3개월", "최근 1년"])
    dur_opt = st.selectbox("⏱️ 영상 길이", ["전체", "숏폼 (3분↓)", "롱폼 (3분↑)"])
    
    st.markdown("---")
    search = st.button("🚀 검색 시작", type="primary", use_container_width=True)

# --- 4. 메인 화면 ---
st.title("📊 YouTube Viral Analysis Tool")
st.markdown("파이썬의 강력함과 HTML의 디자인을 합친 하이브리드 버전입니다.")

# 상단 가이드 박스
st.markdown("""
<div style="background:white; padding:15px; border-radius:10px; border:1px solid #ddd; margin-bottom:20px;">
    <strong>🏆 성과 등급 기준 (조회수 ÷ 구독자)</strong><br>
    <span style="color:#6a11cb; font-weight:bold;">전설 (5배~)</span> | 
    <span style="color:#11998e; font-weight:bold;">영웅 (2배~)</span> | 
    <span style="color:#f39c12; font-weight:bold;">강자 (1배~)</span>
</div>
""", unsafe_allow_html=True)

if search and api_key:
    try:
        with st.spinner("데이터를 분석하고, 자막을 준비하고 있습니다..."):
            youtube = build('youtube', 'v3', developerKey=api_key)
            
            # 날짜 계산
            pub_after = None
            if date_opt != "전체":
                d = 30 if "30일" in date_opt else 90 if "3개월" in date_opt else 365
                pub_after = (datetime.now() - timedelta(days=d)).isoformat("T") + "Z"

            # 검색
            search_res = youtube.search().list(q=keyword, part='snippet', type='video', maxResults=30, publishedAfter=pub_after).execute()
            v_ids = [i['id']['videoId'] for i in search_res['items']]
            
            if not v_ids:
                st.warning("검색 결과가 없습니다.")
                st.stop()

            # 상세 정보
            v_res = youtube.videos().list(part='snippet,statistics,contentDetails', id=','.join(v_ids)).execute()
            c_ids = list(set([v['snippet']['channelId'] for v in v_res['items']]))
            c_stats = get_channel_stats(youtube, c_ids)

            results = []
            for v in v_res['items']:
                vid = v['id']
                snip = v['snippet']
                stats = v['statistics']
                
                views = int(stats.get('viewCount', 0))
                subs = c_stats.get(snip['channelId'], 0)
                dur = parse_duration(v['contentDetails']['duration'])

                # 필터링
                if views < min_views or subs < min_subs: continue
                if "숏폼" in dur_opt and dur > 180: continue
                if "롱폼" in dur_opt and dur <= 180: continue

                grade_txt, grade_cls = calculate_grade(views, subs)

                results.append({
                    "id": vid, "title": snip['title'], "thumb": snip['thumbnails']['high']['url'],
                    "channel": snip['channelTitle'], "views": views, "subs": subs,
                    "date": snip['publishedAt'][:10], "grade_txt": grade_txt, "grade_cls": grade_cls
                })

            st.success(f"검색 결과: {len(results)}건")

            # ★ HTML+CSS로 카드 그리기 ★
            cols = st.columns(3)
            for idx, item in enumerate(results):
                with cols[idx % 3]:
                    # HTML 코드 생성
                    html_code = f"""
                    <div class="video-card">
                        <div class="thumb-wrap">
                            <img src="{item['thumb']}" class="thumb-img">
                            <span class="rank-badge {item['grade_cls']}">{item['grade_txt']}</span>
                        </div>
                        <div class="card-body">
                            <div class="card-title" title="{item['title']}">{item['title']}</div>
                            <div class="card-info">{item['channel']} | 구독자 {item['subs']:,}</div>
                            <div class="stat-text">조회수 {item['views']:,}회 | {item['date']}</div>
                        </div>
                    </div>
                    """
                    st.markdown(html_code, unsafe_allow_html=True)
                    
                    # 파이썬 기능 버튼
                    with st.expander("🛠️ 분석 도구"):
                        if st.button("📜 대본 보기", key=f"s_{item['id']}"):
                            s = get_transcript(item['id'])
                            if s: st.text_area("자막 내용", s, height=200)
                            else: st.error("자막이 없거나 추출 실패")
                        
                        if st.button("⚡ 정밀 분석", key=f"p_{item['id']}"):
                            s = get_transcript(item['id'])
                            ai_script = s[:15000] if s else "(자막 없음)"
                            prompt = f"""
# Role: 유튜브 분석 전문가
# Task: '{item['title']}' 영상 정밀 분석

[영상 정보]
URL: https://youtu.be/{item['id']}
썸네일: {item['thumb']}
성과: {item['grade_txt']}

[자막(Script)]
\"\"\"
{ai_script}...
\"\"\"

[분석 요청]
1. [Vision] 썸네일 & 오프닝 일치성
2. [Script] 감정의 방아쇠 & 논리 구조
3. [Retention] 이탈 방지 장치
4. 🔥 [Killer Moment] 시청자 집착 구간 추적
5. [Action Plan] 벤치마킹 적용 공식
                            """
                            st.code(prompt)
                            st.info("위 내용을 복사해서 Gemini에 붙여넣으세요.")

    except Exception as e:
        st.error(f"오류가 발생했습니다: {e}")
