"""
ADK Runner Service สำหรับรับข้อความจาก LINE และส่งต่อไปยัง ADK Agent
"""
import os
import asyncio
from google.adk.runners import Runner, InMemorySessionService
from line_oa_campaign_manager.agent import root_agent

# Configuration
APP_NAME = "line_oa_campaign_manager"
USER_ID = "line_user"

# Global session service and runner
session_service = InMemorySessionService()
runner = Runner(
    agent=root_agent,
    app_name=APP_NAME,
    session_service=session_service,
)

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
        
        # สร้าง session ใหม่สำหรับผู้ใช้
        new_session = await session_service.create_session(
            app_name=APP_NAME,
            user_id=current_user_id,
            state={},
        )
        session_id = new_session.id
        print(f"Created new session: {session_id}")
        
        # รัน Agent ด้วย session
        response = await runner.run_async(
            user_input, 
            session_id=session_id
        )
        return response
    except Exception as e:
        print(f"Error in generate_text: {str(e)}")
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
        
        # สร้าง session ใหม่สำหรับผู้ใช้
        new_session = await session_service.create_session(
            app_name=APP_NAME,
            user_id=current_user_id,
            state={},
        )
        session_id = new_session.id
        print(f"Created new session for image: {session_id}")
        
        # รัน Agent ด้วย session
        response = await runner.run_async(
            "กรุณาวิเคราะห์รูปภาพนี้และสร้าง Campaign ตามรูปภาพ",
            session_id=session_id
        )
        return response
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
        
        # สร้าง session ใหม่สำหรับผู้ใช้
        new_session = await session_service.create_session(
            app_name=APP_NAME,
            user_id=current_user_id,
            state={},
        )
        session_id = new_session.id
        print(f"Created new session for document: {session_id}")
        
        # รัน Agent ด้วย session
        response = await runner.run_async(
            "กรุณาวิเคราะห์เอกสารนี้และสร้าง Campaign ตามเนื้อหา",
            session_id=session_id
        )
        return response
    except Exception as e:
        print(f"Error in document_understanding: {str(e)}")
        return "ขออภัย ไม่สามารถวิเคราะห์เอกสารได้ กรุณาลองใหม่อีกครั้ง"

# ฟังก์ชัน wrapper สำหรับใช้กับ Google Cloud Functions
def generate_text_sync(user_input: str) -> str:
    """Synchronous wrapper สำหรับ generate_text"""
    return asyncio.run(generate_text(user_input))

def image_understanding_sync(image_content) -> str:
    """Synchronous wrapper สำหรับ image_understanding"""
    return asyncio.run(image_understanding(image_content))

def document_understanding_sync(doc_content) -> str:
    """Synchronous wrapper สำหรับ document_understanding"""
    return asyncio.run(document_understanding(doc_content))
