import streamlit as st
import openai
from notion_client import Client
import json
import datetime
import requests

# 페이지 설정
st.set_page_config(
    page_title="AI PM 교육 챗봇 & QnA",
    page_icon="🤖",
    layout="wide"
)

# OpenAI 클라이언트 설정
client = openai.OpenAI(api_key=st.secrets["openai"]["api_key"])

# Notion API 설정
NOTION_TOKEN = st.secrets["notion"]["token"]
FAQ_DATABASE_ID = st.secrets["notion"]["database_id"]
NOTION_API_URL = "https://api.notion.com/v1"

# 세션 상태 초기화
if 'is_admin' not in st.session_state:
    st.session_state.is_admin = False

headers = {
    "Authorization": f"Bearer {NOTION_TOKEN}",
    "Content-Type": "application/json",
    "Notion-Version": "2022-06-28"
}

def save_to_notion(name, department, question, answer):
    """QnA를 Notion 데이터베이스에 저장합니다."""
    try:
        url = f"{NOTION_API_URL}/pages"
        
        data = {
            "parent": {"database_id": FAQ_DATABASE_ID},
            "properties": {
                "이름": {"title": [{"text": {"content": name}}]},
                "소속": {"rich_text": [{"text": {"content": department}}]},
                "질문": {"rich_text": [{"text": {"content": question}}]},
                "답변": {"rich_text": [{"text": {"content": answer}}]},
                "등록일": {"date": {"start": datetime.datetime.now().isoformat()}}
            }
        }
        
        response = requests.post(url, headers=headers, json=data)
        response.raise_for_status()
        return True
    except Exception as e:
        st.error(f"Notion 저장 중 오류 발생: {str(e)}")
        return False

def get_faqs_from_notion():
    """Notion 데이터베이스에서 QnA 목록을 가져옵니다."""
    try:
        url = f"{NOTION_API_URL}/databases/{FAQ_DATABASE_ID}/query"
        data = {
            "sorts": [{"property": "등록일", "direction": "descending"}]
        }
        
        response = requests.post(url, headers=headers, json=data)
        response.raise_for_status()
        
        results = response.json().get("results", [])
        faqs = []
        
        for page in results:
            props = page.get("properties", {})
            question = props.get("질문", {}).get("rich_text", [{}])[0].get("text", {}).get("content", "")
            answer = props.get("답변", {}).get("rich_text", [{}])[0].get("text", {}).get("content", "")
            
            if question and answer:
                faqs.append({"question": question, "answer": answer})
        
        return faqs
    except Exception as e:
        st.error(f"FAQ 로드 중 오류 발생: {str(e)}")
        return []

def get_chatbot_response(name, department, question):
    """OpenAI를 사용하여 챗봇 응답을 생성합니다."""
    try:
        client = openai.OpenAI(api_key=st.secrets["openai"]["api_key"])
        
        messages = [
            {"role": "system", "content": """당신은 SK AI Camp 1기 교육 프로그램의 전문 상담사입니다. 
            교육생들의 질문에 친절하고 전문적으로 답변해주세요.
            답변할 때는 다음 내용을 참고해주세요:
            
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
            {"role": "user", "content": f"안녕하세요, 저는 {department}의 {name}입니다. {question}"}
        ]
        
        response = client.chat.completions.create(
            model="gpt-3.5-turbo",
            messages=messages,
            temperature=0.7,
            max_tokens=1000
        )
        
        return response.choices[0].message.content
    except Exception as e:
        st.error(f"챗봇 응답 생성 중 오류 발생: {str(e)}")
        return None

def main():
    st.title("🤖 AI PM 교육 챗봇 & QnA")
    
    tab1, tab2 = st.tabs(["💬 챗봇", "📚 QnA"])
    
    with tab1:
        st.header("AI PM 교육 챗봇")
        st.markdown("""
            안녕하세요! AI PM 교육 관련 궁금한 점을 물어보세요.
            교육 과정, 일정, 커리큘럼 등 다양한 질문에 답변해드립니다.
        """)
        
        with st.form("chatbot_form"):
            name = st.text_input("이름", placeholder="홍길동")
            department = st.text_input("소속", placeholder="전략기획팀")
            question = st.text_area("질문", placeholder="교육 과정에 대해 궁금한 점을 입력해주세요.")
            submitted = st.form_submit_button("질문하기")
            
            if submitted:
                if not name or not department or not question:
                    st.error("모든 항목을 입력해주세요.")
                else:
                    with st.spinner("답변을 생성하고 있습니다..."):
                        answer = get_chatbot_response(name, department, question)
                        if answer:
                            st.success("답변이 생성되었습니다!")
                            st.markdown(f"**답변**: {answer}")
                            
                            # FAQ로 저장
                            if save_to_notion(name, department, question, answer):
                                st.info("✅ 질문과 답변이 FAQ 데이터베이스에 저장되었습니다.")
    
    with tab2:
        st.header("자주 묻는 질문 (FAQ)")
        
        # FAQ 새로고침 버튼
        if st.button("QnA 새로고침"):
            st.session_state.faqs = get_faqs_from_notion()
        
        # FAQ 목록이 없으면 로드
        if "faqs" not in st.session_state:
            st.session_state.faqs = get_faqs_from_notion()
        
        # FAQ 표시
        for i, faq in enumerate(st.session_state.faqs, 1):
            with st.expander(f"Q{i}. {faq['question'][:100]}..."):
                st.markdown(f"**답변**: {faq['answer']}")

if __name__ == "__main__":
    main() 