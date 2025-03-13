import streamlit as st
import pandas as pd
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
import os
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
import requests
import smtplib
import httpx

# 페이지 설정
st.set_page_config(
    page_title="SK AI Camp",
    page_icon="🎓",
    layout="wide"
)

# OpenAI API 키 설정 (Streamlit secrets 사용)
if 'openai' in st.secrets:
    client = OpenAI(api_key=st.secrets['openai']['api_key'])
else:
    st.error("OpenAI API 키가 설정되지 않았습니다. Streamlit Cloud의 Secrets에서 설정해주세요.")
    client = None

# 이메일 설정 (Streamlit secrets 사용)
EMAIL_ADDRESS = st.secrets.get("email", {}).get("gmail_user")
EMAIL_PASSWORD = st.secrets.get("email", {}).get("admin_email")

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

# 세션 상태 초기화
if 'is_admin' not in st.session_state:
    st.session_state.is_admin = False

# 페이지 접근 제어
def check_admin_access():
    """관리자 로그인 여부를 확인하고 접근을 제어합니다."""
    # 현재 페이지 경로 확인
    page_path = st.query_params.get("page", [""])[0]
    
    # 관리자 전용 페이지 목록
    admin_pages = ["streamlit_app_email_simple", "survey_generator"]
    
    # 관리자가 아니고 관리자 전용 페이지에 접근하려는 경우
    if not st.session_state.is_admin and page_path in admin_pages:
        st.error("관리자 로그인이 필요한 페이지입니다.")
        st.stop()

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
        # 서비스 계정 정보를 st.secrets에서 가져옵니다
        if 'gcp' not in st.secrets:
            st.error("서비스 계정 정보가 설정되지 않았습니다. Streamlit Cloud의 Secrets에서 설정해주세요.")
            return None
            
        # service_account.json 파일 생성
        service_account_info = json.loads(st.secrets["gcp"]["service_account"])
        with open('service_account.json', 'w', encoding='utf-8') as f:
            json.dump(service_account_info, f, ensure_ascii=False, indent=2)
            
        creds = ServiceAccountCredentials.from_json_keyfile_name('service_account.json', scope)
        client = gspread.authorize(creds)
        
        # 사용이 끝난 파일 삭제
        os.remove('service_account.json')
        
        return client
    except Exception as e:
        st.error(f"Google Sheets API 연결 오류: {str(e)}")
        if os.path.exists('service_account.json'):
            os.remove('service_account.json')
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

def load_notion_content():
    """Notion 페이지 내용을 로드합니다."""
    notion_url = "https://days-ai.notion.site/SK-AI-Camp-1-19aa024df4dc80f187a1fded00e54339"
    return notion_url

def create_tally_form(title, questions):
    """Tally에서 새로운 폼을 생성합니다."""
    TALLY_API_KEY = st.secrets["tally"]["api_key"]
    api_url = "https://api.tally.so/forms"
    
    # 폼 필드 구성
    fields = []
    for i, question in enumerate(questions):
        fields.append({
            "name": f"question_{i+1}",
            "type": "LONG_TEXT",
            "label": question,
            "required": True
        })
    
    # 요청 데이터
    data = {
        "name": title,
        "fields": fields
    }
    
    # API 요청
    headers = {
        "Authorization": f"Bearer {TALLY_API_KEY}",
        "Content-Type": "application/json"
    }
    
    response = requests.post(api_url, json=data, headers=headers)
    if response.status_code == 201:
        form_data = response.json()
        return form_data["formUrl"]
    else:
        st.error(f"Tally 폼 생성 실패: {response.text}")
        return None

def get_chatbot_response(question):
    """OpenAI를 사용하여 챗봇 응답을 생성합니다."""
    try:
        if not client:
            return "OpenAI API 키가 설정되지 않았습니다."
            
        response = client.chat.completions.create(
            model="gpt-3.5-turbo",
            messages=[
                {"role": "system", "content": """당신은 SK AI Camp 1기 교육 프로그램의 전문 상담사입니다. 
                교육생들의 질문에 친절하고 전문적으로 답변해주세요.
                
                [교육 개요]
                - SK AI Camp는 AI 기술을 활용한 비즈니스 혁신을 주도할 인재 양성 프로그램입니다.
                - 교육 기간은 4일간 진행됩니다.
                - 교육 대상은 SK 그룹사 구성원입니다.
                
                [교육 목표]
                - AI 기술의 이해와 활용 역량 강화
                - AI 프로젝트 기획 및 관리 능력 배양
                - 실무 중심의 AI 비즈니스 케이스 학습
                
                [교육 구성]
                1. AI 기초 및 활용
                   - AI/ML 기본 개념 이해
                   - 생성형 AI의 이해와 활용
                   - AI 윤리와 책임
                
                2. AI 프로젝트 실무
                   - AI 프로젝트 기획과 관리
                   - 데이터 전략 수립
                   - AI 솔루션 도입 사례
                
                3. 실습 및 워크샵
                   - AI 도구 활용 실습
                   - 팀 프로젝트 수행
                   - 비즈니스 케이스 분석
                
                교육은 실무 중심의 집중 교육으로 진행되며, 이론과 실습이 균형있게 구성되어 있습니다."""},
                {"role": "user", "content": question}
            ],
            temperature=0.7
        )
        
        return response.choices[0].message.content
    except Exception as e:
        return f"응답 생성 중 오류가 발생했습니다: {str(e)}"

def main():
    # 관리자 접근 제어 확인
    check_admin_access()
    
    st.title("🎓 SK AI Camp Portal")
    
    # 사이드바에 관리자 로그인 섹션
    with st.sidebar:
        st.header("관리자 로그인")
        if not st.session_state.is_admin:
            password = st.text_input("관리자 비밀번호", type="password")
            if st.button("로그인"):
                if password == "admin123":
                    st.session_state.is_admin = True
                    st.success("관리자로 로그인되었습니다!")
                    st.rerun()
                else:
                    st.error("비밀번호가 올바르지 않습니다.")
        else:
            if st.button("로그아웃"):
                st.session_state.is_admin = False
                st.rerun()
        
        # 메뉴 표시
        st.markdown("### 메뉴")
        
        # 모든 사용자용 메뉴
        st.page_link("streamlit_app_email_simple.py", label="SK AI Camp Portal", icon="🎓")
        st.page_link("pages/chatbot_faq.py", label="AI 챗봇 & FAQ", icon="🤖")
        
        # 관리자용 메뉴
        if st.session_state.is_admin:
            st.page_link("pages/survey_management.py", label="Survey Management", icon="📊")

    # 메인 컨텐츠
    if st.session_state.is_admin:
        # 관리자용 메뉴
        st.header("관리자 메뉴")
        tab1, tab2 = st.tabs(["설문지 생성기", "Survey Management"])
        
        with tab1:
            st.subheader("설문지 생성")
            topic = st.text_input("설문 주제 입력", placeholder="예: AI 교육 만족도 조사")
            
            if st.button("설문 문항 추천"):
                if topic:
                    with st.spinner("설문 문항을 생성하고 있습니다..."):
                        # 여기에 기존 설문 문항 생성 로직 추가
                        questions = [
                            "이번 교육에서 가장 유익했던 내용은 무엇인가요?",
                            "교육 내용의 난이도는 적절했나요?",
                            "강사의 전달력은 어떠했나요?",
                            "실습 시간은 충분했나요?",
                            "이번 교육을 통해 얻은 가장 큰 인사이트는 무엇인가요?"
                        ]
                        st.session_state.generated_questions = questions
                        
                        # 생성된 문항 표시
                        st.subheader("추천된 설문 문항")
                        for i, q in enumerate(questions, 1):
                            st.write(f"{i}. {q}")
                        
                        # JSON 다운로드 버튼
                        survey_data = {
                            "title": topic,
                            "questions": questions
                        }
                        json_str = json.dumps(survey_data, ensure_ascii=False, indent=2)
                        st.download_button(
                            "JSON 다운로드",
                            json_str.encode('utf-8'),
                            "survey_questions.json",
                            "application/json",
                            key='download-json'
                        )
                        
                        # Google Forms 생성 버튼
                        if st.button("Google Forms 생성"):
                            try:
                                form_url = create_google_form(topic, questions)
                                if form_url:
                                    st.success("Google Forms가 생성되었습니다!")
                                    st.markdown(f"[설문 링크]({form_url})")
                                    st.session_state.form_url = form_url
                            except Exception as e:
                                st.error(f"Google Forms 생성 중 오류 발생: {str(e)}")
                else:
                    st.warning("설문 주제를 입력해주세요.")
        
        with tab2:
            st.subheader("Survey Management System")
            # 기존 Survey Management System 기능 추가
    
    else:
        # 교육생용 메뉴
        st.header("SK AI Camp 교육 포털")
        
        # Notion 링크 표시
        notion_url = "https://days-ai.notion.site/SK-AI-Camp-1-19aa024df4dc80f187a1fded00e54339"
        st.markdown("""
        ### 📚 교육 자료
        SK AI Camp 교육 자료는 아래 Notion 페이지에서 확인하실 수 있습니다.
        """)
        st.link_button("Notion 페이지 바로가기", notion_url)
        
        # RAG Chatbot
        st.header("AI 교육 도우미")
        user_question = st.text_input("무엇이든 물어보세요!", placeholder="예: 교육 일정이 어떻게 되나요?")
        
        if user_question:
            with st.spinner("답변을 생성하고 있습니다..."):
                response = get_chatbot_response(user_question)
                st.write(response)

if __name__ == "__main__":
    main() 