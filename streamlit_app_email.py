import streamlit as st
import pandas as pd
import os
from dotenv import load_dotenv
import base64
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from google.oauth2.credentials import Credentials
from google_auth_oauthlib.flow import InstalledAppFlow
from google.auth.transport.requests import Request
from googleapiclient.discovery import build
import pickle
import gspread
from oauth2client.service_account import ServiceAccountCredentials

# 페이지 설정
st.set_page_config(
    page_title="교육 만족도 조사 관리 시스템",
    page_icon="📊",
    layout="wide"
)

# 환경 변수 로드
load_dotenv()

# Gmail API 설정
SCOPES = ['https://www.googleapis.com/auth/gmail.send']

@st.cache_resource
def get_gmail_service():
    """Gmail API 서비스를 가져옵니다."""
    creds = None
    
    # 토큰 파일이 있으면 로드
    if os.path.exists('token.pickle'):
        with open('token.pickle', 'rb') as token:
            creds = pickle.load(token)
    
    # 유효한 인증정보가 없으면 새로 생성
    if not creds or not creds.valid:
        if creds and creds.expired and creds.refresh_token:
            creds.refresh(Request())
        else:
            flow = InstalledAppFlow.from_client_secrets_file(
                'credentials.json', SCOPES)
            creds = flow.run_local_server(port=0)
        
        # 토큰 저장
        with open('token.pickle', 'wb') as token:
            pickle.dump(creds, token)
    
    return build('gmail', 'v1', credentials=creds)

@st.cache_data
def load_spreadsheet_data():
    """구글 스프레드시트에서 데이터를 로드합니다."""
    scope = ['https://spreadsheets.google.com/feeds',
             'https://www.googleapis.com/auth/drive']
    
    try:
        creds = ServiceAccountCredentials.from_json_keyfile_name('service_account.json', scope)
        client = gspread.authorize(creds)
        
        # 교육생 명단
        student_sheet = client.open_by_url(
            "https://docs.google.com/spreadsheets/d/1vzBNy-ZtCYfbvsTUnEL0S2unI-jsskr87ChqkDpcJGQ/edit?gid=0"
        ).sheet1
        students_data = student_sheet.get_all_records()
        df_students = pd.DataFrame(students_data)
        
        # 만족도 조사 응답
        survey_sheet = client.open_by_url(
            "https://docs.google.com/spreadsheets/d/1L6uYz41OUA2wTngCuYxo7Wf1sab7KeOGn3XqWcPRb14/edit?gid=1818210716"
        ).sheet1
        survey_data = survey_sheet.get_all_records()
        df_survey = pd.DataFrame(survey_data)
        
        return df_students, df_survey
    
    except Exception as e:
        st.error(f"스프레드시트 로드 중 오류 발생: {str(e)}")
        return None, None

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

def send_reminder_email(service, recipient_name, recipient_email, survey_link):
    """Gmail API를 사용하여 미응답자에게 알림 이메일을 보냅니다."""
    sender_email = "younique624@gmail.com"
    
    # 이메일 내용 설정
    subject = "[알림] 교육 만족도 조사 응답 요청"
    body = f"""안녕하세요, {recipient_name}님.

교육 만족도 조사에 아직 응답하지 않으신 것 같습니다.
더 나은 교육 서비스를 위해 귀하의 소중한 의견이 필요합니다.

아래 링크를 통해 만족도 조사에 참여해 주시면 감사하겠습니다:
{survey_link}

감사합니다."""
    
    # 이메일 메시지 생성
    message = MIMEMultipart()
    message['to'] = recipient_email
    message['from'] = sender_email
    message['subject'] = subject
    message.attach(MIMEText(body, 'plain'))
    
    # 메시지를 Base64로 인코딩
    raw_message = base64.urlsafe_b64encode(message.as_bytes()).decode('utf-8')
    
    try:
        # 이메일 발송
        service.users().messages().send(
            userId='me',
            body={'raw': raw_message}
        ).execute()
        return True
    except Exception as e:
        st.error(f"{recipient_name}님 이메일 발송 실패: {str(e)}")
        return False

def main():
    st.title("📊 교육 만족도 조사 관리 시스템")
    
    # 사이드바 설정
    with st.sidebar:
        st.header("설정")
        survey_link = st.text_input(
            "만족도 조사 링크",
            value="https://forms.gle/your-survey-link",
            help="실제 만족도 조사 Google Forms 링크를 입력하세요."
        )
    
    # Gmail API 서비스 초기화
    try:
        service = get_gmail_service()
        st.success("✅ Gmail API 연결됨")
    except Exception as e:
        st.error(f"❌ Gmail API 연결 실패: {str(e)}")
        return
    
    # 탭 생성
    tab1, tab2 = st.tabs(["📊 현황", "📧 이메일 발송"])
    
    with tab1:
        st.header("응답 현황")
        
        # 데이터 로드
        with st.spinner("데이터를 불러오는 중..."):
            df_students, df_survey = load_spreadsheet_data()
        
        if df_students is not None and df_survey is not None:
            # 전체 현황
            col1, col2, col3 = st.columns(3)
            total_students = len(df_students)
            total_responses = len(df_survey)
            response_rate = (total_responses / total_students) * 100 if total_students > 0 else 0
            
            col1.metric("전체 교육생", f"{total_students}명")
            col2.metric("응답 완료", f"{total_responses}명")
            col3.metric("응답률", f"{response_rate:.1f}%")
            
            # 미응답자 목록
            st.subheader("미응답자 목록")
            non_respondents = find_non_respondents(df_students, df_survey)
            if len(non_respondents) > 0:
                st.dataframe(
                    non_respondents[['이름', '소속', '이메일']],
                    hide_index=True,
                    column_config={
                        "이름": st.column_config.TextColumn("이름", width="medium"),
                        "소속": st.column_config.TextColumn("소속", width="medium"),
                        "이메일": st.column_config.TextColumn("이메일", width="large")
                    }
                )
            else:
                st.success("🎉 모든 교육생이 응답을 완료했습니다!")
    
    with tab2:
        st.header("이메일 발송")
        
        if df_students is not None and df_survey is not None:
            non_respondents = find_non_respondents(df_students, df_survey)
            
            if len(non_respondents) == 0:
                st.success("🎉 모든 교육생이 응답을 완료했습니다!")
            else:
                st.info(f"📝 현재 {len(non_respondents)}명의 미응답자가 있습니다.")
                
                # 이메일 발송 버튼
                if st.button("미응답자에게 이메일 발송", type="primary"):
                    with st.spinner("이메일 발송 중..."):
                        success_count = 0
                        progress_bar = st.progress(0)
                        
                        for idx, row in non_respondents.iterrows():
                            if send_reminder_email(service, row['이름'], row['이메일'], survey_link):
                                success_count += 1
                                st.success(f"✅ {row['이름']}님께 이메일을 발송했습니다.")
                            progress_bar.progress((idx + 1) / len(non_respondents))
                        
                        if success_count > 0:
                            st.success(f"✨ 총 {success_count}명에게 이메일을 발송했습니다!")
                        else:
                            st.error("이메일 발송에 실패했습니다.")

if __name__ == "__main__":
    main() 