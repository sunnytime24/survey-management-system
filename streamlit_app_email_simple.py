import streamlit as st
import pandas as pd
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
import os
from dotenv import load_dotenv
import time
import gspread
from oauth2client.service_account import ServiceAccountCredentials
import re
from google.oauth2.credentials import Credentials
from google_auth_oauthlib.flow import InstalledAppFlow
from google.auth.transport.requests import Request
from googleapiclient.discovery import build
import pickle
import base64
import json
import datetime
from urllib.parse import urlencode
from openai import OpenAI
import plotly.express as px
import plotly.graph_objects as go

# 페이지 설정
st.set_page_config(
    page_title="Survey Management System",
    page_icon="��",
    layout="wide",
    initial_sidebar_state="expanded"
)

# 환경 변수 로드
load_dotenv()

# OpenAI API 키 설정
OPENAI_API_KEY = os.getenv('OPENAI_API_KEY')
if OPENAI_API_KEY:
    client = OpenAI(api_key=OPENAI_API_KEY)
else:
    client = None

# Gmail API 스코프 설정
SCOPES = [
    'https://www.googleapis.com/auth/gmail.send',
    'https://www.googleapis.com/auth/spreadsheets',
    'https://www.googleapis.com/auth/drive.file'
]

# Gmail API 서비스 초기화
if 'gmail_service' not in st.session_state:
    st.session_state.gmail_service = None

# Google Sheets 관리 상태 초기화
if 'survey_sheets' not in st.session_state:
    st.session_state.survey_sheets = []

# 구글 시트 ID 추출 함수
def extract_sheet_id(url):
    """URL에서 Google Sheet ID를 추출합니다."""
    pattern = r'/d/([a-zA-Z0-9-_]+)'
    match = re.search(pattern, url)
    if match:
        return match.group(1)
    return None

@st.cache_resource
def get_gspread_client():
    """Google Sheets API 클라이언트를 생성합니다."""
    scope = ['https://spreadsheets.google.com/feeds',
             'https://www.googleapis.com/auth/drive']
    
    try:
        # 서비스 계정 JSON 파일이 있는지 확인
        if not os.path.exists('service_account.json'):
            st.error("서비스 계정 JSON 파일(service_account.json)이 없습니다.")
            return None
            
        creds = ServiceAccountCredentials.from_json_keyfile_name('service_account.json', scope)
        client = gspread.authorize(creds)
        return client
    except Exception as e:
        st.error(f"Google Sheets API 연결 오류: {str(e)}")
        return None

@st.cache_data(ttl=60)  # 1분 캐시
def load_sheet_data(student_sheet_url, survey_sheet_url):
    """Google Sheets에서 데이터를 로드합니다."""
    client = get_gspread_client()
    if not client:
        return None, None
    
    try:
        # 교육생 명단 로드
        student_sheet_id = extract_sheet_id(student_sheet_url)
        if not student_sheet_id:
            st.error("올바른 교육생 명단 스프레드시트 URL이 아닙니다.")
            return None, None
            
        student_sheet = client.open_by_key(student_sheet_id).sheet1
        students_data = student_sheet.get_all_records()
        df_students = pd.DataFrame(students_data)
        
        # 만족도 조사 응답 로드
        survey_sheet_id = extract_sheet_id(survey_sheet_url)
        if not survey_sheet_id:
            st.error("올바른 만족도 조사 스프레드시트 URL이 아닙니다.")
            return None, None
            
        survey_sheet = client.open_by_key(survey_sheet_id).sheet1
        survey_data = survey_sheet.get_all_records()
        df_survey = pd.DataFrame(survey_data)
        
        return df_students, df_survey
    
    except Exception as e:
        st.error(f"스프레드시트 로드 중 오류 발생: {str(e)}")
        return None, None

# 샘플 데이터 로드 함수 (백업용)
def load_sample_data():
    """샘플 데이터를 로드합니다."""
    
    # 샘플 교육생 데이터
    students_data = [
        {"이름": "교육생1", "소속": "전략기획팀", "이메일": "user1@example.com", "연락처": "010-8331-1308"},
        {"이름": "교육생2", "소속": "전략기획팀", "이메일": "sunnytime24@gmail.com", "연락처": "010-9563-3125"},
        {"이름": "교육생3", "소속": "구매팀", "이메일": "user3@example.com", "연락처": "010-9350-2780"},
        {"이름": "교육생4", "소속": "전략기획팀", "이메일": "user4@example.com", "연락처": "010-6275-4126"},
        {"이름": "교육생5", "소속": "회사1", "이메일": "user5@example.com", "연락처": "010-1382-5301"},
        {"이름": "교육생6", "소속": "법무팀", "이메일": "user6@example.com", "연락처": "010-9910-8739"},
        {"이름": "교육생7", "소속": "구매팀", "이메일": "user7@example.com", "연락처": "010-7800-4733"},
        {"이름": "교육생8", "소속": "회사1", "이메일": "user8@example.com", "연락처": "010-6349-9767"},
        {"이름": "교육생9", "소속": "법무팀", "이메일": "user9@example.com", "연락처": "010-1311-6644"},
        {"이름": "교육생10", "소속": "법무팀", "이메일": "user10@example.com", "연락처": "010-4992-9611"},
        {"이름": "교육생11", "소속": "정보보안팀", "이메일": "user11@example.com", "연락처": "010-2618-9745"},
        {"이름": "교육생12", "소속": "법무팀", "이메일": "user12@example.com", "연락처": "010-6257-9839"},
        {"이름": "교육생13", "소속": "재무회계팀", "이메일": "user13@example.com", "연락처": "010-7603-7713"},
        {"이름": "교육생14", "소속": "법무팀", "이메일": "user14@example.com", "연락처": "010-2439-3183"},
        {"이름": "교육생15", "소속": "정보보안팀", "이메일": "user15@example.com", "연락처": "010-7457-7268"},
        {"이름": "교육생16", "소속": "회사1", "이메일": "user16@example.com", "연락처": "010-4238-5960"},
        {"이름": "교육생17", "소속": "재무회계팀", "이메일": "user17@example.com", "연락처": "010-8558-9000"},
        {"이름": "교육생18", "소속": "연구개발팀", "이메일": "user18@example.com", "연락처": "010-9612-4187"},
        {"이름": "교육생19", "소속": "구매팀", "이메일": "user19@example.com", "연락처": "010-6943-4785"},
        {"이름": "교육생20", "소속": "정보보안팀", "이메일": "user20@example.com", "연락처": "010-7820-3246"},
        {"이름": "교육생21", "소속": "마케팅팀", "이메일": "user21@example.com", "연락처": "010-2203-3160"},
        {"이름": "교육생22", "소속": "마케팅팀", "이메일": "user22@example.com", "연락처": "010-3715-6289"},
        {"이름": "교육생23", "소속": "구매팀", "이메일": "user23@example.com", "연락처": "010-6234-1583"},
        {"이름": "교육생24", "소속": "연구개발팀", "이메일": "user24@example.com", "연락처": "010-1207-4617"},
        {"이름": "교육생25", "소속": "구매팀", "이메일": "user25@example.com", "연락처": "010-8604-8783"},
        {"이름": "교육생26", "소속": "연구개발팀", "이메일": "user26@example.com", "연락처": "010-7911-5348"},
        {"이름": "교육생27", "소속": "마케팅팀", "이메일": "user27@example.com", "연락처": "010-3842-8761"},
        {"이름": "교육생28", "소속": "마케팅팀", "이메일": "user28@example.com", "연락처": "010-5927-3084"},
        {"이름": "교육생29", "소속": "연구개발팀", "이메일": "user29@example.com", "연락처": "010-9476-2158"},
        {"이름": "교육생30", "소속": "정보보안팀", "이메일": "user30@example.com", "연락처": "010-8342-6719"},
    ]
    
    # 샘플 응답 데이터
    survey_data = [
        {"이름": "교육생1", "소속": "전략기획팀", "이메일": "user1@example.com", "만족도": "매우 만족"},
        {"이름": "교육생3", "소속": "구매팀", "이메일": "user3@example.com", "만족도": "만족"},
        {"이름": "교육생5", "소속": "회사1", "이메일": "user5@example.com", "만족도": "보통"},
        {"이름": "교육생7", "소속": "구매팀", "이메일": "user7@example.com", "만족도": "만족"},
        {"이름": "교육생9", "소속": "법무팀", "이메일": "user9@example.com", "만족도": "불만족"},
        {"이름": "교육생11", "소속": "정보보안팀", "이메일": "user11@example.com", "만족도": "매우 만족"},
        {"이름": "교육생13", "소속": "재무회계팀", "이메일": "user13@example.com", "만족도": "만족"},
        {"이름": "교육생15", "소속": "정보보안팀", "이메일": "user15@example.com", "만족도": "보통"},
        {"이름": "교육생17", "소속": "재무회계팀", "이메일": "user17@example.com", "만족도": "매우 만족"},
        {"이름": "교육생19", "소속": "구매팀", "이메일": "user19@example.com", "만족도": "만족"},
        {"이름": "교육생21", "소속": "마케팅팀", "이메일": "user21@example.com", "만족도": "매우 불만족"},
        {"이름": "교육생23", "소속": "구매팀", "이메일": "user23@example.com", "만족도": "보통"},
        {"이름": "교육생25", "소속": "구매팀", "이메일": "user25@example.com", "만족도": "만족"},
        {"이름": "교육생27", "소속": "마케팅팀", "이메일": "user27@example.com", "만족도": "보통"},
        {"이름": "교육생29", "소속": "연구개발팀", "이메일": "user29@example.com", "만족도": "매우 만족"},
    ]
    
    df_students = pd.DataFrame(students_data)
    df_survey = pd.DataFrame(survey_data)
    
    return df_students, df_survey

def find_non_respondents(df_students, df_survey):
    """미응답자 목록을 찾습니다."""
    if df_students is None or df_survey is None:
        return pd.DataFrame()
    
    # 응답자 이메일 목록
    respondent_emails = set(df_survey['이메일'].dropna())
    
    # 전체 교육생 이메일 목록
    student_emails = set(df_students['이메일'].dropna())
    
    # 미응답자 찾기
    non_respondent_emails = student_emails - respondent_emails
    
    # 미응답자 정보 가져오기
    non_respondents = df_students[df_students['이메일'].isin(non_respondent_emails)]
    
    return non_respondents

def get_gmail_service():
    """Gmail API 서비스 객체를 생성합니다."""
    creds = None
    
    if os.path.exists('token.pickle'):
        with open('token.pickle', 'rb') as token:
            creds = pickle.load(token)
    
    if not creds or not creds.valid:
        if creds and creds.expired and creds.refresh_token:
            creds.refresh(Request())
        else:
            if not os.path.exists('credentials.json'):
                st.error("""
                    ### Google Cloud Console 설정이 필요합니다
                    
                    1. [Google Cloud Console](https://console.cloud.google.com)에서 새 프로젝트를 생성하세요.
                    2. Gmail API와 Google Sheets API를 활성화하세요.
                    3. OAuth 동의 화면을 구성하세요:
                       - 사용자 유형: 외부
                       - 필요한 범위 추가: Gmail API, Google Sheets API
                    4. 사용자 인증 정보 → OAuth 2.0 클라이언트 ID 만들기:
                       - 애플리케이션 유형: 데스크톱 앱
                       - credentials.json 파일을 다운로드하여 프로젝트 루트에 저장하세요.
                    5. OAuth 동의 화면 → 테스트 사용자에 본인의 Google 계정을 추가하세요.
                """)
                return None
                
            flow = InstalledAppFlow.from_client_secrets_file(
                'credentials.json', SCOPES)
            
            try:
                creds = flow.run_local_server(port=0)  # 자동으로 사용 가능한 포트 할당
                st.success("✅ Google 계정 인증이 완료되었습니다!")
            except Exception as e:
                st.error(f"인증 과정에서 오류가 발생했습니다: {str(e)}")
                return None
            
        # 인증 정보 저장
        with open('token.pickle', 'wb') as token:
            pickle.dump(creds, token)
    
    try:
        service = build('gmail', 'v1', credentials=creds)
        return service
    except Exception as e:
        st.error(f"Gmail API 서비스 생성 실패: {str(e)}")
        return None

def get_survey_url(base_url):
    """설문 URL을 생성합니다."""
    return f"{base_url}?page=survey"

def create_satisfaction_survey():
    """만족도 조사 URL을 생성합니다."""
    base_url = st.query_params.get('base_url', [None])[0]
    if not base_url:
        base_url = "http://localhost:8501"
    survey_url = get_survey_url(base_url)
    return survey_url

def save_survey_response(response_data):
    """설문 응답을 Google Sheets에 저장합니다."""
    try:
        client = get_gspread_client()
        if not client:
            return False
            
        # 응답 시트가 없으면 생성
        try:
            sheet = client.open("교육 만족도 조사 응답").sheet1
        except:
            sheet = client.create("교육 만족도 조사 응답").sheet1
            # 헤더 추가
            sheet.append_row(["이름", "소속", "이메일", "만족도", "의견", "제출일시"])
        
        # 응답 저장
        sheet.append_row([
            response_data["이름"],
            response_data["소속"],
            response_data["이메일"],
            response_data["만족도"],
            response_data.get("의견", ""),
            datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        ])
        return True
    except Exception as e:
        st.error(f"응답 저장 중 오류 발생: {str(e)}")
        return False

def send_reminder_email(name, email, survey_url):
    """리마인더 이메일을 발송합니다."""
    try:
        service = get_gmail_service()
        if not service:
            return False

        # 이메일 내용 생성
        subject = f"[리마인더] {name}님, 만족도 조사에 참여해주세요"
        body = f"""안녕하세요, {name}님

아직 만족도 조사에 응답하지 않으신 것 같아 안내 드립니다.
아래 링크를 통해 만족도 조사에 참여해주시면 감사하겠습니다.

📝 만족도 조사 링크: {survey_url}

귀중한 의견 부탁드립니다.
감사합니다."""

        # 이메일 메시지 생성
        message = MIMEMultipart()
        message['to'] = email
        message['subject'] = subject
        message.attach(MIMEText(body, 'plain'))
        raw_message = base64.urlsafe_b64encode(message.as_bytes()).decode('utf-8')

        try:
            service.users().messages().send(
                userId='me',
                body={'raw': raw_message}
            ).execute()
            return True
        except Exception as e:
            st.error(f"이메일 발송 실패: {str(e)}")
            return False

    except Exception as e:
        st.error(f"리마인더 이메일 처리 중 오류 발생: {str(e)}")
        return False

def generate_survey_questions(target, purpose, requirements):
    """OpenAI를 사용하여 Survey 문항을 생성합니다."""
    if not client:
        st.error("""
            ### OpenAI API 키가 필요합니다
            1. OpenAI API 키를 발급받으세요.
            2. `.env` 파일에 다음과 같이 설정하세요:
            ```
            OPENAI_API_KEY=your-api-key-here
            ```
        """)
        return None
    
    try:
        # OpenAI API 호출
        prompt = f"""
        다음 조건에 맞는 설문조사 문항을 생성해주세요:

        대상: {target}
        목적: {purpose}
        필수 포함 항목: {requirements}

        다음 형식으로 JSON 응답을 생성해주세요:
        {{
            "title": "설문 제목",
            "description": "설문 설명",
            "questions": [
                {{
                    "type": "text/radio/checkbox/textarea",
                    "question": "질문 내용",
                    "required": true/false,
                    "options": ["보기1", "보기2"] // type이 radio나 checkbox인 경우에만
                }}
            ]
        }}
        """

        response = client.chat.completions.create(
            model="gpt-3.5-turbo",
            messages=[
                {"role": "system", "content": "You are a helpful assistant that creates survey questions."},
                {"role": "user", "content": prompt}
            ],
            temperature=0.7
        )

        # JSON 응답 파싱
        survey_data = json.loads(response.choices[0].message.content)
        return survey_data
        
    except Exception as e:
        st.error(f"Survey 문항 생성 중 오류 발생: {str(e)}")
        return None

def create_google_form(survey_data):
    """Google Forms API를 사용하여 설문지를 생성합니다."""
    # TODO: Google Forms API 연동
    return None

def show_survey_creation():
    st.header("새로운 Survey 생성")
    
    survey_data = None
    
    with st.form("create_survey"):
        target = st.text_input("Survey 대상", placeholder="예: 교육 참가자, 신입사원, 프로젝트 팀원 등")
        purpose = st.text_area("Survey 목적", placeholder="예: 교육 만족도 평가, 업무 환경 개선을 위한 의견 수집 등")
        requirements = st.text_area("필수 포함 항목", placeholder="예: 만족도 5점 척도, 개선사항 의견, 재참여 의향 등")
        submitted = st.form_submit_button("Survey 추천받기")
        
    if submitted:
        if not target or not purpose or not requirements:
            st.error("모든 항목을 입력해주세요.")
            return
            
        with st.spinner("OpenAI로부터 Survey 문항을 생성하는 중..."):
            survey_data = generate_survey_questions(target, purpose, requirements)
            
    if survey_data:
        st.success("✨ Survey 문항이 생성되었습니다!")
        
        # 설문 제목과 설명 표시
        st.subheader(survey_data["title"])
        st.write(survey_data["description"])
        
        # 문항 표시
        st.subheader("추천 Survey 문항")
        for i, q in enumerate(survey_data["questions"], 1):
            st.markdown(f"**{i}. {q['question']}**")
            if q['type'] in ['radio', 'checkbox']:
                st.write("보기:")
                for option in q['options']:
                    st.write(f"- {option}")
            st.write(f"유형: {q['type']}")
            st.write(f"필수 여부: {'예' if q['required'] else '아니오'}")
            st.write("---")
        
        col1, col2 = st.columns(2)
        with col1:
            if st.button("Google Forms로 생성"):
                with st.spinner("Google Forms 생성 중..."):
                    form_url = create_google_form(survey_data)
                    if form_url:
                        st.success("Google Forms가 생성되었습니다!")
                        st.markdown(f"[설문 링크]({form_url})")
                    else:
                        st.info("Google Forms API 연동 준비 중...")
        
        with col2:
            # JSON 다운로드 버튼
            json_str = json.dumps(survey_data, ensure_ascii=False, indent=2)
            st.download_button(
                "JSON 다운로드",
                json_str.encode('utf-8'),
                "survey_questions.json",
                "application/json",
                key='download-json'
            )

def show_survey_status():
    st.header("Survey 응답 현황")
    
    if not st.session_state.survey_sheets:
        st.warning("먼저 'Survey 관리'에서 Survey를 추가해주세요.")
        return
    
    # Survey 선택
    selected_survey = st.selectbox(
        "Survey 선택",
        options=[sheet["name"] for sheet in st.session_state.survey_sheets]
    )
    
    # 선택된 Survey의 데이터 로드
    selected_sheet = next(
        sheet for sheet in st.session_state.survey_sheets 
        if sheet["name"] == selected_survey
    )
    
    try:
        client = get_gspread_client()
        if client:
            sheet = client.open_by_key(selected_sheet["id"]).sheet1
            responses = sheet.get_all_records()
            df_survey = pd.DataFrame(responses)
            
            if not df_survey.empty:
                # 응답 현황
                total_responses = len(df_survey)
                
                # 메트릭 카드 스타일의 응답 현황
                st.markdown("""
                    <div style="padding: 1rem; background: #f8f9fa; border-radius: 0.5rem; margin-bottom: 2rem;">
                        <h3 style="color: #2563EB; margin-bottom: 0.5rem;">응답 현황</h3>
                        <p style="font-size: 2.5rem; font-weight: bold; color: #1e40af; margin: 0;">
                            {}명
                        </p>
                    </div>
                """.format(total_responses), unsafe_allow_html=True)
                
                # 만족도 분포 (만족도 컬럼이 있는 경우)
                if '만족도' in df_survey.columns:
                    st.subheader("만족도 분포")
                    satisfaction_counts = df_survey['만족도'].value_counts()
                    
                    # 만족도 순서 정의
                    satisfaction_order = ['매우 만족', '만족', '보통', '불만족', '매우 불만족']
                    satisfaction_counts = satisfaction_counts.reindex(satisfaction_order).fillna(0)
                    
                    # 색상 맵 정의
                    colors = ['#22c55e', '#86efac', '#fde047', '#f87171', '#dc2626']
                    
                    # Plotly를 사용한 도넛 차트
                    fig = go.Figure(data=[go.Pie(
                        labels=satisfaction_counts.index,
                        values=satisfaction_counts.values,
                        hole=.4,
                        marker=dict(colors=colors)
                    )])
                    
                    fig.update_layout(
                        title="만족도 분포",
                        annotations=[dict(text=f'총 {total_responses}명', x=0.5, y=0.5, font_size=20, showarrow=False)],
                        showlegend=True,
                        legend=dict(orientation="h", yanchor="bottom", y=1.02, xanchor="right", x=1),
                        width=800,
                        height=500
                    )
                    
                    st.plotly_chart(fig, use_container_width=True)
                    
                    # 만족도 통계
                    col1, col2, col3 = st.columns(3)
                    with col1:
                        positive_rate = ((satisfaction_counts['매우 만족'] + satisfaction_counts['만족']) / total_responses * 100)
                        st.metric("긍정 응답률", f"{positive_rate:.1f}%")
                    with col2:
                        neutral_rate = (satisfaction_counts['보통'] / total_responses * 100)
                        st.metric("중립 응답률", f"{neutral_rate:.1f}%")
                    with col3:
                        negative_rate = ((satisfaction_counts['불만족'] + satisfaction_counts['매우 불만족']) / total_responses * 100)
                        st.metric("부정 응답률", f"{negative_rate:.1f}%")
                
                # 기타 응답 분포
                other_cols = [col for col in df_survey.columns if col != '만족도' and df_survey[col].dtype == 'object' and len(df_survey[col].unique()) < 10]
                
                if other_cols:
                    st.subheader("기타 응답 분포")
                    for col in other_cols:
                        counts = df_survey[col].value_counts()
                        
                        # Plotly를 사용한 바 차트
                        fig = go.Figure(data=[
                            go.Bar(
                                x=counts.values,
                                y=counts.index,
                                orientation='h',
                                marker=dict(
                                    color='#3b82f6',
                                    line=dict(color='#1e40af', width=1)
                                )
                            )
                        ])
                        
                        fig.update_layout(
                            title=f"{col} 분포",
                            xaxis_title="응답 수",
                            yaxis_title=None,
                            showlegend=False,
                            width=800,
                            height=400
                        )
                        
                        st.plotly_chart(fig, use_container_width=True)
                        
                        # 응답 비율 표시
                        st.markdown(f"""
                            <div style="padding: 1rem; background: #f8f9fa; border-radius: 0.5rem; margin-bottom: 2rem;">
                                <h4 style="color: #2563EB; margin-bottom: 0.5rem;">{col} 응답 비율</h4>
                                <div style="display: flex; flex-wrap: wrap; gap: 1rem;">
                                    {' '.join([f'<div style="background: #dbeafe; padding: 0.5rem; border-radius: 0.25rem;"><b>{k}</b>: {v/total_responses*100:.1f}%</div>' for k, v in counts.items()])}
                                </div>
                            </div>
                        """, unsafe_allow_html=True)
            else:
                st.info("아직 응답이 없습니다.")
    except Exception as e:
        st.error(f"데이터 로드 중 오류 발생: {str(e)}")

def show_survey_results():
    st.header("Survey 결과")
    
    if not st.session_state.survey_sheets:
        st.warning("먼저 'Survey 관리'에서 Survey를 추가해주세요.")
        return
    
    # Survey 선택
    selected_survey = st.selectbox(
        "Survey 선택",
        options=[sheet["name"] for sheet in st.session_state.survey_sheets],
        key="results"
    )
    
    # 선택된 Survey의 데이터 로드
    selected_sheet = next(
        sheet for sheet in st.session_state.survey_sheets 
        if sheet["name"] == selected_survey
    )
    
    try:
        client = get_gspread_client()
        if client:
            sheet = client.open_by_key(selected_sheet["id"]).sheet1
            responses = sheet.get_all_records()
            df_survey = pd.DataFrame(responses)
            
            if not df_survey.empty:
                st.subheader("Raw Data")
                st.dataframe(df_survey)
                
                # CSV 다운로드 버튼
                csv = df_survey.to_csv(index=False).encode('utf-8')
                st.download_button(
                    "CSV 다운로드",
                    csv,
                    f"{selected_survey}_results.csv",
                    "text/csv",
                    key='download-csv'
                )
            else:
                st.info("아직 응답이 없습니다.")
    except Exception as e:
        st.error(f"데이터 로드 중 오류 발생: {str(e)}")

def show_reminder():
    st.header("리마인더")
    
    if not st.session_state.survey_sheets:
        st.warning("먼저 'Survey 관리'에서 Survey를 추가해주세요.")
        return
    
    # Survey 선택
    selected_survey = st.selectbox(
        "Survey 선택",
        options=[sheet["name"] for sheet in st.session_state.survey_sheets],
        key="reminder"
    )
    
    # 선택된 Survey의 데이터 로드
    selected_sheet = next(
        sheet for sheet in st.session_state.survey_sheets 
        if sheet["name"] == selected_survey
    )
    
    # 대상자 명단 입력 방식 선택
    st.subheader("대상자 명단")
    input_method = st.radio(
        "입력 방식 선택",
        ["등록된 대상자 목록", "Google Sheets 연동", "파일 업로드"],
        horizontal=True
    )
    
    df_students = None
    
    if input_method == "등록된 대상자 목록":
        if 'target_sheets' not in st.session_state or not st.session_state.target_sheets:
            st.warning("등록된 대상자 목록이 없습니다. '대상자 관리' 메뉴에서 목록을 추가해주세요.")
        else:
            selected_target = st.selectbox(
                "대상자 목록 선택",
                options=[sheet["name"] for sheet in st.session_state.target_sheets],
                key="target_list"
            )
            
            try:
                selected_target_sheet = next(
                    sheet for sheet in st.session_state.target_sheets 
                    if sheet["name"] == selected_target
                )
                
                client = get_gspread_client()
                if client:
                    sheet = client.open_by_key(selected_target_sheet['id']).sheet1
                    data = sheet.get_all_records()
                    df_students = pd.DataFrame(data)
                    st.success("✅ 대상자 명단을 성공적으로 불러왔습니다.")
                    st.dataframe(df_students)
            except Exception as e:
                st.error(f"대상자 목록 로드 중 오류 발생: {str(e)}")
    
    elif input_method == "Google Sheets 연동":
        sheet_url = st.text_input("Google Sheets URL")
        if sheet_url:
            try:
                client = get_gspread_client()
                if client:
                    sheet_id = extract_sheet_id(sheet_url)
                    if sheet_id:
                        sheet = client.open_by_key(sheet_id).sheet1
                        data = sheet.get_all_records()
                        df_students = pd.DataFrame(data)
                        st.success("✅ 대상자 명단을 성공적으로 불러왔습니다.")
                        st.dataframe(df_students)
            except Exception as e:
                st.error(f"Google Sheets 로드 중 오류 발생: {str(e)}")
    else:  # 파일 업로드
        uploaded_file = st.file_uploader(
            "Excel/CSV 파일 업로드",
            type=['xlsx', 'csv'],
            help="이름, 소속, 이메일 컬럼이 포함된 파일을 업로드하세요."
        )
        
        if uploaded_file:
            try:
                if uploaded_file.name.endswith('.csv'):
                    df_students = pd.read_csv(uploaded_file)
                else:
                    try:
                        df_students = pd.read_excel(uploaded_file)
                    except ImportError:
                        st.error("""
                            ### Excel 파일 처리를 위한 패키지가 필요합니다
                            터미널에서 다음 명령어를 실행하세요:
                            ```
                            pip install openpyxl
                            ```
                            설치 후 앱을 다시 실행하세요.
                        """)
                        return
                
                st.success("✅ 대상자 명단을 성공적으로 불러왔습니다.")
                st.dataframe(df_students)
                
            except Exception as e:
                st.error(f"파일 처리 중 오류 발생: {str(e)}")
    
    # 대상자 명단이 로드된 경우에만 리마인더 처리
    if df_students is not None:
        try:
            # 응답 데이터 로드
            client = get_gspread_client()
            if client:
                sheet = client.open_by_key(selected_sheet["id"]).sheet1
                responses = sheet.get_all_records()
                df_survey = pd.DataFrame(responses)
                
                # 미응답자 찾기
                non_respondents = find_non_respondents(df_students, df_survey)
                
                if len(non_respondents) == 0:
                    st.success("🎉 모든 대상자가 응답을 완료했습니다!")
                else:
                    st.info(f"📝 현재 {len(non_respondents)}명의 미응답자가 있습니다.")
                    
                    st.subheader("미응답자 목록")
                    st.dataframe(
                        non_respondents[['이름', '소속', '이메일']],
                        hide_index=True
                    )
                    
                    if st.button("리마인더 발송", type="primary"):
                        with st.spinner("리마인더 발송 중..."):
                            success_count = 0
                            total_count = len(non_respondents)
                            progress_bar = st.progress(0.0)
                            
                            for idx, row in non_respondents.iterrows():
                                if send_reminder_email(row['이름'], row['이메일'], selected_sheet["url"]):
                                    success_count += 1
                                    st.success(f"✅ {row['이름']}님께 리마인더를 발송했습니다.")
                                
                                progress_bar.progress(min(1.0, (idx + 1) / total_count))
                            
                            st.balloons()
                            st.success(f"✨ 총 {success_count}명에게 리마인더를 발송했습니다!")
        except Exception as e:
            st.error(f"리마인더 처리 중 오류 발생: {str(e)}")

def main():
    st.title("📊 Survey Management System")
    
    # 메뉴 상태 초기화
    if 'menu' not in st.session_state:
        st.session_state.menu = "메인 화면"
    
    # 메인 메뉴
    st.session_state.menu = st.sidebar.selectbox(
        "메뉴 선택",
        ["메인 화면", "Survey 관리", "대상자 관리", "새로운 Survey 생성", "Survey 응답 현황", "Survey 결과", "리마인더"],
        index=["메인 화면", "Survey 관리", "대상자 관리", "새로운 Survey 생성", "Survey 응답 현황", "Survey 결과", "리마인더"].index(st.session_state.menu)
    )
    
    if st.session_state.menu == "메인 화면":
        show_main_dashboard()
    elif st.session_state.menu == "Survey 관리":
        show_survey_management()
    elif st.session_state.menu == "대상자 관리":
        show_target_management()
    elif st.session_state.menu == "새로운 Survey 생성":
        show_survey_creation()
    elif st.session_state.menu == "Survey 응답 현황":
        show_survey_status()
    elif st.session_state.menu == "Survey 결과":
        show_survey_results()
    elif st.session_state.menu == "리마인더":
        show_reminder()

def show_main_dashboard():
    """메인 대시보드를 표시합니다."""
    st.markdown('<h1 class="main-title">Survey Management System</h1>', unsafe_allow_html=True)
    
    # 시스템 개요
    st.markdown("""
        <div class="card-container">
            <h2 class="sub-title">시스템 개요</h2>
            <p>Survey Management System은 설문조사 생성, 관리, 분석을 위한 통합 플랫폼입니다.
            OpenAI를 활용한 설문 문항 자동 생성, Google Sheets 연동, 응답 현황 분석 등 다양한 기능을 제공합니다.</p>
        </div>
    """, unsafe_allow_html=True)
    
    # 주요 기능 카드
    st.markdown('<h2 class="sub-title">주요 기능</h2>', unsafe_allow_html=True)
    
    col1, col2, col3 = st.columns(3)
    
    with col1:
        st.markdown("""
            <div class="card-container">
                <h3 style="color: #2563EB; font-size: 1.5rem; margin-bottom: 1rem;">
                    📊 Survey 관리
                </h3>
                <p style="margin-bottom: 1rem;">Survey 목록을 관리하고 새로운 Survey를 생성합니다.</p>
            </div>
        """, unsafe_allow_html=True)
        if st.button("Survey 관리", key="btn_survey_mgmt", use_container_width=True):
            st.session_state.menu = "Survey 관리"
            st.rerun()
            
        st.markdown("""
            <div class="card-container">
                <h3 style="color: #2563EB; font-size: 1.5rem; margin-bottom: 1rem;">
                    📈 Survey 결과
                </h3>
                <p style="margin-bottom: 1rem;">응답 데이터를 분석하고 결과를 확인합니다.</p>
            </div>
        """, unsafe_allow_html=True)
        if st.button("Survey 결과", key="btn_survey_results", use_container_width=True):
            st.session_state.menu = "Survey 결과"
            st.rerun()
    
    with col2:
        st.markdown("""
            <div class="card-container">
                <h3 style="color: #2563EB; font-size: 1.5rem; margin-bottom: 1rem;">
                    👥 대상자 관리
                </h3>
                <p style="margin-bottom: 1rem;">Survey 대상자 목록을 관리합니다.</p>
            </div>
        """, unsafe_allow_html=True)
        if st.button("대상자 관리", key="btn_target_mgmt", use_container_width=True):
            st.session_state.menu = "대상자 관리"
            st.rerun()
            
        st.markdown("""
            <div class="card-container">
                <h3 style="color: #2563EB; font-size: 1.5rem; margin-bottom: 1rem;">
                    ✉️ 리마인더
                </h3>
                <p style="margin-bottom: 1rem;">미응답자에게 알림을 발송합니다.</p>
            </div>
        """, unsafe_allow_html=True)
        if st.button("리마인더", key="btn_reminder", use_container_width=True):
            st.session_state.menu = "리마인더"
            st.rerun()
    
    with col3:
        st.markdown("""
            <div class="card-container">
                <h3 style="color: #2563EB; font-size: 1.5rem; margin-bottom: 1rem;">
                    🤖 Survey 생성
                </h3>
                <p style="margin-bottom: 1rem;">OpenAI를 활용하여 새로운 Survey를 생성합니다.</p>
            </div>
        """, unsafe_allow_html=True)
        if st.button("Survey 생성", key="btn_survey_create", use_container_width=True):
            st.session_state.menu = "새로운 Survey 생성"
            st.rerun()
    
    # 현황 대시보드
    if st.session_state.survey_sheets or ('target_sheets' in st.session_state and st.session_state.target_sheets):
        st.markdown('<h2 class="sub-title">현황 대시보드</h2>', unsafe_allow_html=True)
        
        col1, col2, col3 = st.columns(3)
        
        with col1:
            st.markdown("""
                <div class="metric-card">
                    <h4 style="color: #4B5563; margin-bottom: 0.5rem;">등록된 Survey</h4>
                    <p style="color: #2563EB; font-size: 2rem; font-weight: 700; margin: 0;">
                        {}개
                    </p>
                </div>
            """.format(len(st.session_state.survey_sheets)), unsafe_allow_html=True)
        
        with col2:
            if 'target_sheets' in st.session_state:
                st.markdown("""
                    <div class="metric-card">
                        <h4 style="color: #4B5563; margin-bottom: 0.5rem;">등록된 대상자 목록</h4>
                        <p style="color: #2563EB; font-size: 2rem; font-weight: 700; margin: 0;">
                            {}개
                        </p>
                    </div>
                """.format(len(st.session_state.target_sheets)), unsafe_allow_html=True)

def show_target_management():
    """대상자 관리 페이지를 표시합니다."""
    st.header("대상자 관리")
    
    # 대상자 목록 상태 초기화
    if 'target_sheets' not in st.session_state:
        st.session_state.target_sheets = []
    
    tab1, tab2 = st.tabs(["📋 대상자 목록", "➕ 새 대상자 추가"])
    
    with tab1:
        if st.session_state.target_sheets:
            for idx, sheet in enumerate(st.session_state.target_sheets):
                with st.expander(f"대상자 목록 {idx + 1}: {sheet['name']}"):
                    try:
                        client = get_gspread_client()
                        if client:
                            sheet_data = client.open_by_key(sheet['id']).sheet1
                            df = pd.DataFrame(sheet_data.get_all_records())
                            st.dataframe(df)
                            
                            # CSV 다운로드 버튼
                            csv = df.to_csv(index=False).encode('utf-8')
                            st.download_button(
                                "CSV 다운로드",
                                csv,
                                f"{sheet['name']}_대상자목록.csv",
                                "text/csv",
                                key=f'download-csv-{idx}'
                            )
                            
                            if st.button("삭제", key=f"del_target_{idx}"):
                                st.session_state.target_sheets.pop(idx)
                                st.rerun()
                    except Exception as e:
                        st.error(f"데이터 로드 중 오류 발생: {str(e)}")
        else:
            st.info("등록된 대상자 목록이 없습니다. 새로운 목록을 추가해주세요.")
    
    with tab2:
        st.subheader("새 대상자 목록 추가")
        
        method = st.radio(
            "추가 방법 선택",
            ["Google Sheets 연동", "파일 업로드"],
            horizontal=True
        )
        
        if method == "Google Sheets 연동":
            with st.form("add_target_sheet"):
                list_name = st.text_input("목록 이름")
                sheet_url = st.text_input("Google Sheets URL")
                submitted = st.form_submit_button("추가")
                
                if submitted and list_name and sheet_url:
                    sheet_id = extract_sheet_id(sheet_url)
                    if sheet_id:
                        st.session_state.target_sheets.append({
                            "name": list_name,
                            "url": sheet_url,
                            "id": sheet_id
                        })
                        st.success(f"✅ {list_name} 목록이 추가되었습니다!")
                        st.rerun()
        
        else:  # 파일 업로드
            uploaded_file = st.file_uploader(
                "Excel/CSV 파일 업로드",
                type=['xlsx', 'csv'],
                help="이름, 소속, 이메일 컬럼이 포함된 파일을 업로드하세요."
            )
            
            if uploaded_file:
                try:
                    if uploaded_file.name.endswith('.csv'):
                        df = pd.read_csv(uploaded_file)
                    else:
                        df = pd.read_excel(uploaded_file)
                    
                    st.dataframe(df)
                    
                    if st.button("Google Sheets로 저장"):
                        try:
                            client = get_gspread_client()
                            if client:
                                # 새 스프레드시트 생성
                                sheet = client.create(f"대상자목록_{datetime.datetime.now().strftime('%Y%m%d_%H%M%S')}")
                                # 데이터 저장
                                worksheet = sheet.sheet1
                                worksheet.update([df.columns.values.tolist()] + df.values.tolist())
                                
                                # 목록에 추가
                                st.session_state.target_sheets.append({
                                    "name": uploaded_file.name.split('.')[0],
                                    "url": f"https://docs.google.com/spreadsheets/d/{sheet.id}",
                                    "id": sheet.id
                                })
                                
                                st.success("✅ 대상자 목록이 Google Sheets에 저장되었습니다!")
                                st.rerun()
                        except Exception as e:
                            st.error(f"Google Sheets 저장 중 오류 발생: {str(e)}")
                
                except Exception as e:
                    st.error(f"파일 처리 중 오류 발생: {str(e)}")

def show_survey_management():
    st.header("Survey 관리")
    
    # Google Sheets 추가
    with st.form("add_sheet"):
        sheet_name = st.text_input("Survey 이름")
        sheet_url = st.text_input("Google Sheets URL")
        submitted = st.form_submit_button("추가")
        
        if submitted and sheet_name and sheet_url:
            sheet_id = extract_sheet_id(sheet_url)
            if sheet_id:
                if 'survey_sheets' not in st.session_state:
                    st.session_state.survey_sheets = []
                st.session_state.survey_sheets.append({
                    "name": sheet_name,
                    "url": sheet_url,
                    "id": sheet_id
                })
                st.success(f"✅ {sheet_name} Survey가 추가되었습니다!")
    
    # 등록된 Sheets 목록
    if st.session_state.survey_sheets:
        st.subheader("등록된 Survey 목록")
        for idx, sheet in enumerate(st.session_state.survey_sheets):
            col1, col2, col3 = st.columns([3, 6, 1])
            with col1:
                st.write(sheet["name"])
            with col2:
                st.write(sheet["url"])
            with col3:
                if st.button("삭제", key=f"del_{idx}"):
                    st.session_state.survey_sheets.pop(idx)
                    st.rerun()
    else:
        st.info("등록된 Survey가 없습니다. 새로운 Survey를 추가해주세요.")

if __name__ == "__main__":
    main() 