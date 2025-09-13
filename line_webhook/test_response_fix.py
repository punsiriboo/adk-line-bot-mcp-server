#!/usr/bin/env python3
"""
ทดสอบการแก้ไขปัญหา ADK response ที่ไม่ส่งผลลัพธ์กลับมา
"""

import asyncio
import sys
import os

# เพิ่ม path เพื่อให้สามารถ import modules ได้
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from adk_runner_service import generate_text_sync

def test_response_fix():
    """ทดสอบการแก้ไขปัญหา response"""
    print("=== ทดสอบการแก้ไขปัญหา ADK Response ===")
    
    # ทดสอบข้อความที่เคยมีปัญหา
    test_messages = [
        "hellocheck qouta message",
        "สวัสดี",
        "ช่วยฉันหน่อย",
        "test message"
    ]
    
    for i, message in enumerate(test_messages, 1):
        print(f"\n--- ทดสอบที่ {i}: {message} ---")
        
        try:
            # ทดสอบด้วย user_id เดียวกันเพื่อใช้ session เดิม
            user_id = "test_user_123"
            response = generate_text_sync(message, user_id)
            
            if response:
                print(f"✅ ได้รับ response: {response[:100]}...")
            else:
                print("❌ ไม่ได้รับ response")
                
        except Exception as e:
            print(f"❌ Error: {e}")
    
    print("\n=== การทดสอบเสร็จสิ้น ===")

if __name__ == "__main__":
    test_response_fix()
