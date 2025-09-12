#!/usr/bin/env python3
"""
ทดสอบ ADK Runner Service แบบง่าย
"""

import sys
import os
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from adk_runner_service import generate_text_sync

def test_adk_bot():
    """ทดสอบการทำงานของ ADK bot"""
    print("=" * 50)
    print("ทดสอบ ADK Bot")
    print("=" * 50)
    
    # ทดสอบข้อความง่ายๆ
    test_messages = [
        "สวัสดี",
        "คุณเป็นใคร",
        "ช่วยแนะนำตัวเองหน่อย",
        "check quota message"
    ]
    
    for i, message in enumerate(test_messages, 1):
        print(f"\n[{i}] ทดสอบข้อความ: '{message}'")
        print("-" * 30)
        
        try:
            response = generate_text_sync(message, f"test_user_{i}")
            print(f"คำตอบ: {response}")
            
            if "ไม่สามารถประมวลผล" in response or "เกิดข้อผิดพลาด" in response:
                print("❌ การทดสอบล้มเหลว - ได้รับข้อความ error")
            else:
                print("✅ การทดสอบสำเร็จ")
                
        except Exception as e:
            print(f"❌ Error: {e}")
            import traceback
            print(f"Traceback: {traceback.format_exc()}")
    
    print("\n" + "=" * 50)
    print("การทดสอบเสร็จสิ้น")
    print("=" * 50)

if __name__ == "__main__":
    test_adk_bot()
