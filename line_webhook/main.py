import os
import asyncio
import threading
import logging
import yaml
from flask import Flask, request

# โหลด environment variables จากไฟล์ env.yaml
def load_env_vars():
    """โหลด environment variables จากไฟล์ env.yaml"""
    try:
        with open('env.yaml', 'r', encoding='utf-8') as file:
            env_data = yaml.safe_load(file)
            if env_data:
                for key, value in env_data.items():
                    if value:  # เฉพาะค่าที่ไม่ใช่ None หรือ empty
                        os.environ[key] = str(value)
                        print(f"Loaded env var: {key}")
    except FileNotFoundError:
        print("Warning: env.yaml file not found, using system environment variables")
    except Exception as e:
        print(f"Error loading env.yaml: {e}")

# โหลด environment variables
load_env_vars()

# LINE Bot SDK
from linebot.v3.exceptions import InvalidSignatureError
from linebot.v3 import WebhookHandler
from linebot.v3.webhooks import (
    MessageEvent,
    TextMessageContent
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


CHANNEL_ACCESS_TOKEN = os.environ.get("MANAGER_OA_LINE_CHANNEL_ACCESS_TOKEN", "")
CHANNEL_SECRET = os.environ.get("MANAGER_OA_LINE_CHANNEL_SECRET","")

print(f"MANAGER_OA_LINE_CHANNEL_ACCESS_TOKEN: {'SET' if CHANNEL_ACCESS_TOKEN else 'NOT SET'}")
print(f"MANAGER_OA_LINE_CHANNEL_SECRET: {'SET' if CHANNEL_SECRET else 'NOT SET'}")


configuration = Configuration(access_token=CHANNEL_ACCESS_TOKEN)
handler = WebhookHandler(CHANNEL_SECRET)
api_client = ApiClient(configuration)
line_bot_api = MessagingApi(api_client)
line_bot_blob_api = MessagingApiBlob(api_client)
from adk_runner_service import generate_text


app = Flask(__name__)

# ตั้งค่า logging สำหรับ Cloud Logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

@app.route("/", methods=["POST"])
def webhook_listening():
    try:
        # ดึงค่า Signature จาก header
        signature = request.headers.get("X-Line-Signature", "")
        logger.info(f"Received signature: {signature[:20]}...")

        # แปลง request body เป็น text
        body = request.get_data(as_text=True)
        logger.info(f"Request body length: {len(body)}")
        logger.info(f"Request body: {body}")

        # ตรวจสอบและส่งให้ handler จาก LINE SDK จัดการ
        if CHANNEL_ACCESS_TOKEN and CHANNEL_SECRET:
            logger.info("Processing webhook with LINE SDK")
            handler.handle(body, signature)
            logger.info("Webhook processed successfully")
        else:
            logger.error("ERROR: Missing LINE credentials, cannot process webhook")
            return "ERROR: Missing credentials", 500

        return "OK"
    except InvalidSignatureError as e:
        logger.error(f"Invalid signature error: {e}")
        return "Invalid signature", 400
    except Exception as e:
        import traceback
        logger.error(f"Unexpected error in webhook: {e}")
        logger.error(f"Traceback: {traceback.format_exc()}")
        return f"ERROR: {str(e)}", 500

@handler.add(MessageEvent, message=TextMessageContent)
def handle_text_message(event):
    user_id = event.source.user_id
    user_input = event.message.text
    
    logger.info(f"=== NEW MESSAGE RECEIVED ===")
    logger.info(f"User ID: {user_id}")
    logger.info(f"Message: {user_input}")
    logger.info(f"Reply Token: {event.reply_token}")
    
    try:
        # แสดง loading animation
        logger.info("Showing loading animation")
        line_bot_api.show_loading_animation(
            ShowLoadingAnimationRequest(chat_id=event.source.user_id)
        )
        
        # ใช้ synchronous wrapper ที่มีอยู่แล้วใน adk_runner_service
        logger.info("Calling ADK runner service")
        from adk_runner_service import generate_text_sync
        response = generate_text_sync(user_input, user_id)
        
        logger.info(f"ADK response: {response}")
        
        # ตรวจสอบว่าคำตอบมาจาก agent จริงหรือไม่
        if response and response.strip():
            # ส่งคำตอบจาก agent กลับไปยังผู้ใช้
            logger.info("Sending response to user")
            line_bot_api.reply_message_with_http_info(
                ReplyMessageRequest(
                    reply_token=event.reply_token,
                    messages=[TextMessage(text=response)])
            )
            logger.info(f"[SUCCESS] Response sent: {response[:100]}...")
        else:
            # ถ้า agent ไม่ตอบ ให้ log และไม่ส่งอะไรกลับ
            logger.warning(f"[NO RESPONSE] Agent did not provide valid response for: {user_input}")
        
    except Exception as e:
        import traceback
        logger.error(f"Error in handle_text_message: {e}")
        logger.error(f"Traceback: {traceback.format_exc()}")
        # ไม่ส่ง error message กลับ ให้ log error เท่านั้น
        logger.error(f"[ERROR] Failed to process message from {user_id}: {user_input}")

@app.route("/health", methods=["GET"])
def health_check():
    return "OK", 200

if __name__ == "__main__":
    port = int(os.environ.get("PORT", 8080))
    app.run(host="0.0.0.0", port=port, debug=False)