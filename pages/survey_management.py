import streamlit as st
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
from openai import OpenAI
import os
from dotenv import load_dotenv
import smtplib
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
import httpx

load_dotenv()

# OpenAI 클라이언트 설정
try:
    api_key = os.getenv("OPENAI_API_KEY")
    if not api_key:
        st.error("OpenAI API 키가 설정되지 않았습니다. .env 파일을 확인해주세요.")
        client = None
    else:
        client = OpenAI(
            api_key=api_key,
            http_client=httpx.Client(
                timeout=httpx.Timeout(60.0, connect=5.0)
            )
        )
except Exception as e:
    st.error(f"OpenAI 클라이언트 초기화 중 오류가 발생했습니다: {str(e)}")
    client = None

# 이메일 설정
EMAIL_ADDRESS = os.getenv("EMAIL_ADDRESS")
EMAIL_PASSWORD = os.getenv("EMAIL_PASSWORD")

def send_reminder_email(recipient_email, name):
    subject = "설문조사 참여 안내"
    body = f"""
    안녕하세요 {name}님,
    
    아직 설문조사에 참여하지 않으신 것 같습니다.
    귀하의 의견이 매우 중요하오니, 설문조사에 참여해 주시면 감사하겠습니다.
    
    감사합니다.
    """
    
    msg = MIMEMultipart()
    msg['From'] = EMAIL_ADDRESS
    msg['To'] = recipient_email
    msg['Subject'] = subject
    msg.attach(MIMEText(body, 'plain'))
    
    try:
        with smtplib.SMTP_SSL('smtp.gmail.com', 465) as smtp:
            smtp.login(EMAIL_ADDRESS, EMAIL_PASSWORD)
            smtp.send_message(msg)
        return True
    except Exception as e:
        st.error(f"이메일 발송 실패: {str(e)}")
        return False

def analyze_survey_results(survey_data):
    if client is None:
        return "OpenAI API 클라이언트가 초기화되지 않아 분석을 수행할 수 없습니다."
        
    try:
        # OpenAI를 사용한 설문 결과 분석
        analysis_prompt = f"""
        다음 설문조사 결과를 분석해주세요:
        {survey_data.to_string()}
        
        다음 항목들을 포함해서 분석해주세요:
        1. 주요 트렌드
        2. 특이사항
        3. 개선 제안사항
        """
        
        response = client.chat.completions.create(
            model="gpt-4",
            messages=[{"role": "user", "content": analysis_prompt}]
        )
        
        return response.choices[0].message.content
    except Exception as e:
        return f"분석 중 오류가 발생했습니다: {str(e)}"

st.title("설문조사 관리 시스템")

tab1, tab2, tab3, tab4 = st.tabs([
    "설문조사 결과 업로드",
    "설문조사 대상자 업로드",
    "리마인더 이메일 발송",
    "설문결과 분석"
])

with tab1:
    st.header("설문조사 결과 업로드")
    upload_method = st.radio("업로드 방식 선택", ["파일 업로드", "URL 입력"])
    
    if upload_method == "파일 업로드":
        uploaded_file = st.file_uploader("설문조사 결과 파일 선택 (Excel 또는 CSV)", type=["xlsx", "csv"])
        if uploaded_file:
            try:
                if uploaded_file.name.endswith('.csv'):
                    # CSV 파일 읽기 옵션 추가
                    survey_results = pd.read_csv(
                        uploaded_file,
                        encoding='utf-8',
                        on_bad_lines='skip',  # 문제가 있는 라인 건너뛰기
                        low_memory=False,     # 대용량 파일 처리
                        dtype=str             # 모든 컬럼을 문자열로 읽기
                    )
                else:
                    survey_results = pd.read_excel(uploaded_file)
                
                # 데이터 정제
                survey_results = survey_results.replace({'\n': ' ', '\r': ''}, regex=True)
                
                st.session_state['survey_results'] = survey_results
                st.success("설문조사 결과가 성공적으로 업로드되었습니다!")
                st.write("데이터 미리보기:")
                st.dataframe(survey_results.head())
                
                # 데이터 정보 표시
                st.write("데이터 정보:")
                st.write(f"- 총 행 수: {len(survey_results)}")
                st.write(f"- 총 열 수: {len(survey_results.columns)}")
                st.write("- 컬럼 목록:")
                st.write(survey_results.columns.tolist())
            except Exception as e:
                st.error(f"파일 읽기 중 오류가 발생했습니다: {str(e)}")
    else:
        survey_url = st.text_input("설문조사 결과 URL 입력")
        if st.button("URL에서 데이터 가져오기"):
            try:
                # URL에서 CSV 파일 읽기 옵션 추가
                survey_results = pd.read_csv(
                    survey_url,
                    encoding='utf-8',
                    on_bad_lines='skip',      # 문제가 있는 라인 건너뛰기
                    low_memory=False,         # 대용량 파일 처리
                    dtype=str                 # 모든 컬럼을 문자열로 읽기
                )
                
                # 데이터 정제
                survey_results = survey_results.replace({'\n': ' ', '\r': ''}, regex=True)
                
                st.session_state['survey_results'] = survey_results
                st.success("설문조사 결과를 성공적으로 가져왔습니다!")
                st.write("데이터 미리보기:")
                st.dataframe(survey_results.head())
                
                # 데이터 정보 표시
                st.write("데이터 정보:")
                st.write(f"- 총 행 수: {len(survey_results)}")
                st.write(f"- 총 열 수: {len(survey_results.columns)}")
                st.write("- 컬럼 목록:")
                st.write(survey_results.columns.tolist())
            except Exception as e:
                st.error(f"URL에서 데이터를 가져오는데 실패했습니다: {str(e)}")
                st.write("문제 해결을 위한 제안:")
                st.write("1. URL이 올바른지 확인해주세요.")
                st.write("2. CSV 파일이 올바른 형식인지 확인해주세요.")
                st.write("3. 파일이 너무 큰 경우, 파일 업로드 방식을 사용해보세요.")

with tab2:
    st.header("설문조사 대상자 업로드")
    target_upload_method = st.radio("대상자 업로드 방식 선택", ["파일 업로드", "URL 입력"], key="target_upload")
    
    if target_upload_method == "파일 업로드":
        target_file = st.file_uploader("대상자 명단 파일 선택 (Excel 또는 CSV)", type=["xlsx", "csv"], key="target_file")
        if target_file:
            if target_file.name.endswith('.csv'):
                target_list = pd.read_csv(target_file)
            else:
                target_list = pd.read_excel(target_file)
            st.session_state['target_list'] = target_list
            st.success("대상자 명단이 성공적으로 업로드되었습니다!")
            st.dataframe(target_list)
    else:
        target_url = st.text_input("대상자 명단 URL 입력")
        if st.button("URL에서 대상자 명단 가져오기"):
            try:
                target_list = pd.read_csv(target_url)
                st.session_state['target_list'] = target_list
                st.success("대상자 명단을 성공적으로 가져왔습니다!")
                st.dataframe(target_list)
            except Exception as e:
                st.error(f"URL에서 데이터를 가져오는데 실패했습니다: {str(e)}")

with tab3:
    st.header("리마인더 이메일 발송")
    if 'survey_results' in st.session_state and 'target_list' in st.session_state:
        # 미응답자 식별
        respondents = set(st.session_state['survey_results']['이메일'])
        non_respondents = st.session_state['target_list'][
            ~st.session_state['target_list']['이메일'].isin(respondents)
        ]
        
        st.write(f"총 {len(non_respondents)} 명의 미응답자가 있습니다.")
        st.dataframe(non_respondents)
        
        if st.button("리마인더 이메일 발송"):
            success_count = 0
            for _, row in non_respondents.iterrows():
                if send_reminder_email(row['이메일'], row['이름']):
                    success_count += 1
            
            st.success(f"{success_count}명에게 리마인더 이메일을 발송했습니다.")
    else:
        st.warning("설문조사 결과와 대상자 명단을 먼저 업로드해주세요.")

with tab4:
    st.header("설문결과 분석")
    if 'survey_results' in st.session_state:
        survey_results = st.session_state['survey_results']
        
        # 타임스탬프 컬럼 제외
        timestamp_columns = survey_results.columns[survey_results.columns.str.lower().str.contains('timestamp|시간|날짜|date|time')]
        analysis_data = survey_results.drop(columns=timestamp_columns)
        
        # 기본적인 통계 시각화
        st.subheader("응답 통계")
        
        # 수치형 데이터에 대한 히스토그램
        numeric_cols = analysis_data.select_dtypes(include=['float64', 'int64']).columns
        if len(numeric_cols) > 0:
            for col in numeric_cols:
                fig = px.histogram(analysis_data, x=col, title=f"{col} 분포")
                st.plotly_chart(fig)
        
        # 범주형 데이터에 대한 파이 차트
        categorical_cols = analysis_data.select_dtypes(include=['object']).columns
        if len(categorical_cols) > 0:
            for col in categorical_cols:
                if analysis_data[col].nunique() < 10:  # 너무 많은 카테고리가 있는 경우 제외
                    fig = px.pie(analysis_data, names=col, title=f"{col} 분포")
                    st.plotly_chart(fig)
        
        # OpenAI를 사용한 분석
        st.subheader("AI 분석 결과")
        if st.button("AI 분석 시작"):
            analysis_result = analyze_survey_results(analysis_data)
            st.write(analysis_result)
    else:
        st.warning("설문조사 결과를 먼저 업로드해주세요.") 