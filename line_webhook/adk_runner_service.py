"""
ADK Runner Service สำหรับรับข้อความจาก LINE และส่งต่อไปยัง ADK Agent
"""

import logging
from google.adk.runners import Runner
from google.adk.sessions import InMemorySessionService
from google.genai import types
from line_oa_campaign_manager.agent import line_oa_agent

# ตั้งค่า logger
logger = logging.getLogger(__name__)

# ---------------------------
# Config
# ---------------------------
APP_NAME = "line_oa_campaign_manager"
DEFAULT_USER_ID = "line_user"
# ใช้ InMemorySessionService เพื่อหลีกเลี่ยงปัญหา database schema ใน Cloud Run
session_service = InMemorySessionService()
print(f"[ADK] InMemorySessionService initialized successfully")

runner = Runner(
    agent=line_oa_agent,
    app_name=APP_NAME,
    session_service=session_service,
)

# เก็บ mapping: user_id -> session_id (อยู่ในหน่วยความจำของโปรเซสนี้)
# ลบ cache เพื่อให้สร้าง session ใหม่เสมอ (แก้ปัญหา database schema)
user_sessions: dict[str, str] = {}

# เก็บ runner instances แยกตาม user เพื่อป้องกัน event loop conflicts
user_runners: dict[str, Runner] = {}


# -------------------------
async def get_or_create_session(user_id: str) -> str:
    """สร้าง session ใหม่เสมอเพื่อหลีกเลี่ยงปัญหา database schema"""
    # สร้าง session ใหม่เสมอเพื่อหลีกเลี่ยงปัญหา database schema
    try:
        new_session = await session_service.create_session(
            app_name=APP_NAME,
            user_id=user_id,
            state={},  # ใส่ state เริ่มต้นได้ตามต้องการ
        )
        user_sessions[user_id] = new_session.id
        print(f"[ADK] Created new session for {user_id}: {new_session.id}")
        return new_session.id
    except Exception as e:
        print(f"[ADK] Error creating session: {e}")
        import traceback
        print(f"[ADK] Session creation traceback: {traceback.format_exc()}")
        # Fallback: สร้าง session ID แบบง่าย
        fallback_session_id = f"fallback_{user_id}_{hash(user_id) % 10000}"
        user_sessions[user_id] = fallback_session_id
        print(f"[ADK] Using fallback session ID: {fallback_session_id}")
        return fallback_session_id


# ---------------------------
# Event processing
# ---------------------------
async def process_agent_response(event) -> str | None:
    """คืนข้อความสุดท้าย (final response) หาก event นั้นเป็น final หรือมี text content"""
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

    # ตรวจสอบว่ามี text content หรือไม่ (ไม่จำเป็นต้องเป็น final response เสมอ)
    if event.content and event.content.parts:
        for part in event.content.parts:
            if getattr(part, "text", None) and part.text.strip():
                text_content = part.text.strip()
                print(f"[ADK] Found text content: {text_content[:100]}...")
                
                # ถ้าเป็น final response ให้คืนทันที
                if event.is_final_response():
                    print(f"[ADK] Final response detected: {text_content[:100]}...")
                    return text_content
                
                # ถ้าไม่ใช่ final response แต่มี text content ให้เก็บไว้
                # (จะคืนในภายหลังถ้าไม่มี final response)
                return text_content

    # ถ้าเป็น final response แต่ไม่มี text content
    if event.is_final_response():
        print("[ADK] Final response detected but no text content")
        return None

    return None

async def generate_text(user_input: str, user_id: str | None = None) -> str:
    """
    รับข้อความจากผู้ใช้และส่งต่อไปยัง ADK Agent
    - ถ้า user_id ซ้ำ จะอ้างอิง session เดิมเสมอ
    """
    import asyncio

    current_user_id = user_id or DEFAULT_USER_ID
    logger.info(f"[ADK] Processing message from {current_user_id}: {user_input[:100]}...")

    try:
        # 1) ดึง/สร้าง session
        session_id = await get_or_create_session(current_user_id)
        logger.info(f"[ADK] Using session: {session_id}")

        # 2) เตรียม content
        content = types.Content(role="user", parts=[types.Part(text=user_input)])

        # 3) ใช้ runner แยกตาม user เพื่อป้องกัน event loop conflicts
        if current_user_id not in user_runners:
            print(f"[ADK] Creating new runner for user: {current_user_id}")
            user_runners[current_user_id] = Runner(
                agent=line_oa_agent,
                app_name=APP_NAME,
                session_service=session_service,
            )
        
        user_runner = user_runners[current_user_id]
        
        # 4) รัน agent และดึงคำตอบสุดท้าย
        async def run_once() -> str | None:
            final_text = None
            last_text_response = None
            event_count = 0
            try:
                print(f"[ADK] Starting agent run for session: {session_id}")
                
                # ใช้ try-except เพื่อจัดการกับ async generator
                try:
                    async_gen = user_runner.run_async(
                        user_id=current_user_id,
                        session_id=session_id,
                        new_message=content,
                    )
                    
                    try:
                        async for event in async_gen:
                            event_count += 1
                            print(f"[ADK] Event {event_count}: {event.id}")
                            
                            resp = await process_agent_response(event)
                            if resp is not None:
                                # ถ้าเป็น final response ให้คืนทันที
                                if event.is_final_response():
                                    final_text = resp
                                    print(f"[ADK] Final response received: {resp[:100]}...")
                                    break
                                else:
                                    # เก็บ response ล่าสุดไว้เผื่อไม่มี final response
                                    last_text_response = resp
                                    print(f"[ADK] Non-final response received: {resp[:100]}...")
                                
                        print(f"[ADK] Agent run completed. Total events: {event_count}")
                        
                        # ถ้าไม่มี final response แต่มี text response ให้ใช้ตัวล่าสุด
                        if final_text is None and last_text_response is not None:
                            final_text = last_text_response
                            print(f"[ADK] Using last text response: {final_text[:100]}...")
                    
                    finally:
                        # ปิด async generator อย่างปลอดภัย
                        try:
                            await async_gen.aclose()
                        except Exception as close_error:
                            # ไม่ log error นี้เพราะเป็นปัญหาใน MCP library
                            pass
                    
                except Exception as gen_error:
                    print(f"[ADK] Error in async generator: {gen_error}")
                    return None
                
            except RuntimeError as e:
                if "Event loop is closed" in str(e):
                    print("[ADK] Event loop closed error detected")
                    return None
                else:
                    print(f"[ADK] Runtime error: {e}")
                    raise
            except Exception as e:
                print(f"[ADK] Error in run_once: {e}")
                import traceback
                print(f"[ADK] Traceback: {traceback.format_exc()}")
                return None
            return final_text

        # กำหนด timeout 60 วินาที เพื่อรอคำตอบจาก ADK Agent
        # เพิ่ม retry mechanism สำหรับ MCP toolset ที่ไม่เสถียร
        max_retries = 3
        for attempt in range(max_retries):
            try:
                print(f"[ADK] Starting agent with 60s timeout (attempt {attempt + 1}/{max_retries})...")
                final_response_text = await asyncio.wait_for(run_once(), timeout=60.0)
                print(f"[ADK] Agent completed successfully")
                break  # สำเร็จแล้ว ออกจาก loop
            except asyncio.TimeoutError:
                print(f"[ADK] Timeout: agent took more than 60 seconds (attempt {attempt + 1})")
                if attempt == max_retries - 1:
                    return None
                print(f"[ADK] Retrying...")
                await asyncio.sleep(2)  # รอ 2 วินาทีก่อน retry
            except RuntimeError as e:
                if "Event loop is closed" in str(e):
                    print("[ADK] Event loop closed error in wait_for")
                    return None
                elif "cancel scope" in str(e).lower():
                    print(f"[ADK] MCP cancel scope error (attempt {attempt + 1}): {e}")
                    if attempt == max_retries - 1:
                        return None
                    print(f"[ADK] Retrying...")
                    await asyncio.sleep(2)  # รอ 2 วินาทีก่อน retry
                else:
                    print(f"[ADK] Runtime error in wait_for: {e}")
                    raise
            except Exception as e:
                print(f"[ADK] Unexpected error in wait_for (attempt {attempt + 1}): {e}")
                if attempt == max_retries - 1:
                    return None
                print(f"[ADK] Retrying...")
                await asyncio.sleep(2)  # รอ 2 วินาทีก่อน retry

        # 5) ส่งเฉพาะคำตอบจาก agent จริงๆ
        if final_response_text and final_response_text.strip():
            print(f"[ADK] Agent response: {final_response_text[:100]}...")
            return final_response_text
        
        print("[ADK] No response received from agent")
        
        # ถ้า agent ไม่ตอบเลย ให้ส่งข้อความ fallback
        fallback_message = "ขออภัยครับ ฉันไม่สามารถตอบคำถามนี้ได้ในขณะนี้ กรุณาลองใหม่อีกครั้งครับ"
        print(f"[ADK] Using fallback response: {fallback_message}")
        return fallback_message

    except Exception as e:
        import traceback
        print(f"[ADK] Error in generate_text: {e}")
        print(f"[ADK] Traceback: {traceback.format_exc()}")
        return None


# ---------------------------
# Synchronous wrapper for Flask
# ---------------------------
def generate_text_sync(user_input: str, user_id: str | None = None) -> str:
    """
    Synchronous wrapper สำหรับ generate_text เพื่อใช้กับ Flask
    """
    import asyncio
    import threading
    import signal
    import os
    
    logger.info(f"[ADK-SYNC] Starting sync wrapper for user: {user_id}")
    logger.info(f"[ADK-SYNC] Input message: {user_input}")
    
    # ใช้ threading เพื่อหลีกเลี่ยงปัญหา event loop
    result_container = [None]
    error_container = [None]
    loop_container = [None]
    
    def run_in_thread():
        try:
            # สร้าง event loop ใหม่ใน thread นี้
            loop = asyncio.new_event_loop()
            asyncio.set_event_loop(loop)
            loop_container[0] = loop
            
            try:
                logger.info(f"[ADK-SYNC] Running async function in thread...")
                result = loop.run_until_complete(generate_text(user_input, user_id))
                result_container[0] = result
                logger.info(f"[ADK-SYNC] Completed successfully - Result: {result}")
            except Exception as e:
                logger.error(f"[ADK-SYNC] Error in async function: {e}")
                error_container[0] = e
            finally:
                # ปิด loop อย่างปลอดภัย
                try:
                    # รอสักครู่เพื่อให้ async operations เสร็จสิ้น
                    import time
                    time.sleep(0.2)
                    
                    # ยกเลิก pending tasks ก่อน
                    pending = asyncio.all_tasks(loop)
                    if pending:
                        print(f"[ADK-SYNC] Cancelling {len(pending)} pending tasks")
                        for task in pending:
                            if not task.done():
                                task.cancel()
                        
                        # รอให้ tasks ยกเลิกเสร็จ
                        try:
                            if pending:
                                loop.run_until_complete(asyncio.gather(*pending, return_exceptions=True))
                        except Exception as gather_error:
                            print(f"[ADK-SYNC] Error gathering tasks: {gather_error}")
                    
                    # รอสักครู่เพื่อให้ subprocess cleanup เสร็จ
                    time.sleep(0.3)
                    
                    # ปิด loop
                    if not loop.is_closed():
                        loop.close()
                        print("[ADK-SYNC] Event loop closed safely")
                        
                except Exception as close_error:
                    print(f"[ADK-SYNC] Error closing loop: {close_error}")
                    
        except Exception as e:
            import traceback
            print(f"[ADK-SYNC] Error in thread: {e}")
            print(f"[ADK-SYNC] Traceback: {traceback.format_exc()}")
            error_container[0] = e
    
    # รันใน thread พร้อม timeout
    thread = threading.Thread(target=run_in_thread, daemon=True)
    thread.start()
    thread.join(timeout=100)  # timeout 100 วินาที
    
    # ถ้า thread ยังทำงานอยู่ ให้ยกเลิก
    if thread.is_alive():
        print("[ADK-SYNC] Thread timeout - forcing cleanup")
        try:
            if loop_container[0] and not loop_container[0].is_closed():
                # ส่งสัญญาณให้หยุด
                loop_container[0].call_soon_threadsafe(lambda: None)
                # รอสักครู่เพื่อให้ cleanup เสร็จ
                import time
                time.sleep(0.2)
        except Exception as cleanup_error:
            print(f"[ADK-SYNC] Cleanup error: {cleanup_error}")
        return None
    
    if error_container[0]:
        print(f"[ADK-SYNC] Thread error: {error_container[0]}")
        return None  # ส่ง None แทนข้อความ error
    
    if result_container[0]:
        logger.info(f"[ADK-SYNC] Returning result: {result_container[0][:100]}...")
        return result_container[0]
    else:
        logger.warning(f"[ADK-SYNC] No result returned for user: {user_id}")
        return None  # ส่ง None แทนข้อความ error
