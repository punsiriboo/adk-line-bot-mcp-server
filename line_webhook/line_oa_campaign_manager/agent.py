import os
import mimetypes
import asyncio
import shutil
from pathlib import Path
from google import genai
from google.genai import types
from google.adk.agents import Agent
from google.adk.tools.mcp_tool.mcp_toolset import MCPToolset
from google.adk.tools.mcp_tool.mcp_session_manager import StdioConnectionParams
from mcp import StdioServerParameters
import uuid
from google.cloud import storage


def gemini_generate_image(prompt: str, out_prefix: str):
    """Generate image using Gemini AI and upload to Google Cloud Storage"""
    try:
        client = genai.Client(api_key=os.getenv("GEMINI_API_KEY"))
        storage_client = storage.Client()

        res = client.models.generate_content(
            model="gemini-2.5-flash-image-preview",
            contents=[
                types.Content(role="user",
                parts=[
                    types.Part.from_text(text=prompt),
                ])
            ],
            config=types.GenerateContentConfig(response_modalities=["IMAGE"])
        )

        for part in res.candidates[0].content.parts:
            if getattr(part, "inline_data", None) and part.inline_data.data:
                ext = mimetypes.guess_extension(part.inline_data.mime_type) or ".bin"
                image_uuid = str(uuid.uuid4())
                path = Path(f"{out_prefix}{image_uuid}{ext}")
                path.write_bytes(part.inline_data.data)
                print(f"Saved image: {path}")
                gcs_path = f"gs://line-oa-campaign-manager-images/{path.name}"
                bucket = storage_client.bucket("line-oa-campaign-manager-images")
                blob = bucket.blob(path.name)
                blob.upload_from_filename(path)
                print(f"Uploaded image to: {gcs_path}")
                return gcs_path
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
    # ใช้ credentials จริงแต่ไม่ตรวจสอบ authentication
    channel_token = os.getenv("LINE_CHANNEL_ACCESS_TOKEN", "")
    destination_user_id = os.getenv("LINE_DESTINATION_USER_ID", "")
    
    print("⚠ Creating MCP Toolset with real credentials but bypassing authentication check")
    
    # สร้าง MCP Toolset พร้อม credentials จริง
    line_bot_server_mcp_toolset = MCPToolset(
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
                    "NODE_ENV": "production",
                    "MCP_TIMEOUT": "30000",  # 30 seconds timeout
                    "MCP_RETRY_COUNT": "3",  # Retry 3 times
                },
            ),
        ),
    )
    print("✓ MCP Toolset created successfully with real credentials")
except Exception as e:
    print(f"✗ Failed to create MCP Toolset: {e}")
    import traceback
    print(f"Traceback: {traceback.format_exc()}")
    # สร้าง fallback toolset หรือใช้ tools อื่น
    line_bot_server_mcp_toolset = None

try:
    agent_instruction_prompt = Path(__file__).parent / "agent_instruction_prompt.txt"
    agent_instruction_prompt = agent_instruction_prompt.read_text()
    print("✓ Agent instruction prompt loaded successfully")
except Exception as e:
    print(f"✗ Failed to load agent instruction prompt: {e}")
    agent_instruction_prompt = "คุณเป็นผู้ช่วยด้านการตลาดและการออกแบบ Flex Message สำหรับ LINE OA"

# สร้าง fallback function สำหรับส่ง Flex Message เมื่อ MCP Tool ไม่ทำงาน
def send_flex_message_fallback(message: str):
    """Fallback function สำหรับส่งข้อความเมื่อ MCP Tool ไม่ทำงาน"""
    return f"✅ ฉันได้สร้าง Flex Message สำหรับคุณแล้ว: {message}\n\n💡 หมายเหตุ: บริการ MCP Tool ไม่พร้อมใช้งานในขณะนี้ แต่ฉันสามารถสร้าง Flex Message JSON ให้คุณได้"

try:
    # สร้าง tools list โดยตรวจสอบว่า MCP toolset พร้อมใช้งานหรือไม่
    tools = [gemini_generate_image, send_flex_message_fallback]
    if line_bot_server_mcp_toolset is not None:
        tools.append(line_bot_server_mcp_toolset)
        print("✓ MCP Toolset added to agent tools")
    else:
        print("⚠ MCP Toolset not available, using fallback functions")
    
    root_agent = Agent(
        model='gemini-2.0-flash-001',
        name='line_oa_campaign_manager',
        description="LINE Bot Campaign Manager",
        instruction=agent_instruction_prompt,
        tools=tools,
    )
    print("✓ Root agent created successfully")
except Exception as e:
    print(f"✗ Failed to create root agent: {e}")
    import traceback
    print(f"Traceback: {traceback.format_exc()}")
    # สร้าง fallback agent
    root_agent = Agent(
        model='gemini-2.0-flash-001',
        name='line_oa_campaign_manager',
        description="LINE Bot Campaign Manager",
        instruction="คุณเป็นผู้ช่วยด้านการตลาดและการออกแบบ Flex Message สำหรับ LINE OA",
        tools=[gemini_generate_image, send_flex_message_fallback],
    )
