"""
Gemini Service สำหรับรับข้อความจาก LINE และส่งต่อไปยัง ADK Agent
"""
import os
import asyncio
from line_oa_campaign_manager.agent import root_agent

async def generate_text(user_input: str) -> str:
    """
    รับข้อความจากผู้ใช้และส่งต่อไปยัง ADK Agent
    
    Args:
        user_input (str): ข้อความจากผู้ใช้
        
    Returns:
        str: คำตอบจาก Agent
    """
    try:
        # ส่งข้อความไปยัง ADK Agent
        response = await root_agent.run_async(user_input)
        return response
    except Exception as e:
        print(f"Error in generate_text: {str(e)}")
        return "ขออภัย เกิดข้อผิดพลาดในการประมวลผล กรุณาลองใหม่อีกครั้ง"

async def image_understanding(image_content) -> str:
    """
    รับรูปภาพและส่งต่อไปยัง ADK Agent
    
    Args:
        image_content: เนื้อหาของรูปภาพ
        
    Returns:
        str: คำตอบจาก Agent
    """
    try:
        # ส่งรูปภาพไปยัง ADK Agent
        response = await root_agent.run_async("กรุณาวิเคราะห์รูปภาพนี้และสร้าง Campaign ตามรูปภาพ")
        return response
    except Exception as e:
        print(f"Error in image_understanding: {str(e)}")
        return "ขออภัย ไม่สามารถวิเคราะห์รูปภาพได้ กรุณาลองใหม่อีกครั้ง"

async def document_understanding(doc_content) -> str:
    """
    รับเอกสารและส่งต่อไปยัง ADK Agent
    
    Args:
        doc_content: เนื้อหาของเอกสาร
        
    Returns:
        str: คำตอบจาก Agent
    """
    try:
        # ส่งเอกสารไปยัง ADK Agent
        response = await root_agent.run_async("กรุณาวิเคราะห์เอกสารนี้และสร้าง Campaign ตามเนื้อหา")
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
