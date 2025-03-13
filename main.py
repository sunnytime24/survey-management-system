import os
from flask import Flask, request, jsonify, render_template
from notion_client import Client
from dotenv import load_dotenv
import smtplib
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from openai import OpenAI
import json

# 환경 변수 로드
load_dotenv()

app = Flask(__name__)

# Notion 클라이언트 설정
notion = Client(auth=os.getenv("NOTION_TOKEN"))

# OpenAI 클라이언트 설정
client = OpenAI(api_key=os.getenv("OPENAI_API_KEY"))

# FAQ 데이터베이스 ID
FAQ_DATABASE_ID = os.getenv("NOTION_FAQ_DATABASE_ID")

def send_email(subject, body):
    """이메일 전송 함수"""
    msg = MIMEMultipart()
    msg['From'] = os.getenv("GMAIL_USER")
    msg['To'] = os.getenv("ADMIN_EMAIL")
    msg['Subject'] = subject
    
    msg.attach(MIMEText(body, 'plain'))
    
    server = smtplib.SMTP('smtp.gmail.com', 587)
    server.starttls()
    server.login(os.getenv("GMAIL_USER"), os.getenv("GMAIL_APP_PASSWORD"))
    server.send_message(msg)
    server.quit()

def get_recommended_answer(question):
    """OpenAI를 사용하여 추천 답변 생성"""
    response = client.chat.completions.create(
        model="gpt-3.5-turbo",
        messages=[
            {"role": "system", "content": "당신은 교육 프로그램 운영자입니다. 질문에 대해 전문적이고 명확하게 답변해주세요."},
            {"role": "user", "content": question}
        ]
    )
    return response.choices[0].message.content

def add_to_faq(question, answer):
    """FAQ 데이터베이스에 새로운 Q&A 추가"""
    notion.pages.create(
        parent={"database_id": FAQ_DATABASE_ID},
        properties={
            "Question": {"title": [{"text": {"content": question}}]},
            "Answer": {"rich_text": [{"text": {"content": answer}}]}
        }
    )

@app.route('/')
def home():
    return render_template('index.html')

@app.route('/ask', methods=['POST'])
def ask_question():
    data = request.json
    name = data.get('name')
    organization = data.get('organization')
    question = data.get('question')
    
    # 추천 답변 생성
    recommended_answer = get_recommended_answer(question)
    
    # 이메일 내용 구성
    email_body = f"""
    새로운 질문이 접수되었습니다.
    
    이름: {name}
    소속: {organization}
    질문: {question}
    
    추천 답변:
    {recommended_answer}
    
    이 답변을 수정하거나 승인하시려면 관리자 페이지에서 처리해주세요.
    """
    
    # 이메일 전송
    send_email(f"새로운 질문: {name}", email_body)
    
    return jsonify({
        "status": "success",
        "message": "질문이 접수되었습니다. 관리자가 답변을 검토한 후 FAQ에 게시될 예정입니다."
    })

@app.route('/approve_answer', methods=['POST'])
def approve_answer():
    data = request.json
    question = data.get('question')
    answer = data.get('answer')
    
    # FAQ에 추가
    add_to_faq(question, answer)
    
    return jsonify({
        "status": "success",
        "message": "답변이 FAQ에 추가되었습니다."
    })

if __name__ == '__main__':
    app.run(debug=True) 