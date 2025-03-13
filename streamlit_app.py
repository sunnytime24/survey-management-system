import streamlit as st
import os
from dotenv import load_dotenv
from notion_client import Client
from openai import OpenAI
from email_validator import validate_email, EmailNotValidError

# 환경 변수 로드
load_dotenv()

# 임시 FAQ 데이터
SAMPLE_FAQS = [
    {
        "제목": "자주 묻는 질문 1",
        "내용": "이것은 첫 번째 FAQ의 답변입니다."
    },
    {
        "제목": "자주 묻는 질문 2",
        "내용": "이것은 두 번째 FAQ의 답변입니다."
    }
]

# API 키 설정
try:
    notion = Client(auth=os.getenv("NOTION_TOKEN"))
except Exception as e:
    st.error("Notion API 연결에 실패했습니다. 환경 변수를 확인해주세요.")
    notion = None

# OpenAI 클라이언트 설정
client = OpenAI(api_key=os.getenv("OPENAI_API_KEY"))

# 페이지 설정
st.set_page_config(
    page_title="FAQ 시스템",
    page_icon="❓",
    layout="wide"
)

# 제목
st.title("FAQ 시스템")

# 사이드바
with st.sidebar:
    st.header("설정")
    selected_option = st.selectbox(
        "메뉴 선택",
        ["FAQ 검색", "문의하기"]
    )

if selected_option == "FAQ 검색":
    # FAQ 검색 섹션
    st.header("FAQ 검색")
    search_query = st.text_input("검색어를 입력하세요")
    
    if search_query:
        try:
            if notion:
                # Notion 데이터베이스에서 FAQ 검색
                database_id = os.getenv("NOTION_FAQ_DATABASE_ID")
                response = notion.databases.query(
                    database_id=database_id,
                    filter={
                        "or": [
                            {
                                "property": "Title",
                                "title": {
                                    "contains": search_query
                                }
                            },
                            {
                                "property": "Content",
                                "rich_text": {
                                    "contains": search_query
                                }
                            }
                        ]
                    }
                )
                
                if not response["results"]:
                    st.info("검색 결과가 없습니다.")
                else:
                    for page in response["results"]:
                        try:
                            title = page["properties"]["Title"]["title"][0]["text"]["content"]
                            content = page["properties"]["Content"]["rich_text"][0]["text"]["content"]
                            with st.expander(title):
                                st.write(content)
                        except (KeyError, IndexError) as e:
                            st.error(f"데이터 형식 오류: {str(e)}")
                            st.json(page)  # 디버깅을 위해 페이지 데이터 출력
            else:
                # 임시 데이터에서 검색
                found = False
                for faq in SAMPLE_FAQS:
                    if search_query.lower() in faq["제목"].lower() or search_query.lower() in faq["내용"].lower():
                        with st.expander(faq["제목"]):
                            st.write(faq["내용"])
                            found = True
                
                if not found:
                    st.info("검색 결과가 없습니다.")
                    
        except Exception as e:
            st.error(f"검색 중 오류가 발생했습니다: {str(e)}")
            st.info("현재 임시 데이터를 사용합니다.")
            
            # 임시 데이터 표시
            for faq in SAMPLE_FAQS:
                with st.expander(faq["제목"]):
                    st.write(faq["내용"])

else:
    # 문의하기 섹션
    st.header("문의하기")
    
    with st.form("contact_form"):
        name = st.text_input("이름")
        email = st.text_input("이메일")
        message = st.text_area("문의 내용")
        
        submitted = st.form_submit_button("문의하기")
        
        if submitted:
            try:
                # 이메일 유효성 검사
                validate_email(email)
                
                # OpenAI를 사용하여 응답 생성
                response = client.chat.completions.create(
                    model="gpt-3.5-turbo",
                    messages=[
                        {"role": "system", "content": "당신은 고객 서비스 담당자입니다."},
                        {"role": "user", "content": f"다음 문의에 대해 답변해주세요: {message}"}
                    ]
                )
                
                st.success("문의가 성공적으로 전송되었습니다!")
                st.info(f"답변: {response.choices[0].message.content}")
                
            except EmailNotValidError:
                st.error("유효하지 않은 이메일 주소입니다.")
            except Exception as e:
                st.error(f"오류가 발생했습니다: {str(e)}")

# Notion 설정 안내
with st.sidebar:
    st.markdown("---")
    st.markdown("### Notion 설정 방법")
    st.markdown("""
    1. Notion API 토큰 발급받기
    2. 데이터베이스 생성 및 공유
    3. 데이터베이스 ID 복사
    4. .env 파일에 설정하기
    """)
    if not notion:
        st.warning("현재 Notion API가 연결되지 않았습니다.") 