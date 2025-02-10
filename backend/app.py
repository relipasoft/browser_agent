import os
os.environ["PYDANTIC_V1_COMPAT_MODE"] = "true"

import sys
# Nếu chạy trên Windows, thiết lập event loop policy hỗ trợ subprocess
if sys.platform == "win32":
    import asyncio
    asyncio.set_event_loop_policy(asyncio.WindowsProactorEventLoopPolicy())

from langchain_ollama import ChatOllama
from browser_use import Agent
from dotenv import load_dotenv
import platform
import asyncio
from fastapi import FastAPI, WebSocket, WebSocketDisconnect
from pydantic import BaseModel
from browser_use.browser.browser import Browser, BrowserConfig
import logging
import traceback
from datetime import datetime
from enum import Enum
from fastapi.middleware.cors import CORSMiddleware
import json

# ----------------------------
# 1. Configure Logging
# ----------------------------
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# ----------------------------
# 2. Load Environment Variables
# ----------------------------
load_dotenv()

# Verify the OpenAI API key is loaded
api_key = os.getenv("OPENAI_API_KEY")
if not api_key:
    raise ValueError(
        "OPENAI_API_KEY not found in .env file. Make sure your .env file is set up correctly."
    )

# ----------------------------
# 3. Initialize FastAPI App
# ----------------------------
app = FastAPI(title="AI Agent API with BrowserUse (WebSocket)", version="1.0")

# Configure CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # For development: allow all origins. In production, specify exact origins.
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# ----------------------------
# 4. Utility Function: Get Chrome Path
# ----------------------------
def get_chrome_path() -> str:
    """
    Returns the most common Chrome executable path based on the operating system.
    Raises:
        FileNotFoundError: If Chrome is not found in the expected path.
    """
    system = platform.system()
    
    if system == "Windows":
        # Common installation path for Windows
        chrome_path = os.path.join(
            os.environ.get("PROGRAMFILES", "C:\\Program Files"),
            "Google\\Chrome\\Application\\chrome.exe"
        )
    elif system == "Darwin":
        # Common installation path for macOS
        chrome_path = "/Applications/Google Chrome.app/Contents/MacOS/Google Chrome"
    elif system == "Linux":
        # Common installation path for Linux
        chrome_path = "/usr/bin/google-chrome"
    else:
        raise FileNotFoundError(f"Unsupported operating system: {system}")
    
    if not os.path.exists(chrome_path):
        raise FileNotFoundError(f"Google Chrome executable not found at: {chrome_path}")
    
    return chrome_path

# ----------------------------
# 5. WebSocket Endpoint to Run Agent Task
# ----------------------------
@app.websocket("/ws/agent")
async def agent_websocket(websocket: WebSocket):
    await websocket.accept()
    try:
        # Nhận thông điệp từ client (dạng JSON có chứa trường "task")
        data = await websocket.receive_text()
        try:
            payload = json.loads(data)
        except json.JSONDecodeError:
            await websocket.send_text(json.dumps({"status": "error", "error": "Invalid JSON format"}))
            await websocket.close()
            return

        task = payload.get("task")
        if not task:
            await websocket.send_text(json.dumps({"status": "error", "error": "Field 'task' is required"}))
            await websocket.close()
            return

        logger.info(f"Received task via WebSocket: {task}")
        await websocket.send_text(json.dumps({"status": "starting", "message": "Task is starting."}))

        browser = None
        try:
            # Khởi tạo browser instance cho task
            logger.info("Initializing browser instance.")
            await websocket.send_text(json.dumps({"status": "initializing_browser", "message": "Initializing browser instance."}))
            browser = Browser(
                config=BrowserConfig(
                    chrome_instance_path=get_chrome_path(),  # Sử dụng đường dẫn Chrome đã được xác định
                    disable_security=True,
                    headless=False,  # Đổi thành True nếu muốn chạy chế độ headless
                )
            )
            await websocket.send_text(json.dumps({"status": "browser_initialized", "message": "Browser instance initialized."}))

            # Khởi tạo agent với browser vừa khởi tạo
            agent = Agent(
                task=task,
                llm=ChatOllama(
                model="qwen2.5",
                num_ctx=32000
                ),
                browser=browser)
            await websocket.send_text(json.dumps({"status": "agent_running", "message": "Agent is running the task."}))

            # Chạy task và đợi kết quả trả về từ agent
            result = await agent.run()
            logger.info("Agent task completed successfully.")
            await websocket.send_text(json.dumps({"status": "completed", "result": result}))

        except Exception as e:
            logger.error(f"Error processing task via WebSocket: {e}")
            logger.error(traceback.format_exc())
            await websocket.send_text(json.dumps({"status": "failed", "error": str(e)}))
        finally:
            # Đảm bảo đóng browser cho dù có lỗi hay không
            if browser:
                try:
                    logger.info("Closing browser instance.")
                    await browser.close()
                    await websocket.send_text(json.dumps({"status": "browser_closed", "message": "Browser instance closed."}))
                except Exception as close_e:
                    logger.error(f"Error closing browser: {close_e}")
                    await websocket.send_text(json.dumps({"status": "failed", "error": f"Error closing browser: {str(close_e)}"}))
    except WebSocketDisconnect:
        logger.info("WebSocket disconnected by client.")
    except Exception as e:
        logger.error(f"Unexpected error: {e}")
        logger.error(traceback.format_exc())
