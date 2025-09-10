# Import libraries ที่ใช้
import os
import sys
from flask import Flask, request
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
print(f"CHANNEL_ACCESS_TOKEN: {'SET' if CHANNEL_ACCESS_TOKEN else 'NOT SET'}")
print(f"CHANNEL_SECRET: {'SET' if CHANNEL_SECRET else 'NOT SET'}")

if not CHANNEL_ACCESS_TOKEN or not CHANNEL_SECRET:
    print("ERROR: Missing required environment variables")
    print("Required: LINE_CHANNEL_ACCESS_TOKEN, LINE_CHANNEL_SECRET")
    # ไม่ raise error เพื่อให้ app start ได้
    # raise ValueError("LINE_CHANNEL_ACCESS_TOKEN และ LINE_CHANNEL_SECRET ต้องถูกตั้งค่าใน environment variables")

configuration = Configuration(access_token=CHANNEL_ACCESS_TOKEN)
handler = WebhookHandler(CHANNEL_SECRET)
api_client = ApiClient(configuration)
line_bot_api = MessagingApi(api_client)
line_bot_blob_api = MessagingApiBlob(api_client)

# import ฟังก์ชันจาก service ที่เรียก ADK Agent
try:
    from adk_runner_service import generate_text_sync, image_understanding_sync, document_understanding_sync
    print("✓ ADK runner service imported successfully")
except ImportError as e:
    print(f"✗ Failed to import ADK runner service: {e}")
    # สร้าง fallback functions
    def generate_text_sync(text):
        return "ขออภัย บริการ ADK Agent ไม่พร้อมใช้งานในขณะนี้"
    def image_understanding_sync(image_content):
        return "ขออภัย บริการวิเคราะห์รูปภาพไม่พร้อมใช้งานในขณะนี้"
    def document_understanding_sync(doc_content):
        return "ขออภัย บริการวิเคราะห์เอกสารไม่พร้อมใช้งานในขณะนี้"

# สร้าง Flask app
app = Flask(__name__)

# Function สำหรับรับ webhook จาก LINE
@app.route("/", methods=["POST"])
def webhook_listening():
    try:
        # ดึงค่า Signature จาก header
        signature = request.headers.get("X-Line-Signature", "")
        print(f"Received signature: {signature[:20]}...")

        # แปลง request body เป็น text
        body = request.get_data(as_text=True)
        print(f"Request body length: {len(body)}")

        # ตรวจสอบและส่งให้ handler จาก LINE SDK จัดการ
        if CHANNEL_ACCESS_TOKEN and CHANNEL_SECRET:
            handler.handle(body, signature)
        else:
            print("ERROR: Missing LINE credentials, cannot process webhook")
            return "ERROR: Missing credentials", 500

        return "OK"
    except InvalidSignatureError as e:
        print(f"Invalid signature error: {e}")
        return "Invalid signature", 400
    except Exception as e:
        import traceback
        print(f"Unexpected error in webhook: {e}")
        print(f"Traceback: {traceback.format_exc()}")
        return f"ERROR: {str(e)}", 500

# Health check endpoint
@app.route("/health", methods=["GET"])
def health_check():
    return "OK", 200

# กรณีข้อความเป็นประเภท Text
@handler.add(MessageEvent, message=TextMessageContent)
def handle_text_message(event):
    try:
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
    except Exception as e:
        import traceback
        print(f"Error in handle_text_message: {e}")
        print(f"Traceback: {traceback.format_exc()}")
        
        # ส่งข้อความแจ้งข้อผิดพลาด
        try:
            line_bot_api.reply_message(
                ReplyMessageRequest(
                    reply_token=event.reply_token,
                    messages=[TextMessage(text="ขออภัย เกิดข้อผิดพลาดในการประมวลผล กรุณาลองใหม่อีกครั้ง")],
                )
            )
        except Exception as reply_error:
            print(f"Failed to send error reply: {reply_error}")

# กรณีข้อความเป็นรูปภาพ
@handler.add(MessageEvent, message=ImageMessageContent)
def handle_image_message(event):
    try:
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
    except Exception as e:
        import traceback
        print(f"Error in handle_image_message: {e}")
        print(f"Traceback: {traceback.format_exc()}")
        
        # ส่งข้อความแจ้งข้อผิดพลาด
        try:
            line_bot_api.reply_message(
                ReplyMessageRequest(
                    reply_token=event.reply_token,
                    messages=[TextMessage(text="ขออภัย ไม่สามารถวิเคราะห์รูปภาพได้ กรุณาลองใหม่อีกครั้ง")],
                )
            )
        except Exception as reply_error:
            print(f"Failed to send error reply: {reply_error}")

# กรณีข้อความเป็นไฟล์เอกสาร
@handler.add(MessageEvent, message=FileMessageContent)
def handle_file_message(event):
    try:
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
    except Exception as e:
        import traceback
        print(f"Error in handle_file_message: {e}")
        print(f"Traceback: {traceback.format_exc()}")
        
        # ส่งข้อความแจ้งข้อผิดพลาด
        try:
            line_bot_api.reply_message(
                ReplyMessageRequest(
                    reply_token=event.reply_token,
                    messages=[TextMessage(text="ขออภัย ไม่สามารถวิเคราะห์เอกสารได้ กรุณาลองใหม่อีกครั้ง")],
                )
            )
        except Exception as reply_error:
            print(f"Failed to send error reply: {reply_error}")

# รัน server สำหรับ Cloud Run
if __name__ == "__main__":
    port = int(os.environ.get("PORT", 8080))
    print(f"Starting server on port {port}")
    print(f"Environment variables:")
    print(f"  PORT: {os.environ.get('PORT', 'NOT SET')}")
    print(f"  LINE_CHANNEL_ACCESS_TOKEN: {'SET' if os.environ.get('LINE_CHANNEL_ACCESS_TOKEN') else 'NOT SET'}")
    print(f"  LINE_CHANNEL_SECRET: {'SET' if os.environ.get('LINE_CHANNEL_SECRET') else 'NOT SET'}")
    print(f"  GEMINI_API_KEY: {'SET' if os.environ.get('GEMINI_API_KEY') else 'NOT SET'}")
    print(f"  NPX_PATH: {os.environ.get('NPX_PATH', 'NOT SET')}")
    
    try:
        app.run(host="0.0.0.0", port=port, debug=False)
    except Exception as e:
        print(f"Error starting server: {e}")
        sys.exit(1)