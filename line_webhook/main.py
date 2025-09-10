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
    def run_async_in_thread():
        """รัน async function ใน thread แยกเพื่อหลีกเลี่ยงปัญหา cancel scope"""
        try:
            # สร้าง event loop ใหม่ใน thread นี้
            loop = asyncio.new_event_loop()
            asyncio.set_event_loop(loop)
            
            async def process_message():
                try:
                    user_id = event.source.user_id
                    line_bot_api.show_loading_animation(
                        ShowLoadingAnimationRequest(chat_id=user_id)
                    )
                    print(f"User ID: {user_id}")
                    print(f"Message: {event.message.text}")

                    gemini_response = await generate_text(
                        user_input=event.message.text,
                        user_id=user_id
                    )
                        
                    print(f"Gemini Response: {gemini_response}")

                    line_bot_api.reply_message(
                        ReplyMessageRequest(
                            reply_token=event.reply_token,
                            messages=[TextMessage(text=gemini_response)],
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
            
            # รัน async function ใน event loop ของ thread นี้
            loop.run_until_complete(process_message())
            
        except Exception as e:
            print(f"Error in thread: {e}")
        finally:
            # ปิด event loop
            try:
                loop.close()
            except:
                pass
    
    # รันใน thread แยก
    thread = threading.Thread(target=run_async_in_thread)
    thread.daemon = True
    thread.start()

@app.route("/health", methods=["GET"])
def health_check():
    return "OK", 200

if __name__ == "__main__":
    port = int(os.environ.get("PORT", 8080))
    app.run(host="0.0.0.0", port=port, debug=False)