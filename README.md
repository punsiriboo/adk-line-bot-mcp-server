# LINE Bot Campaign Manager

LINE Bot ที่ใช้ Google ADK (Agent Development Kit) สำหรับสร้าง Campaign และ Flex Message ที่สวยงาม

## ฟีเจอร์

- 🤖 **AI Agent**: ใช้ Google ADK Agent สำหรับประมวลผลข้อความ
- 📱 **LINE Integration**: รับข้อความจาก LINE และตอบกลับด้วย Flex Message
- 🎨 **Flex Message**: สร้างข้อความที่สวยงามและมีฟังก์ชันครบถ้วน
- 🖼️ **Image Generation**: สร้างรูปภาพประกอบ Campaign
- 📄 **Document Analysis**: วิเคราะห์เอกสารและสร้าง Campaign

## การติดตั้ง

### 1. Clone Repository
```bash
git clone <repository-url>
cd adk-line-bot-mcp-server
```

### 2. ติดตั้ง Dependencies
```bash
pip install -r requirements.txt
```

### 3. ตั้งค่า Environment Variables
สร้างไฟล์ `.env` ในโฟลเดอร์ `line_oa_campaign_manager/`:

```env
# Gemini API Key
GEMINI_API_KEY=your_gemini_api_key_here

# LINE Bot Configuration
LINE_CHANNEL_ACCESS_TOKEN=your_line_channel_access_token_here
LINE_CHANNEL_SECRET=your_line_channel_secret_here
LINE_DESTINATION_USER_ID=your_line_destination_user_id_here
```

### 4. รัน Local Development
```bash
python main.py
```

## การใช้งาน

### Google Cloud Functions
```bash
# Deploy to Google Cloud Functions
gcloud functions deploy webhook_listening \
  --runtime python39 \
  --trigger-http \
  --allow-unauthenticated \
  --source . \
  --entry-point webhook_listening
```

### LINE Bot Setup
1. สร้าง LINE Bot Channel
2. ตั้งค่า Webhook URL: `https://your-function-url/webhook`
3. เปิดใช้งาน Messaging API

## โครงสร้างไฟล์

```
├── line_oa_campaign_manager/
│   ├── agent.py              # ADK Agent configuration
│   └── __init__.py
├── line_webhook/
│   └── line_webhook.py       # LINE webhook handlers
├── gemini_service.py         # Service layer for ADK Agent
├── main.py                   # Main entry point
├── requirements.txt          # Python dependencies
└── README.md                # Documentation
```

## API Endpoints

- `POST /webhook` - LINE webhook endpoint
- `GET /health` - Health check

## การพัฒนา

### เพิ่มฟีเจอร์ใหม่
1. แก้ไข `agent.py` สำหรับ Agent configuration
2. เพิ่ม handlers ใน `line_webhook.py`
3. อัปเดต `gemini_service.py` สำหรับ business logic

### Testing
```bash
# Test webhook locally
python -m pytest tests/
```

## License

MIT License
