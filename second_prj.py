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

# 환경 변수 로드
load_dotenv()

# Gmail API 설정
SCOPES = ['https://www.googleapis.com/auth/gmail.send']

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

def load_spreadsheet_data():
    """구글 스프레드시트에서 데이터를 로드합니다."""
    scope = ['https://spreadsheets.google.com/feeds',
             'https://www.googleapis.com/auth/drive']
    
    creds = ServiceAccountCredentials.from_json_keyfile_name('service_account.json', scope)
    client = gspread.authorize(creds)
    
    try:
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
        print(f"스프레드시트 로드 중 오류 발생: {str(e)}")
        return None, None

def find_non_respondents(df_students, df_survey):
    """미응답자 목록을 찾습니다."""
    if df_students is None or df_survey is None:
        return []
    
    # 응답자 이메일 목록
    respondent_emails = set(df_survey['이메일'].dropna())
    
    # 전체 교육생 이메일 목록
    student_emails = set(df_students['이메일'].dropna())
    
    # 미응답자 찾기
    non_respondent_emails = student_emails - respondent_emails
    
    # 미응답자 정보 가져오기
    non_respondents = df_students[df_students['이메일'].isin(non_respondent_emails)]
    
    return non_respondents

def send_reminder_email(service, recipient_name, recipient_email):
    """Gmail API를 사용하여 미응답자에게 알림 이메일을 보냅니다."""
    sender_email = "younique624@gmail.com"
    
    # 이메일 내용 설정
    subject = "[알림] 교육 만족도 조사 응답 요청"
    body = f"""안녕하세요, {recipient_name}님.

교육 만족도 조사에 아직 응답하지 않으신 것 같습니다.
더 나은 교육 서비스를 위해 귀하의 소중한 의견이 필요합니다.

아래 링크를 통해 만족도 조사에 참여해 주시면 감사하겠습니다:
[만족도 조사 링크]

감사합니다.
"""
    
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
        
        print(f"✅ {recipient_name}님께 이메일을 발송했습니다.")
        return True
    except Exception as e:
        print(f"❌ {recipient_name}님 이메일 발송 실패: {str(e)}")
        return False

def main():
    print("📊 교육 만족도 조사 미응답자 알림 시스템")
    
    # Gmail API 서비스 초기화
    try:
        service = get_gmail_service()
        print("✅ Gmail API 연결 완료")
    except Exception as e:
        print(f"❌ Gmail API 연결 실패: {str(e)}")
        return
    
    print("\n1. 데이터 로딩 중...")
    
    # 데이터 로드
    df_students, df_survey = load_spreadsheet_data()
    
    if df_students is None or df_survey is None:
        print("❌ 데이터 로딩 실패")
        return
    
    print("✅ 데이터 로딩 완료")
    
    # 미응답자 찾기
    print("\n2. 미응답자 확인 중...")
    non_respondents = find_non_respondents(df_students, df_survey)
    
    if len(non_respondents) == 0:
        print("✨ 모든 교육생이 응답을 완료했습니다!")
        return
    
    print(f"📝 총 {len(non_respondents)}명의 미응답자가 있습니다.")
    
    # 이메일 발송
    print("\n3. 알림 이메일 발송 중...")
    success_count = 0
    
    for _, row in non_respondents.iterrows():
        if send_reminder_email(service, row['이름'], row['이메일']):
            success_count += 1
    
    print(f"\n✨ 작업 완료: {success_count}/{len(non_respondents)}명에게 이메일을 발송했습니다.")

if __name__ == "__main__":
    main() 