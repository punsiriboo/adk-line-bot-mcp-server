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
import uuid
from google.cloud import storage


def gemini_generate_image(prompt: str, out_prefix: str = "output"):
    client = genai.Client(api_key=os.getenv("GEMINI_API_KEY"))
    storage_client = storage.Client()

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
            uuid = str(uuid.uuid4())
            path = Path(f"{out_prefix}{uuid}{ext}")
            path.write_bytes(part.inline_data.data)
            print(f"Saved image: {path}")
            gcs_path = f"gs://line-oa-campaign-manager-images/{path.name}"
            bucket = storage_client.bucket("line-oa-campaign-manager-images")
            blob = bucket.blob(path.name)
            blob.upload_from_filename(path)
            print(f"Uploaded image to: {gcs_path}")

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

agent_instruction_prompt = Path(__file__).parent / "agent_instruction_prompt.txt"
agent_instruction_prompt = agent_instruction_prompt.read_text()

root_agent = Agent(
    model='gemini-2.0-flash-001',
    name='line_oa_campaign_manager',
    description="LINE Bot Campaign Manager",
    instruction=agent_instruction_prompt,
    tools=[gemini_generate_image, line_bot_server_mcp_toolset],
)
