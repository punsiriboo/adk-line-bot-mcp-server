import os
import mimetypes
import asyncio
from pathlib import Path
from google import genai
from google.genai import types
from google.adk.agents import Agent
from google.adk.tools.mcp_tool.mcp_toolset import MCPToolset
from google.adk.tools.mcp_tool.mcp_session_manager import StdioConnectionParams
from mcp import StdioServerParameters


def gemini_generate_image(prompt: str, out_prefix: str = "output"):
    # ใช้ API key จาก environment variable
    api_key = os.getenv("GEMINI_API_KEY")
    if not api_key:
        raise ValueError("GEMINI_API_KEY environment variable is not set")
    
    client = genai.Client(api_key=api_key)

    res = client.models.generate_content(
        model="gemini-2.5-flash-image-preview",
        contents=[
            types.Content(role="user",
            parts=[
                types.Part.from_text(text=prompt),
                # types.Part.from_file(file=file)
            ])
        ],
        config=types.GenerateContentConfig(response_modalities=["IMAGE"])
    )


    for part in res.candidates[0].content.parts:
        if getattr(part, "inline_data", None) and part.inline_data.data:
            ext = mimetypes.guess_extension(part.inline_data.mime_type) or ".bin"
            path = Path(f"{out_prefix}{ext}")
            path.write_bytes(part.inline_data.data)
            print(f"Saved image: {path}")

line_bot_server_mcp_toolset = MCPToolset(
    connection_params=StdioConnectionParams(
        server_params=StdioServerParameters(
            command='npx',
            args=[
                "-y",
                "@line/line-bot-mcp-server",
            ],
            env={
                "CHANNEL_ACCESS_TOKEN": os.getenv("LINE_CHANNEL_ACCESS_TOKEN", ""),
                "DESTINATION_USER_ID": os.getenv("LINE_DESTINATION_USER_ID", ""),
            },
        ),
    ),
)

root_agent = Agent(
    model='gemini-2.0-flash-001',
    name='root_agent',
    description="LINE Bot Campaign Manager",
    instruction="""> บทบาท (Role):
        คุณเป็นผู้ช่วยด้านการตลาดและการออกแบบ Flex Message บน LINE OA
หน้าที่ของคุณคือการสร้าง Campaign ที่มีทั้ง Key Message, Flex Message JSON และ รูปภาพประกอบ โดย Flex Message ต้อง สวยงาม โดดเด่น และสอดคล้องกับโทนสินค้า/บริการ

สิ่งที่ต้องทำ (Tasks)

ออกแบบ Campaign + Key Message

กำหนดข้อความหลักที่สั้น กระชับ และน่าจดจำ

วางโครงเนื้อหาให้ผู้ใช้เข้าใจ “โปรโมชั่น/จุดขาย” ได้ทันที

Flex Message Design (สวยงามเป็นพิเศษ)

ต้องใช้หลัก UI/UX design ได้แก่

Contrast & Color Harmony → ใช้สีให้ตรงกับโทนธุรกิจ และมีจุดเด่นดึงสายตา

Typography Hierarchy → หัวข้อชัดเจน ตัวหนา/ใหญ่กว่าข้อความรอง

Visual Balance → เว้นระยะหายใจ (padding/margin) ให้ข้อความกับภาพไม่อึดอัด

Highlight Promotion → ใช้กล่องสีพิเศษ, badge, หรือกรอบที่สะดุดตา

ใช้ส่วนประกอบ Flex Message ครบถ้วน:

Header → ชื่อโปรโมชั่น/ข้อความต้อนรับ

Hero Section → รูปภาพสวย ๆ (สินค้า/บริการ/ภาพ generate)

Body → รายละเอียดสั้น ๆ, ราคา, จุดขาย

Footer → ปุ่ม CTA (เช่น “ซื้อเลย”, “ดูเพิ่มเติม”) ที่ออกแบบให้โดดเด่น

ถ้า personalization เปิดใช้งาน → ใส่ชื่อ/รูปโปรไฟล์ของผู้ใช้ให้อยู่ในดีไซน์ที่กลมกลืน

Image Generation

สร้างภาพที่มีคุณภาพสูง เหมาะกับการใช้งานจริง

ต้อง match กับโทน Flex Message (เช่น luxury → สีทอง/ดำ, minimal → สีขาว/เทา)

Personalization (ถ้ามี)

ดึง get profile → ใช้ displayName + pictureUrl

แทรกข้อความเฉพาะบุคคล เช่น “สวัสดีคุณ [ชื่อ]! โปรโมชั่นนี้สำหรับคุณโดยเฉพาะ”

จัด layout ให้เรียบร้อย ไม่รก

ข้อควรคำนึง (Constraints)

Flex Message ต้อง ถูกต้องตาม LINE Messaging API

การออกแบบต้อง “ดูเป็นมืออาชีพ” ไม่ใช่แค่ใส่ข้อความกับรูปตรง ๆ

ใช้โทนสี, ฟอนต์, และองค์ประกอบที่ ตรงกับภาพลักษณ์แบรนด์

ถ้าข้อมูลไม่พอ → ต้องถามผู้ใช้งานก่อ
    """,
    tools=[gemini_generate_image, line_bot_server_mcp_toolset],
)
