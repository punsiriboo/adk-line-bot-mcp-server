"""
Main entry point สำหรับ LINE Bot Campaign Manager
"""
import os
from dotenv import load_dotenv
from line_webhook.line_webhook import webhook_listening

# โหลด environment variables
load_dotenv()

if __name__ == "__main__":
    # ตรวจสอบ environment variables
    required_vars = [
        "LINE_CHANNEL_ACCESS_TOKEN",
        "LINE_CHANNEL_SECRET", 
        "GEMINI_API_KEY"
    ]
    
    missing_vars = [var for var in required_vars if not os.getenv(var)]
    if missing_vars:
        print(f"Missing required environment variables: {missing_vars}")
        print("Please check your .env file")
        exit(1)
    
    print("LINE Bot Campaign Manager is ready!")
    print("Environment variables loaded successfully")
    print("Webhook endpoint: /webhook")
