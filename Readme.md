# Project Setup Guide

This project includes two script files to run a FastAPI application with **uvicorn** and automatically open Chrome in debugging mode (port 9222) if no Chrome is already open in that mode:

- **run.bat**: For Windows
- **run.command**: For macOS

Additionally, the project includes a Chrome Extension located in the **chrome_extension** folder. The guide below explains how to run the script files and install the extension.

---

## 1. Installing Required Packages
Python version 3.11 recommended

Before running any script file, you need to install the required packages from the `requirements.txt` file.

Open Terminal (macOS) or Command Prompt (Windows) and run:

```bash
pip install -r requirements.txt
```

## 2. Environment Setup

Create a `.env` file in the project root directory with your OpenAI API key:

```
OPENAI_API_KEY=your_api_key_here
```

## 3. Running the Application

### For Windows:
Double-click the `run.bat` file or run it from Command Prompt:
```
.\run.bat
```

### For macOS:
Make the script executable first, then run it:
```bash
chmod +x run.command
./run.command
```

The script will:
1. Install required packages
2. Start the FastAPI server with uvicorn on port 8888
3. Open Chrome in debugging mode on port 9222 (if not already running)

## 4. Installing the Chrome Extension

1. Open Chrome and navigate to `chrome://extensions/`
2. Enable "Developer mode" (toggle in the top-right corner)
3. Click "Load unpacked" button
4. Select the `chrome_extension` folder from this project
5. The "Relipa Browser Agent" extension should now appear in your extensions list

## 5. Using the Extension

1. After the extension is installed, you'll see a new icon in your Chrome toolbar
2. Click on the icon to open the side panel
3. Enter your task in the input field and click "Send"
4. The extension will communicate with the FastAPI server and display results in the chat interface

## 6. Docker Support

The project also includes Docker support. To run with Docker:

```bash
docker-compose up --build
```

Note that you need to configure the Docker volume mapping in `docker-compose.yml` based on your operating system to properly link Chrome:

- For Windows: Uncomment the Windows volume mapping
- For macOS: Uncomment the macOS volume mapping
- For Linux: Uncomment the Linux volume mapping

## 7. Troubleshooting

- If Chrome doesn't open automatically, verify your Chrome installation path
- If the server fails to start, check if port 8888 is already in use
- If the extension can't connect to the server, ensure the server is running and accessible on localhost:8888