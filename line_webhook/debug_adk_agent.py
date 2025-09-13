#!/usr/bin/env python3
"""
Debug ADK Agent เพื่อดูว่าทำไมไม่ตอบ
"""

import os
import asyncio
import logging

# ตั้งค่า environment variables จาก env.yaml
os.environ['MANAGER_OA_LINE_CHANNEL_ACCESS_TOKEN'] = '6ujkgHjkMPHVPDd58CRrZXj06uhr/YKmSv9b1Yf/s2FW6eV3D4nmICMwrUUo40zjmbmwf0S5Ac6r2NwOaWojreYa+OZWjfm1M+zRcqglbAX1BFxJbPEDqhVLP1ufd5XV295OhPo6RSlf4pJFVJtkPgdB04t89/1O/w1cDnyilFU='
os.environ['MANAGER_OA_LINE_CHANNEL_SECRET'] = 'd3e5a0e1f6a905a870cbf79b5efa25aa'
os.environ['GEMINI_API_KEY'] = 'AIzaSyCTym6JUmYmk5LcB74ZmHzDjiEMcmsSC1M'
os.environ['DEST_OA_LINE_CHANNEL_ACCESS_TOKEN'] = 'C+cnWWvekKl2ehZk6jwKWl8gPjoFZF+on4GVxOU5v+FiF7iBGGfv3yX+eYjkR/SObQU2vGpcsgpnnxvAP7jbeST5rn0qIzq3ReGHqJBEkUimuP5RzH//vg5+mayVpT9Sv48BooyyiWUxWgghqd/oXQdB04t89/1O/w1cDnyilFU='
os.environ['DEST_OA_LINE_DESTINATION_USER_ID'] = 'U40e607358f4cf9bc434d0b09cb982c5b'

# ตั้งค่า logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)

async def debug_adk_agent():
    """Debug ADK Agent เพื่อดูว่าทำไมไม่ตอบ"""
    print("=" * 60)
    print("Debug ADK Agent")
    print("=" * 60)
    
    try:
        from adk_runner_service import generate_text
        
        print("Testing ADK Agent with message: 'hello'")
        response = await generate_text("hello", "test_user")
        
        print(f"ADK Response: {response}")
        print(f"Response type: {type(response)}")
        print(f"Response length: {len(response) if response else 0}")
        
        if response:
            print("✅ ADK Agent responded successfully")
        else:
            print("❌ ADK Agent did not respond")
            
    except Exception as e:
        print(f"❌ Error: {e}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    asyncio.run(debug_adk_agent())
