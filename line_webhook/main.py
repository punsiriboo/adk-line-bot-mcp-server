import os
import asyncio
import threading
from flask import Flask, request

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

@handler.add(MessageEvent, message=TextMessageContent)
def handle_text_message(event):
    user_id = event.source.user_id
    user_input = event.message.text
    
    # ใช้ threading เพื่อเรียกใช้ async function
    def run_async_generate():
        def run_in_thread():
            loop = asyncio.new_event_loop()
            asyncio.set_event_loop(loop)
            try:
                return loop.run_until_complete(generate_text(user_input, user_id))
            finally:
                loop.close()
        
        # ใช้ thread เพื่อไม่ให้บล็อก main thread
        result = [None]
        exception = [None]
        
        def target():
            try:
                result[0] = run_in_thread()
            except Exception as e:
                exception[0] = e
        
        thread = threading.Thread(target=target)
        thread.start()
        thread.join(timeout=30)  # timeout 30 วินาที
        
        if thread.is_alive():
            return "ขออภัย การประมวลผลใช้เวลานานเกินไป กรุณาลองใหม่อีกครั้ง"
        
        if exception[0]:
            print(f"Error in async call: {exception[0]}")
            return "ขออภัย เกิดข้อผิดพลาดในการประมวลผล กรุณาลองใหม่อีกครั้ง"
        
        return result[0] or "ขออภัย ไม่สามารถประมวลผลข้อความได้ กรุณาลองใหม่อีกครั้ง"
    
    response = run_async_generate()
    
    line_bot_api.reply_message_with_http_info(
        ReplyMessageRequest(
            reply_token=event.reply_token,
            messages=[TextMessage(text=response)])
    )
    print(f"Received text message: {event.message.text}")
    print(f"Response: {response}")

@app.route("/health", methods=["GET"])
def health_check():
    return "OK", 200

if __name__ == "__main__":
    port = int(os.environ.get("PORT", 8080))
    app.run(host="0.0.0.0", port=port, debug=False)