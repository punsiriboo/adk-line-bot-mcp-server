# Import libraries ที่ใช้
import os
import functions_framework
from dotenv import load_dotenv

# LINE SDK
from linebot.v3.exceptions import InvalidSignatureError
from linebot.v3 import WebhookHandler
from linebot.v3.webhooks import (
    MessageEvent,
    TextMessageContent,
    ImageMessageContent,
    FileMessageContent,
)
from linebot.v3.messaging import (
    Configuration,
    ApiClient,
    MessagingApi,
    MessagingApiBlob,
    ReplyMessageRequest,
    TextMessage,
    ShowLoadingAnimationRequest,
)


CHANNEL_ACCESS_TOKEN = os.environ.get("LINE_CHANNEL_ACCESS_TOKEN")
CHANNEL_SECRET = os.environ.get("LINE_CHANNEL_SECRET")

# ตรวจสอบว่ามี environment variables หรือไม่
if not CHANNEL_ACCESS_TOKEN or not CHANNEL_SECRET:
    raise ValueError("LINE_CHANNEL_ACCESS_TOKEN และ LINE_CHANNEL_SECRET ต้องถูกตั้งค่าใน environment variables")

configuration = Configuration(access_token=CHANNEL_ACCESS_TOKEN)
handler = WebhookHandler(CHANNEL_SECRET)
api_client = ApiClient(configuration)
line_bot_api = MessagingApi(api_client)
line_bot_blob_api = MessagingApiBlob(api_client)

# import ฟังก์ชันจาก service ที่เรียก ADK Agent
from adk_runner_service import generate_text_sync, image_understanding_sync, document_understanding_sync

# Function สำหรับรับ webhook จาก LINE
@functions_framework.http
def webhook_listening(request):
    # ดึงค่า Signature จาก header
    signature = request.headers["X-Line-Signature"]

    # แปลง request body เป็น text
    body = request.get_data(as_text=True)
    print("Request body: " + body)

    # ตรวจสอบและส่งให้ handler จาก LINE SDK จัดการ
    try:
        handler.handle(body, signature)
    except InvalidSignatureError:
        print("Invalid signature. Please check your channel access token/channel secret.")

    return "OK"

# กรณีข้อความเป็นประเภท Text
@handler.add(MessageEvent, message=TextMessageContent)
def handle_text_message(event):
    # แสดง loading animation ระหว่างประมวลผล
    line_bot_api.show_loading_animation(
        ShowLoadingAnimationRequest(chat_id=event.source.user_id)
    )

    # ส่งข้อความไปให้ ADK Agent ประมวลผล
    gemini_reponse = generate_text_sync(event.message.text)

    # ตอบกลับข้อความที่ได้จาก Gemini
    line_bot_api.reply_message(
        ReplyMessageRequest(
            reply_token=event.reply_token,
            messages=[TextMessage(text=gemini_reponse)],
        )
    )

# กรณีข้อความเป็นรูปภาพ
@handler.add(MessageEvent, message=ImageMessageContent)
def handle_image_message(event):
    # แสดง loading animation ระหว่างประมวลผล
    line_bot_api.show_loading_animation_with_http_info(
        ShowLoadingAnimationRequest(chat_id=event.source.user_id)
    )

    # ดึง binary ของภาพจาก LINE server
    message_content = line_bot_blob_api.get_message_content(message_id=event.message.id)

    # ส่งไปให้ ADK Agent วิเคราะห์ภาพ
    gemini_reponse = image_understanding_sync(message_content)

    # ตอบกลับผลลัพธ์จาก Gemini
    line_bot_api.reply_message(
        ReplyMessageRequest(
            reply_token=event.reply_token,
            messages=[TextMessage(text=gemini_reponse)],
        )
    )

# กรณีข้อความเป็นไฟล์เอกสาร
@handler.add(MessageEvent, message=FileMessageContent)
def handle_file_message(event):
    # ดึง binary ของไฟล์จาก LINE server
    doc_content = line_bot_blob_api.get_message_content(message_id=event.message.id)

    # ส่งไปให้ ADK Agent วิเคราะห์เนื้อหาในเอกสาร
    gemini_reponse = document_understanding_sync(doc_content)

    # ตอบกลับผลลัพธ์จาก Gemini
    line_bot_api.reply_message(
        ReplyMessageRequest(
            reply_token=event.reply_token,
            messages=[TextMessage(text=gemini_reponse)],
        )
    )