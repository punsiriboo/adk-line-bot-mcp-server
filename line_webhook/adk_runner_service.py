"""
ADK Runner Service สำหรับรับข้อความจาก LINE และส่งต่อไปยัง ADK Agent
"""
import os
import asyncio
from google.adk.runners import Runner, InMemorySessionService
from google.genai import types
from line_oa_campaign_manager.agent import root_agent

# Configuration
APP_NAME = "line_oa_campaign_manager"
USER_ID = "line_user"

# Global session service และ runner - ใช้ session เดียวกันสำหรับ user เดียวกัน
session_service = InMemorySessionService()
runner = Runner(
    agent=root_agent,
    app_name=APP_NAME,
    session_service=session_service,
)

# Dictionary เพื่อเก็บ session_id ของแต่ละ user
user_sessions = {}

async def get_or_create_session(user_id: str):
    """ดึงหรือสร้าง session สำหรับ user"""
    if user_id in user_sessions:
        session_id = user_sessions[user_id]
        print(f"Using existing session for user {user_id}: {session_id}")
        return session_id
    else:
        # สร้าง session ใหม่สำหรับ user
        new_session = await session_service.create_session(
            app_name=APP_NAME,
            user_id=user_id,
            state={},
        )
        session_id = new_session.id
        user_sessions[user_id] = session_id
        print(f"Created new session for user {user_id}: {session_id}")
        return session_id


async def process_agent_response(event):
    """Process and display agent response events."""
    # Log basic event info
    print(f"Event ID: {event.id}, Author: {event.author}")

    # Check for specific parts first
    has_specific_part = False
    if event.content and event.content.parts:
        for part in event.content.parts:
            if hasattr(part, "executable_code") and part.executable_code:
                # Access the actual code string via .code
                print(
                    f"  Debug: Agent generated code:\n```python\n{part.executable_code.code}\n```"
                )
                has_specific_part = True
            elif hasattr(part, "code_execution_result") and part.code_execution_result:
                # Access outcome and output correctly
                print(
                    f"  Debug: Code Execution Result: {part.code_execution_result.outcome} - Output:\n{part.code_execution_result.output}"
                )
                has_specific_part = True
            elif hasattr(part, "tool_response") and part.tool_response:
                # Print tool response information
                print(f"  Tool Response: {part.tool_response.output}")
                has_specific_part = True
            # Also print any text parts found in any event for debugging
            elif hasattr(part, "text") and part.text and not part.text.isspace():
                print(f"  Text: '{part.text.strip()}'")

    # Check for final response after specific parts
    final_response = None
    if event.is_final_response():
        if (
            event.content
            and event.content.parts
            and hasattr(event.content.parts[0], "text")
            and event.content.parts[0].text
        ):
            final_response = event.content.parts[0].text.strip()
            
        else:
            final_response = "ขออภัย ไม่สามารถประมวลผลข้อความได้ กรุณาลองใหม่อีกครั้ง"

    return final_response

async def generate_text(user_input: str, user_id: str = None) -> str:
    """
    รับข้อความจากผู้ใช้และส่งต่อไปยัง ADK Agent
    
    Args:
        user_input (str): ข้อความจากผู้ใช้
        user_id (str): ID ของผู้ใช้ (optional)
        
    Returns:
        str: คำตอบจาก Agent
    """
    try:
        # ใช้ user_id ที่ส่งมาหรือใช้ default
        current_user_id = user_id or USER_ID
        
        # ดึงหรือสร้าง session สำหรับ user นี้
        session_id = await get_or_create_session(current_user_id)
        
        final_response_text = None
        
        # สร้าง Content object ตามตัวอย่างจาก Google
        content = types.Content(role="user", parts=[types.Part(text=user_input)])
        
        # ใช้ try-except เพื่อจัดการ MCP Tool errors และ async context issues
        try:
            # ใช้ asyncio.wait_for เพื่อจัดการ timeout และ async context
            import asyncio
            
            async def run_agent():
                try:
                    async for event in runner.run_async(
                        user_id=current_user_id, 
                        session_id=session_id, 
                        new_message=content
                    ):
                        # Process each event and get the final response if available
                        response = await process_agent_response(event)
                        if response:
                            return response
                    return None
                except Exception as e:
                    print(f"Error in run_agent: {e}")
                    return None
            
            # รัน agent พร้อม timeout 30 วินาที
            final_response_text = await asyncio.wait_for(run_agent(), timeout=30.0)
                    
        except asyncio.TimeoutError:
            print("MCP Tool timeout after 30 seconds")
            final_response_text = "ขออภัย การประมวลผลใช้เวลานานเกินไป กรุณาลองใหม่อีกครั้ง"
        except Exception as mcp_error:
            print(f"MCP Tool error: {mcp_error}")
            import traceback
            print(f"MCP Traceback: {traceback.format_exc()}")
            # ถ้า MCP Tool มีปัญหา ให้ใช้ fallback function
            final_response_text = "ขออภัย บริการ MCP Tool ไม่พร้อมใช้งานในขณะนี้ แต่ฉันสามารถสร้าง Flex Message ให้คุณได้"

        return final_response_text or "ขออภัย ไม่สามารถประมวลผลข้อความได้ กรุณาลองใหม่อีกครั้ง"
    except Exception as e:
        print(f"Error in generate_text: {str(e)}")
        import traceback
        print(f"Traceback: {traceback.format_exc()}")
        return "ขออภัย เกิดข้อผิดพลาดในการประมวลผล กรุณาลองใหม่อีกครั้ง"

async def image_understanding(image_content, user_id: str = None) -> str:
    """
    รับรูปภาพและส่งต่อไปยัง ADK Agent
    
    Args:
        image_content: เนื้อหาของรูปภาพ
        user_id (str): ID ของผู้ใช้ (optional)
        
    Returns:
        str: คำตอบจาก Agent
    """
    try:
        # ใช้ user_id ที่ส่งมาหรือใช้ default
        current_user_id = user_id or USER_ID
        
        # ดึงหรือสร้าง session สำหรับ user นี้
        session_id = await get_or_create_session(current_user_id)
        
        final_response_text = None
        
        # สร้าง Content object ตามตัวอย่างจาก Google
        content = types.Content(role="user", parts=[types.Part(text="กรุณาวิเคราะห์รูปภาพนี้และสร้าง Campaign ตามรูปภาพ")])
        
        # ใช้ try-except เพื่อจัดการ MCP Tool errors และ async context issues
        try:
            import asyncio
            
            async def run_agent():
                async for event in runner.run_async(
                    user_id=current_user_id, 
                    session_id=session_id, 
                    new_message=content
                ):
                    response = await process_agent_response(event)
                    if response:
                        return response
                return None
            
            # รัน agent พร้อม timeout 30 วินาที
            final_response_text = await asyncio.wait_for(run_agent(), timeout=30.0)
                    
        except asyncio.TimeoutError:
            print("MCP Tool timeout after 30 seconds")
            final_response_text = "ขออภัย การวิเคราะห์รูปภาพใช้เวลานานเกินไป กรุณาลองใหม่อีกครั้ง"
        except Exception as mcp_error:
            print(f"MCP Tool error: {mcp_error}")
            final_response_text = "ขออภัย บริการ MCP Tool ไม่พร้อมใช้งานในขณะนี้ กรุณาลองใหม่อีกครั้ง"
                
        return final_response_text or "ขออภัย ไม่สามารถวิเคราะห์รูปภาพได้ กรุณาลองใหม่อีกครั้ง"
    except Exception as e:
        print(f"Error in image_understanding: {str(e)}")
        return "ขออภัย ไม่สามารถวิเคราะห์รูปภาพได้ กรุณาลองใหม่อีกครั้ง"

async def document_understanding(doc_content, user_id: str = None) -> str:
    """
    รับเอกสารและส่งต่อไปยัง ADK Agent
    
    Args:
        doc_content: เนื้อหาของเอกสาร
        user_id (str): ID ของผู้ใช้ (optional)
        
    Returns:
        str: คำตอบจาก Agent
    """
    try:
        # ใช้ user_id ที่ส่งมาหรือใช้ default
        current_user_id = user_id or USER_ID
        
        # ดึงหรือสร้าง session สำหรับ user นี้
        session_id = await get_or_create_session(current_user_id)
        
        final_response_text = None
        
        # สร้าง Content object ตามตัวอย่างจาก Google
        content = types.Content(role="user", parts=[types.Part(text="กรุณาวิเคราะห์เอกสารนี้และสร้าง Campaign ตามเนื้อหา")])
        
        # ใช้ try-except เพื่อจัดการ MCP Tool errors และ async context issues
        try:
            import asyncio
            
            async def run_agent():
                async for event in runner.run_async(
                    user_id=current_user_id, 
                    session_id=session_id, 
                    new_message=content
                ):
                    response = await process_agent_response(event)
                    if response:
                        return response
                return None
            
            # รัน agent พร้อม timeout 30 วินาที
            final_response_text = await asyncio.wait_for(run_agent(), timeout=30.0)
                    
        except asyncio.TimeoutError:
            print("MCP Tool timeout after 30 seconds")
            final_response_text = "ขออภัย การวิเคราะห์เอกสารใช้เวลานานเกินไป กรุณาลองใหม่อีกครั้ง"
        except Exception as mcp_error:
            print(f"MCP Tool error: {mcp_error}")
            final_response_text = "ขออภัย บริการ MCP Tool ไม่พร้อมใช้งานในขณะนี้ กรุณาลองใหม่อีกครั้ง"
                
        return final_response_text or "ขออภัย ไม่สามารถวิเคราะห์เอกสารได้ กรุณาลองใหม่อีกครั้ง"
    except Exception as e:
        print(f"Error in document_understanding: {str(e)}")
        return "ขออภัย ไม่สามารถวิเคราะห์เอกสารได้ กรุณาลองใหม่อีกครั้ง"

# ฟังก์ชัน wrapper สำหรับใช้กับ Google Cloud Functions
def generate_text_sync(user_input: str) -> str:
    """Synchronous wrapper สำหรับ generate_text พร้อม retry mechanism"""
    max_retries = 3
    retry_count = 0
    
    while retry_count < max_retries:
        try:
            # ใช้ asyncio.run ใน try-except เพื่อจัดการ MCP Tool errors
            result = asyncio.run(generate_text(user_input))
            return result
        except Exception as e:
            retry_count += 1
            print(f"Error in generate_text_sync (attempt {retry_count}/{max_retries}): {e}")
            import traceback
            print(f"Traceback: {traceback.format_exc()}")
            
            if retry_count < max_retries:
                print(f"Retrying in 2 seconds...")
                import time
                time.sleep(2)
                continue
            else:
                # ถ้า MCP Tool มีปัญหา ให้ส่งข้อความแจ้งเตือน
                if "MCP" in str(e) or "mcp" in str(e):
                    return "ขออภัย บริการ MCP Tool ไม่พร้อมใช้งานในขณะนี้ กรุณาลองใหม่อีกครั้ง"
                else:
                    return "ขออภัย เกิดข้อผิดพลาดในการประมวลผล กรุณาลองใหม่อีกครั้ง"

def image_understanding_sync(image_content) -> str:
    """Synchronous wrapper สำหรับ image_understanding"""
    try:
        return asyncio.run(image_understanding(image_content))
    except Exception as e:
        print(f"Error in image_understanding_sync: {e}")
        import traceback
        print(f"Traceback: {traceback.format_exc()}")
        return "ขออภัย ไม่สามารถวิเคราะห์รูปภาพได้ กรุณาลองใหม่อีกครั้ง"

def document_understanding_sync(doc_content) -> str:
    """Synchronous wrapper สำหรับ document_understanding"""
    try:
        return asyncio.run(document_understanding(doc_content))
    except Exception as e:
        print(f"Error in document_understanding_sync: {e}")
        import traceback
        print(f"Traceback: {traceback.format_exc()}")
        return "ขออภัย ไม่สามารถวิเคราะห์เอกสารได้ กรุณาลองใหม่อีกครั้ง"
