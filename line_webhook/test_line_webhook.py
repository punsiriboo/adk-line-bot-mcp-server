#!/usr/bin/env python3
"""
ทดสอบ LINE Webhook เพื่อดู log ใน Cloud Logging
"""

import json
import logging
import os
from unittest.mock import patch

# ตั้งค่า environment variables
os.environ['MANAGER_OA_LINE_CHANNEL_ACCESS_TOKEN'] = 'test_channel_token'
os.environ['MANAGER_OA_LINE_CHANNEL_SECRET'] = 'test_channel_secret'
os.environ['GEMINI_API_KEY'] = 'test_gemini_key'

# ตั้งค่า logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)

def test_line_webhook():
    """ทดสอบ LINE webhook เพื่อดู log"""
    print("=" * 60)
    print("ทดสอบ LINE Webhook เพื่อดู Log")
    print("=" * 60)
    
    try:
        from main import app
        
        # สร้าง test client
        with app.test_client() as client:
            # สร้าง LINE webhook payload
            webhook_data = {
                "events": [
                    {
                        "type": "message",
                        "message": {
                            "type": "text",
                            "text": "check qouta message"
                        },
                        "source": {
                            "user_id": "U7a8652113444f5bd27cc9b87b7f326e3"
                        },
                        "reply_token": "test_reply_token_123"
                    }
                ]
            }
            
            print("Sending webhook request...")
            print(f"Payload: {json.dumps(webhook_data, indent=2)}")
            
            # Mock LINE signature validation
            with patch('main.handler') as mock_handler:
                # Mock handler.handle to call our message handler
                def mock_handle(body, signature):
                    import json
                    data = json.loads(body)
                    for event_data in data.get('events', []):
                        if event_data.get('type') == 'message':
                            # Create mock event object
                            class MockEvent:
                                def __init__(self, event_data):
                                    self.source = MockSource(event_data['source'])
                                    self.message = MockMessage(event_data['message'])
                                    self.reply_token = event_data.get('reply_token', '')
                            
                            class MockSource:
                                def __init__(self, source_data):
                                    self.user_id = source_data['user_id']
                            
                            class MockMessage:
                                def __init__(self, message_data):
                                    self.text = message_data['text']
                            
                            # Import and call the message handler
                            from main import handle_text_message
                            handle_text_message(MockEvent(event_data))
                
                mock_handler.handle = mock_handle
                
                # ส่ง webhook request
                response = client.post('/', 
                                     data=json.dumps(webhook_data),
                                     content_type='application/json',
                                     headers={'X-Line-Signature': 'test_signature'})
                
                print(f"Response status: {response.status_code}")
                print(f"Response data: {response.get_data(as_text=True)}")
                
                if response.status_code == 200:
                    print("✅ Webhook processed successfully")
                else:
                    print(f"❌ Webhook failed with status: {response.status_code}")
                    
    except Exception as e:
        print(f"❌ Test failed: {e}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    test_line_webhook()
