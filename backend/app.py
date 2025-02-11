import os
os.environ["PYDANTIC_V1_COMPAT_MODE"] = "true"

import sys
if sys.platform == "win32":
    import asyncio
    asyncio.set_event_loop_policy(asyncio.WindowsProactorEventLoopPolicy())

import asyncio
import logging
import traceback
import platform
import json  # Dùng để đóng gói message thành JSON
from datetime import datetime
from enum import Enum
from typing import List, Optional
from langchain_openai import ChatOpenAI
from langchain_ollama import ChatOllama
from fastapi import FastAPI, BackgroundTasks, WebSocket
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from dotenv import load_dotenv

# ----------------------------
# 1. Configure Global Logging
# ----------------------------

# Bộ lọc chỉ cho phép log từ module browser_use.agent và các module con của nó.
class AgentOnlyFilter(logging.Filter):
    def filter(self, record):
        return record.name.startswith("browser_use.agent")

# Custom Logging Handler gửi log tới một WebSocket cụ thể,
# đóng gói message theo định dạng JSON:
# {
#    "type": <"process" hoặc "result">,
#    "message": <nội dung log>
# }
class WebSocketTaskLogHandler(logging.Handler):
    def __init__(self, websocket: WebSocket):
        super().__init__()
        self.websocket = websocket

    def emit(self, record):
        try:
            # Lấy nội dung message theo formatter (ở đây chúng ta sẽ dùng formatter "%(message)s")
            message_text = self.format(record)
            # Nếu logger name là "browser_use.agent.final" thì đây là log final result.
            msg_type = "result" if record.name == "browser_use.agent.final" else "process"
            payload = {"type": msg_type, "message": message_text}
            payload_str = json.dumps(payload)
            # Gửi message không đồng bộ qua websocket.
            asyncio.create_task(self.websocket.send_text(payload_str))
        except Exception:
            self.handleError(record)

# Cấu hình logging toàn cục cho console (vẫn giữ timestamp, level,...)
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(levelname)s - %(message)s",
)
root_logger = logging.getLogger()

# ----------------------------
# 2. Load Environment Variables
# ----------------------------
load_dotenv()
api_key = os.getenv("OPENAI_API_KEY")
if not api_key:
    raise ValueError("OPENAI_API_KEY not found in .env file. Please configure your .env file correctly.")

# ----------------------------
# 3. Initialize FastAPI App
# ----------------------------
app = FastAPI(title="AI Agent API with BrowserUse", version="1.0")
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # Trong production, hãy giới hạn origin cho phép.
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# ----------------------------
# 4. Define Pydantic Models
# ----------------------------
class TaskRequest(BaseModel):
    task: str

class TaskResponse(BaseModel):
    result: str

class TaskStatus(str, Enum):
    RUNNING = "running"
    COMPLETED = "completed"
    FAILED = "failed"

class TaskRecord(BaseModel):
    id: int
    task: str
    status: TaskStatus
    start_time: datetime
    end_time: Optional[datetime] = None
    duration: Optional[float] = None  # Duration in seconds
    result: Optional[str] = None
    error: Optional[str] = None

# ----------------------------
# 5. Global Task Registry
# ----------------------------
task_records: List[TaskRecord] = []
task_id_counter: int = 0
task_lock = asyncio.Lock()

# ----------------------------
# 6. Helper Functions & Background Task Function
# ----------------------------
from browser_use.browser.browser import Browser, BrowserConfig
from browser_use import Agent
from langchain_openai import ChatOpenAI

def get_chrome_path() -> str:
    """
    Trả về đường dẫn của Chrome dựa trên hệ điều hành.
    """
    system = platform.system()
    if system == "Windows":
        chrome_path = os.path.join(
            os.environ.get("PROGRAMFILES", "C:\\Program Files"),
            "Google\\Chrome\\Application\\chrome.exe"
        )
    elif system == "Darwin":
        chrome_path = "/Applications/Google Chrome.app/Contents/MacOS/Google Chrome"
    elif system == "Linux":
        chrome_path = "/usr/bin/google-chrome"
    else:
        raise FileNotFoundError(f"Unsupported operating system: {system}")
    
    if not os.path.exists(chrome_path):
        raise FileNotFoundError(f"Google Chrome executable not found at: {chrome_path}")
    return chrome_path

async def execute_task(task_id: int, task: str):
    """
    Thực hiện Agent:
      - Cập nhật task record.
      - Khởi tạo Browser và Agent.
      - Chạy Agent và ghi log kết quả.
    """
    global task_records
    browser = None
    try:
        # Ghi log bắt đầu task bằng logger có namespace "browser_use.agent"
        # logging.getLogger("browser_use.agent").info(f"🚀 Starting task: {{\"task\":\"{task}\"}}")
        async with task_lock:
            task_record = TaskRecord(
                id=task_id,
                task=task,
                status=TaskStatus.RUNNING,
                start_time=datetime.utcnow()
            )
            task_records.append(task_record)
        
        # logging.getLogger("browser_use.agent").info(f"Task ID {task_id}: Initializing new browser instance.")
        browser = Browser(
            config=BrowserConfig(
                chrome_instance_path=get_chrome_path(),
                disable_security=True,
                headless=False,  # Đổi thành True nếu muốn chạy ẩn
            )
        )
        # logging.getLogger("browser_use.agent").info(f"Task ID {task_id}: Browser initialized successfully.")
        
        # Khởi tạo Agent với Browser và ChatOpenAI LLM.
        agent = Agent(
            task=task,
            llm=ChatOpenAI(model="gpt-4o", api_key=api_key),
            # llm=ChatOllama(model="qwen2.5",num_ctx=32000),
            browser=browser
        )
        logging.getLogger("browser_use.agent").info(f"Agent initialized. Running task.")
        result = await agent.run()
        # Log thông báo Agent.run() hoàn thành trước
        logging.getLogger("browser_use.agent").info(f"Task ID {task_id}: Agent run completed successfully.")
        # Sau đó, lấy kết quả cuối cùng và log với logger có namespace "browser_use.agent.final"
        final_result = result.final_result()
        logging.getLogger("browser_use.agent.final").info(f"{final_result}")
        
        async with task_lock:
            for record in task_records:
                if record.id == task_id:
                    record.status = TaskStatus.COMPLETED
                    record.end_time = datetime.utcnow()
                    record.duration = (record.end_time - record.start_time).total_seconds()
                    record.result = str(final_result)
                    break

    except Exception as e:
        logging.getLogger("browser_use.agent").error(f"Error in background task ID {task_id}: {e}")
        logging.getLogger("browser_use.agent").error(traceback.format_exc())
        async with task_lock:
            for record in task_records:
                if record.id == task_id:
                    record.status = TaskStatus.FAILED
                    record.end_time = datetime.utcnow()
                    record.duration = (record.end_time - record.start_time).total_seconds()
                    record.error = str(e)
                    break
    finally:
        if browser:
            try:
                logging.getLogger("browser_use.agent").info(f"Task ID {task_id}: Closing browser instance.")
                await browser.close()
                logging.getLogger("browser_use.agent").info(f"Task ID {task_id}: Browser closed successfully.")
            except Exception as close_e:
                logging.getLogger("browser_use.agent").error(f"Task ID {task_id}: Error closing browser: {close_e}")
                logging.getLogger("browser_use.agent").error(traceback.format_exc())

# ----------------------------
# 7. WebSocket Endpoint /ws/run (Kết hợp chạy task và nhận log)
# ----------------------------
@app.websocket("/ws/run")
async def websocket_run(websocket: WebSocket):
    """
    Client kết nối qua WebSocket, gửi nhiệm vụ cần chạy (chuỗi văn bản).
    Server sẽ gắn handler tạm thời để đẩy log (chỉ log từ browser_use.agent)
    với định dạng JSON theo pattern:
      {
          "type": <"process" hoặc "result">,
          "message": <nội dung log>
      }
    Trong đó, log từ quá trình thực thi có type "process" và final result có type "result".
    Sau khi task hoàn thành, server gửi thông báo "Task finished." rồi đóng kết nối.
    """
    await websocket.accept()
    try:
        # Nhận thông điệp nhiệm vụ từ client
        data = await websocket.receive_text()
        task = data.strip()
        if not task:
            await websocket.send_text(json.dumps({"type": "error", "message": "Task is empty!"}))
            await websocket.close()
            return

        # Cập nhật task id
        global task_id_counter
        async with task_lock:
            task_id_counter += 1
            current_task_id = task_id_counter

        # Tạo handler tạm thời gửi log của browser_use.agent đến kết nối này.
        temp_handler = WebSocketTaskLogHandler(websocket)
        temp_handler.setLevel(logging.INFO)
        # Formatter chỉ hiển thị message (loại bỏ datetime, level, ...)
        temp_handler.setFormatter(logging.Formatter("%(message)s"))
        temp_handler.addFilter(AgentOnlyFilter())
        root_logger.addHandler(temp_handler)

        # logging.getLogger("browser_use.agent").info(f"Received task via WebSocket: {task}")
        # Chạy task (await trực tiếp)
        await execute_task(current_task_id, task)
    except Exception as e:
        logging.getLogger("browser_use.agent").error(f"Error executing task via WebSocket: {e}")
    finally:
        # Loại bỏ handler tạm thời
        root_logger.removeHandler(temp_handler)
        try:
            await websocket.send_text(json.dumps({"type": "info", "message": "Task finished."}))
        except Exception:
            pass
        await websocket.close()
