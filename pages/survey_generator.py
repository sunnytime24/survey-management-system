import streamlit as st
from google.oauth2.credentials import Credentials
from googleapiclient.discovery import build
from google.oauth2 import service_account
import json
import base64
import pandas as pd
import smtplib
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart

# 페이지 설정
st.set_page_config(
    page_title="설문지 생성기",
    page_icon="📝",
    layout="wide"
)

# 세션 상태 초기화
if 'is_admin' not in st.session_state:
    st.session_state.is_admin = False

# 관리자 접근 제어
if not st.session_state.is_admin:
    st.error("관리자 로그인이 필요한 페이지입니다.")
    st.stop()

def send_survey_email(email_list, form_url, title):
    """설문지 링크를 이메일로 발송합니다."""
    try:
        sender_email = st.secrets["email"]["gmail_user"]
        sender_password = st.secrets["email"]["gmail_password"]

        for recipient in email_list:
            msg = MIMEMultipart()
            msg['From'] = sender_email
            msg['To'] = recipient
            msg['Subject'] = f"[설문조사] {title}"

            body = f"""안녕하세요,
            
{title} 설문조사에 참여해 주시기 바랍니다.

아래 링크를 클릭하여 설문에 응답해 주세요:
{form_url}

감사합니다."""

            msg.attach(MIMEText(body, 'plain'))

            with smtplib.SMTP_SSL('smtp.gmail.com', 465) as server:
                server.login(sender_email, sender_password)
                server.send_message(msg)

        return True
    except Exception as e:
        st.error(f"이메일 발송 중 오류 발생: {str(e)}")
        return False

def create_google_form(title, questions):
    """Google Form을 생성하고 질문들을 추가합니다."""
    try:
        # 서비스 계정 인증 정보 로드
        credentials_info = json.loads(st.secrets["gcp"]["service_account"])
        credentials = service_account.Credentials.from_service_account_info(
            credentials_info,
            scopes=['https://www.googleapis.com/auth/forms',
                   'https://www.googleapis.com/auth/drive']
        )

        # Forms API 서비스 생성
        service = build('forms', 'v1', credentials=credentials)

        # 폼 생성
        form = {
            'info': {
                'title': title,
                'documentTitle': title
            }
        }
        
        result = service.forms().create(body=form).execute()
        form_id = result['formId']

        # 질문 추가
        requests = []
        for question in questions:
            request = {
                'createItem': {
                    'item': {
                        'title': question,
                        'questionItem': {
                            'question': {
                                'required': True,
                                'textQuestion': {
                                    'paragraph': True
                                }
                            }
                        }
                    },
                    'location': {
                        'index': 0
                    }
                }
            }
            requests.append(request)

        update = {
            'requests': requests
        }
        
        service.forms().batchUpdate(formId=form_id, body=update).execute()
        
        # 응답 URL 반환 (편집 URL이 아닌 설문 응답용 URL)
        form_url = f"https://docs.google.com/forms/d/{form_id}/viewform"
        return form_url
    
    except Exception as e:
        st.error(f"Google Form 생성 중 오류 발생: {str(e)}")
        return None

def main():
    st.title("📝 설문지 생성기")
    
    # 탭 생성
    tab1, tab2 = st.tabs(["설문지 생성", "발송 대상자 관리"])
    
    with tab1:
        # JSON 파일 업로드
        uploaded_file = st.file_uploader("설문지 JSON 파일 업로드", type=['json'])
        
        if uploaded_file:
            try:
                questions_data = json.load(uploaded_file)
                questions = questions_data.get("questions", [])
                
                st.header("업로드된 질문 목록")
                for i, q in enumerate(questions, 1):
                    st.write(f"{i}. {q}")
                
                with st.form("create_form"):
                    title = st.text_input("설문지 제목", placeholder="설문지 제목을 입력하세요")
                    submitted = st.form_submit_button("Google Form 생성")
                    
                    if submitted and title:
                        with st.spinner("Google Form을 생성하고 있습니다..."):
                            form_url = create_google_form(title, questions)
                            if form_url:
                                st.success("Google Form이 생성되었습니다!")
                                st.markdown(f"[설문지 링크]({form_url})")
                                # 생성된 폼 URL을 세션에 저장
                                st.session_state.form_url = form_url
                                st.session_state.form_title = title
                
            except Exception as e:
                st.error(f"JSON 파일 처리 중 오류 발생: {str(e)}")
    
    with tab2:
        st.header("발송 대상자 관리")
        
        # 이메일 주소 입력 방식 선택
        input_method = st.radio(
            "이메일 주소 입력 방식 선택",
            ["직접 입력", "CSV 파일 업로드"]
        )
        
        email_list = []
        
        if input_method == "직접 입력":
            email_input = st.text_area(
                "이메일 주소 입력 (한 줄에 하나씩)",
                placeholder="example1@sk.com\nexample2@sk.com"
            )
            if email_input:
                email_list = [email.strip() for email in email_input.split("\n") if email.strip()]
        
        else:  # CSV 파일 업로드
            uploaded_csv = st.file_uploader("이메일 주소가 포함된 CSV 파일 업로드", type=['csv'])
            if uploaded_csv:
                try:
                    df = pd.read_csv(uploaded_csv)
                    email_column = st.selectbox("이메일 주소가 포함된 열 선택", df.columns)
                    if email_column:
                        email_list = df[email_column].dropna().tolist()
                except Exception as e:
                    st.error(f"CSV 파일 처리 중 오류 발생: {str(e)}")
        
        # 이메일 목록 표시
        if email_list:
            st.write(f"총 {len(email_list)}명의 발송 대상자가 있습니다:")
            for email in email_list:
                st.write(f"- {email}")
        
        # 설문지 발송
        if st.button("설문지 발송") and email_list and hasattr(st.session_state, 'form_url'):
            with st.spinner("설문지를 발송하고 있습니다..."):
                if send_survey_email(email_list, st.session_state.form_url, st.session_state.form_title):
                    st.success(f"총 {len(email_list)}명에게 설문지가 발송되었습니다!")
                else:
                    st.error("설문지 발송 중 오류가 발생했습니다.")

if __name__ == "__main__":
    main() 