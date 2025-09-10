"""
ADK Runner Service สำหรับรับข้อความจาก LINE และส่งต่อไปยัง ADK Agent (simplified)
"""

from google.adk.runners import Runner
from google.adk.sessions import DatabaseSessionService
from google.genai import types
from line_oa_campaign_manager.agent import root_agent

# ---------------------------
# Config
# ---------------------------
APP_NAME = "line_oa_campaign_manager"
DEFAULT_USER_ID = "line_user"
DB_URL = "sqlite:///./agent_session.db"

# ---------------------------
# Services
# ---------------------------
session_service = DatabaseSessionService(db_url=DB_URL)
runner = Runner(
    agent=root_agent,
    app_name=APP_NAME,
    session_service=session_service,
)

# เก็บ mapping: user_id -> session_id (อยู่ในหน่วยความจำของโปรเซสนี้)
user_sessions: dict[str, str] = {}


# ---------------------------
# Session helpers
# ---------------------------
async def get_or_create_session(user_id: str) -> str:
    """ดึงหรือสร้าง session สำหรับ user_id เดิมจะอ้างอิง session เดิมเสมอ"""
    if user_id in user_sessions:
        return user_sessions[user_id]

    new_session = await session_service.create_session(
        app_name=APP_NAME,
        user_id=user_id,
        state={},  # ใส่ state เริ่มต้นได้ตามต้องการ
    )
    user_sessions[user_id] = new_session.id
    return new_session.id


# ---------------------------
# Event processing
# ---------------------------
async def process_agent_response(event) -> str | None:
    """คืนข้อความสุดท้าย (final response) หาก event นั้นเป็น final"""
    # debug เล็กน้อย (ไม่บังคับ)
    print(f"[event] id={event.id} author={event.author}")

    # พิมพ์ text part (ถ้ามี) เพื่อดู trace ระหว่างรัน
    if event.content and event.content.parts:
        for part in event.content.parts:
            if getattr(part, "text", None):
                txt = part.text.strip()
                if txt:
                    print(f"  text: {txt[:500]}")  # limit log

            if getattr(part, "tool_response", None):
                print(f"  tool: {part.tool_response.output}")

            if getattr(part, "executable_code", None):
                print("  code generated")
            if getattr(part, "code_execution_result", None):
                print(f"  code result: {part.code_execution_result.outcome}")

    # ถ้าเป็น final ให้ดึงข้อความแรกที่เป็น text ออกมาเป็นคำตอบ
    if event.is_final_response():
        if event.content and event.content.parts:
            for part in event.content.parts:
                if getattr(part, "text", None) and part.text.strip():
                    return part.text.strip()
        return "ขออภัย ไม่สามารถประมวลผลข้อความได้ กรุณาลองใหม่อีกครั้ง"

    return None


# ---------------------------
# Public API
# ---------------------------
async def generate_text(user_input: str, user_id: str | None = None) -> str:
    """
    รับข้อความจากผู้ใช้และส่งต่อไปยัง ADK Agent
    - ถ้า user_id ซ้ำ จะอ้างอิง session เดิมเสมอ
    """
    import asyncio

    current_user_id = user_id or DEFAULT_USER_ID

    try:
        # 1) ดึง/สร้าง session
        session_id = await get_or_create_session(current_user_id)

        # 2) เตรียม content
        content = types.Content(role="user", parts=[types.Part(text=user_input)])

        # 3) รัน agent และดึงคำตอบสุดท้าย
        async def run_once() -> str | None:
            final_text = None
            async for event in runner.run_async(
                user_id=current_user_id,
                session_id=session_id,
                new_message=content,
            ):
                resp = await process_agent_response(event)
                if resp is not None:
                    final_text = resp
            return final_text

        # กำหนด timeout 30 วินาที
        try:
            final_response_text = await asyncio.wait_for(run_once(), timeout=30.0)
        except asyncio.TimeoutError:
            print("Timeout: agent took more than 30s")
            return "ขออภัย การประมวลผลใช้เวลานานเกินไป กรุณาลองใหม่อีกครั้ง"

        # 4) Fallback หากยังไม่ได้คำตอบ
        return final_response_text or "ขออภัย ไม่สามารถประมวลผลข้อความได้ กรุณาลองใหม่อีกครั้ง"

    except Exception as e:
        import traceback
        print(f"Error in generate_text: {e}")
        print(traceback.format_exc())
        # หากมีปัญหาเกี่ยวกับ MCP/Runner ให้แจ้ง fallback แบบสั้น
        return (
            "ขออภัย เกิดข้อผิดพลาดในการประมวลผล "
            "กรุณาลองใหม่อีกครั้ง หรือให้รายละเอียดเพิ่มเติม"
        )
