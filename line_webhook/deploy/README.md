# LINE OA Campaign Manager Webhook Deployment

## การตั้งค่า

1. คัดลอกไฟล์ `init.she.example` เป็น `init.sh`:
   ```bash
   cp init.she.example init.sh
   ```

2. แก้ไขไฟล์ `init.sh` ให้ถูกต้อง:
   - ตั้งค่า GCP account และ project ID
   - ตั้งค่า LINE Channel Access Token และ Channel Secret

## การ Deploy

รันคำสั่ง:
```bash
./deploy.sh
```

## ข้อกำหนด

- ต้องมี gcloud CLI ติดตั้งและ login แล้ว
- ต้องมี LINE Bot Channel Access Token และ Channel Secret
- ต้องมี Google Cloud Project ที่เปิดใช้งาน Cloud Functions API

## Environment Variables ที่จำเป็น

- `LINE_CHANNEL_ACCESS_TOKEN`: Token สำหรับเข้าถึง LINE Messaging API
- `LINE_CHANNEL_SECRET`: Secret key สำหรับตรวจสอบ webhook signature
