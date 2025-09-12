import os
import mimetypes
import uuid
import shutil
from pathlib import Path
from google import genai
from google.genai import types
from google.adk.agents import Agent
from google.adk.tools.mcp_tool.mcp_toolset import MCPToolset, SseConnectionParams
from google.adk.tools.mcp_tool.mcp_session_manager import StdioConnectionParams
from mcp import StdioServerParameters
from google.cloud import storage
from dotenv import load_dotenv

load_dotenv()


def gemini_generate_image(prompt: str):
    """
    สร้างรูปภาพโดยใช้ Gemini AI และอัปโหลดไปยัง Google Cloud Storage
    
    Args:
        prompt (str): คำอธิบายหรือข้อความที่ใช้ในการสร้างรูปภาพ
        
    Returns:
        str: URL ของรูปภาพใน Google Cloud Storage (รูปแบบ https://storage.googleapis.com/line-oa-campaign-manager-images/filename)
             หรือข้อความแสดงข้อผิดพลาดหากการสร้างรูปภาพล้มเหลว
             
    Raises:
        Exception: หากเกิดข้อผิดพลาดในการเชื่อมต่อ API หรือการอัปโหลดไฟล์
    """
    try:
        client = genai.Client(api_key=os.getenv("GEMINI_API_KEY"))
        sa = Path(__file__).parent / "ai-agent-sa.json"
        storage_client = storage.Client.from_service_account_json(sa)

        res = client.models.generate_content(
            model="gemini-2.5-flash-image-preview",
            contents=[types.Content(role="user", parts=[types.Part.from_text(text=prompt)])],
            config=types.GenerateContentConfig(response_modalities=["IMAGE"])
        )

        for part in res.candidates[0].content.parts:
            if getattr(part, "inline_data", None) and part.inline_data.data:
                ext = mimetypes.guess_extension(part.inline_data.mime_type) or ".bin"
                image_uuid = str(uuid.uuid4())
                path = Path(f"{image_uuid}{ext}")
                path.write_bytes(part.inline_data.data)
                print(f"Saved image: {path}")
                gcs_path = f"gs://line-oa-campaign-manager-images/{path.name}"
                public_url = f"https://storage.googleapis.com/line-oa-campaign-manager-images/{path.name}"
                bucket = storage_client.bucket("line-oa-campaign-manager-images")
                blob = bucket.blob(path.name)
                blob.upload_from_filename(path)
                print(f"Uploaded image to: {gcs_path}")
                return public_url
        return "Image generation failed"
    except Exception as e:
        print(f"Error in gemini_generate_image: {e}")
        return f"Error generating image: {str(e)}"

# ใช้ absolute path ของ npx สำหรับ Docker container
def get_npx_path():
    """หาตำแหน่ง npx command สำหรับ Docker container"""
    # ใช้ environment variable ก่อน
    npx_path = os.getenv('NPX_PATH')
    if npx_path and os.path.exists(npx_path):
        print(f"Using NPX_PATH: {npx_path}")
        return npx_path
    
    # ลองหา npx ใน PATH
    npx_path = shutil.which('npx')
    if npx_path:
        print(f"Found npx in PATH: {npx_path}")
        return npx_path
    
    # Docker container paths ที่เป็นไปได้
    docker_paths = [
        '/usr/bin/npx',                 # Standard Linux path
        '/usr/local/bin/npx',           # Alternative path
        '/opt/nodejs/bin/npx',          # Node.js installed via package manager
        '/app/node_modules/.bin/npx',   # Local node_modules
    ]
    
    for path in docker_paths:
        if os.path.exists(path):
            print(f"Found npx at: {path}")
            return path
    
    # ถ้าหาไม่เจอเลย ให้ใช้ 'npx' และให้ระบบจัดการเอง
    print("Warning: npx not found in common paths, using 'npx'")
    return 'npx'

npx_path = get_npx_path()
print(f"Using npx command: {npx_path}")

try:
    channel_token = os.getenv("DEST_OA_LINE_CHANNEL_ACCESS_TOKEN")
    destination_user_id = os.getenv("DEST_OA_LINE_DESTINATION_USER_ID")

    if not channel_token or not destination_user_id:
        print("Warning: Missing LINE credentials for MCP server")
        line_bot_mcp_toolset = None
    else:
        # ปรับปรุงการตั้งค่า MCP เพื่อลดปัญหา event loop และ subprocess cleanup
        line_bot_mcp_toolset = MCPToolset(
            connection_params=StdioConnectionParams(
                server_params=StdioServerParameters(
                    command=npx_path,
                    args=[
                        "-y",
                        "@line/line-bot-mcp-server",
                    ],
                    env={
                        "CHANNEL_ACCESS_TOKEN": channel_token,
                        "DESTINATION_USER_ID": destination_user_id,
                        "MCP_RETRY_COUNT": "2",  # ลด retry เป็น 2 ครั้ง
                        "MCP_TIMEOUT": "15",     # ลด timeout เป็น 15 วินาที
                        "MCP_INITIALIZATION_TIMEOUT": "20",  # ลด initialization timeout
                        "NODE_ENV": "production",  # เพิ่ม NODE_ENV
                        "NODE_NO_WARNINGS": "1",   # ปิด warnings
                    },
                ),
            ),
        )
        print("✓ MCP Toolset created successfully")
except Exception as e:
    print(f"Failed to create MCP Toolset: {e}")
    import traceback
    print(f"Traceback: {traceback.format_exc()}")
    line_bot_mcp_toolset = None

agent_instruction_prompt = Path(__file__).parent / "agent_instruction_prompt.txt"
agent_instruction_prompt = agent_instruction_prompt.read_text()

agent_tools = [gemini_generate_image]
if line_bot_mcp_toolset is not None:
    agent_tools.append(line_bot_mcp_toolset)
    print("MCP Toolset added to agent tools")
else:
    print("MCP Toolset not available")

line_oa_agent = Agent(
    model='gemini-2.0-flash-001',
    name='line_oa_campaign_manager',
    description="LINE Bot Campaign Manager",
    instruction=agent_instruction_prompt,
    tools=agent_tools,
)