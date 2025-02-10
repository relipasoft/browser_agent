# main.py

# Important Instructions:
# 1. Close any existing Chrome instances.
# 2. Start Chrome with remote debugging enabled:
#    /Applications/Google\ Chrome.app/Contents/MacOS/Google\ Chrome --remote-debugging-port=9222
# 3. Run the FastAPI server:
#    uvicorn main:app --host 127.0.0.1 --port 8888 --reload --workers 1
# make sure you set OPENAI_API_KEY=yourOpenAIKeyHere to .env file

import os
os.environ["PYDANTIC_V1_COMPAT_MODE"] = "true"

from langchain_ollama import ChatOllama
from browser_use import Agent
from dotenv import load_dotenv
import platform
import asyncio
from fastapi import FastAPI, HTTPException, Query, BackgroundTasks
from pydantic import BaseModel
from browser_use.browser.browser import Browser, BrowserConfig
import logging
import traceback
from datetime import datetime
from typing import List, Optional
from enum import Enum
from fastapi.middleware.cors import CORSMiddleware



# ----------------------------
# 1. Configure Logging
# ----------------------------
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# ----------------------------
# 2. Load Environment Variables
# ----------------------------
load_dotenv()

# ----------------------------
# 3. Initialize FastAPI App
# ----------------------------
app = FastAPI(title="AI Agent API with BrowserUse", version="1.0")


# Configure CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # For development: allow all origins. In production, specify exact origins.
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
# 5. Initialize Task Registry
# ----------------------------
task_records: List[TaskRecord] = []
task_id_counter: int = 0
task_lock = asyncio.Lock()  # To manage concurrent access to task_records

# ----------------------------
# 6. Define Background Task Function
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
    
    # Verify that the Chrome executable exists at the determined path
    if not os.path.exists(chrome_path):
        raise FileNotFoundError(f"Google Chrome executable not found at: {chrome_path}")
    
    return chrome_path



async def execute_task(task_id: int, task: str):
    """
    Background task to execute the AI agent.
    Initializes a new browser instance for each task to ensure isolation.
    """
    global task_records
    browser = None  # Initialize browser instance for this task
    try:
        logger.info(f"Starting background task ID {task_id}: {task}")
        
        # Create and add the task record with status 'running'
        async with task_lock:
            task_record = TaskRecord(
                id=task_id,
                task=task,
                status=TaskStatus.RUNNING,
                start_time=datetime.utcnow()
            )
            task_records.append(task_record)
        
        # Initialize a new browser instance for this task
        logger.info(f"Task ID {task_id}: Initializing new browser instance.")
        browser = Browser(
            config=BrowserConfig(
                chrome_instance_path=get_chrome_path(),  # Update if different
                disable_security=True,
                headless=False,  # Set to True for headless mode
                # Removed 'remote_debugging_port' as it caused issues
            )
        )
        logger.info(f"Task ID {task_id}: Browser initialized successfully.")
        
        # Initialize and run the Agent with the new browser instance
        agent = Agent(
            task=task,
            llm=ChatOllama(
            model="qwen2.5",
            num_ctx=32000
            ),
            browser=browser
        )
        logger.info(f"Task ID {task_id}: Agent initialized. Running task.")
        result = await agent.run()
        logger.info(f"Task ID {task_id}: Agent.run() completed successfully.")
        
        # Update the task record with status 'completed'
        async with task_lock:
            for record in task_records:
                if record.id == task_id:
                    record.status = TaskStatus.COMPLETED
                    record.end_time = datetime.utcnow()
                    record.duration = (record.end_time - record.start_time).total_seconds()
                    record.result = result
                    break

    except Exception as e:
        logger.error(f"Error in background task ID {task_id}: {e}")
        logger.error(traceback.format_exc())
        
        # Update the task record with status 'failed'
        async with task_lock:
            for record in task_records:
                if record.id == task_id:
                    record.status = TaskStatus.FAILED
                    record.end_time = datetime.utcnow()
                    record.duration = (record.end_time - record.start_time).total_seconds()
                    record.error = str(e)
                    break
    finally:
        # Ensure that the browser is closed in case of failure or success
        if browser:
            try:
                logger.info(f"Task ID {task_id}: Closing browser instance.")
                await browser.close()
                logger.info(f"Task ID {task_id}: Browser instance closed successfully.")
            except Exception as close_e:
                logger.error(f"Task ID {task_id}: Error closing browser: {close_e}")
                logger.error(traceback.format_exc())

# ----------------------------
# 7. Define POST /run Endpoint
# ----------------------------
@app.post("/run", response_model=TaskResponse)
async def run_task_post(request: TaskRequest, background_tasks: BackgroundTasks):
    """
    POST Endpoint to run the AI agent with a specified task.
    
    - **task**: The task description for the AI agent.
    """
    global task_id_counter
    task = request.task
    logger.info(f"Received task via POST: {task}")
    
    # Increment task ID
    async with task_lock:
        task_id_counter += 1
        current_task_id = task_id_counter
    
    # Enqueue the background task
    background_tasks.add_task(execute_task, current_task_id, task)
    
    # Respond immediately
    return TaskResponse(result="Task is being processed.")

# ----------------------------
# 8. Define GET /run Endpoint
# ----------------------------
@app.get("/run", response_model=TaskResponse)
async def run_task_get(
    task: str = Query(..., description="The task description for the AI agent."),
    background_tasks: BackgroundTasks = None
):
    """
    GET Endpoint to run the AI agent with a specified task.
    
    - **task**: The task description for the AI agent.
    """
    global task_id_counter
    logger.info(f"Received task via GET: {task}")
    
    # Increment task ID
    async with task_lock:
        task_id_counter += 1
        current_task_id = task_id_counter
    
    # Enqueue the background task
    background_tasks.add_task(execute_task, current_task_id, task)
    
    # Respond immediately
    return TaskResponse(result="Task is being processed.")

# ----------------------------
# 9. Define GET /lastResponses Endpoint
# ----------------------------
@app.get("/lastResponses", response_model=List[TaskRecord])
async def get_last_responses(
    limit: Optional[int] = Query(100, description="Maximum number of task records to return"),
    status: Optional[TaskStatus] = Query(None, description="Filter by task status")
):
    """
    GET Endpoint to retrieve the last task responses.
    
    - **limit**: The maximum number of task records to return (default: 100).
    - **status**: (Optional) Filter tasks by status ('running', 'completed', 'failed').
    
    Returns a list of task records in descending order of task ID.
    """
    async with task_lock:
        filtered_tasks = task_records.copy()
        if status:
            filtered_tasks = [task for task in filtered_tasks if task.status == status]
        # Sort and limit
        sorted_tasks = sorted(filtered_tasks, key=lambda x: x.id, reverse=True)[:limit]
        return sorted_tasks

# ----------------------------
# 10. Define Root Endpoint
# ----------------------------
@app.get("/")
def read_root():
    return {
        "message": "AI Agent API with BrowserUse is running. Use the /run endpoint with a 'task' field in the POST request body or as a query parameter in a GET request to execute tasks."
    }

#For executable.
# ----------------------------
# 12. Entry Point
# ----------------------------
if __name__ == "__main__":
    import uvicorn

    uvicorn.run("mainOllama:app", host="127.0.0.1", port=8888, reload=True, workers=1)