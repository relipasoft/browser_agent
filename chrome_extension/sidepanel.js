const chatContainer = document.getElementById('chat-container');
const chatInput = document.getElementById('chat-input');
const sendButton = document.getElementById('send-button');

/**
 * Tạo khối tin nhắn Bot gồm phần header và log.
 * @returns {Object} Chứa các phần tử container, header và log.
 */
function createBotMessage() {
  const container = document.createElement('div');
  container.classList.add('bot-message');

  const header = document.createElement('div');
  header.classList.add('bot-header');
  header.textContent = "Thinking...";

  const log = document.createElement('div');
  log.classList.add('bot-log');

  container.appendChild(header);
  container.appendChild(log);
  chatContainer.appendChild(container);
  chatContainer.scrollTop = chatContainer.scrollHeight;
  
  return { container, header, log };
}

/**
 * Thêm dòng văn bản vào phần log.
 * @param {string} text 
 * @param {HTMLElement} logContainer 
 */
function appendLogText(text, logContainer) {
  const p = document.createElement('p');
  p.textContent = text;
  logContainer.appendChild(p);
  logContainer.parentElement.scrollTop = logContainer.parentElement.scrollHeight;
}

/**
 * Xử lý message nhận được từ WebSocket với định dạng JSON.
 * Nếu type là "process": thêm nội dung vào log.
 * Nếu type là "result": cập nhật header và ẩn log (cho dropdown).
 * @param {string} data 
 * @param {HTMLElement} logContainer 
 * @param {HTMLElement} headerElement 
 */
function processIncomingJSON(data, logContainer, headerElement) {
  let messageObj;
  try {
    messageObj = JSON.parse(data);
  } catch (err) {
    console.error("Error parsing JSON:", err);
    appendLogText(data, logContainer);
    return;
  }

  if (!messageObj.type || !messageObj.message) {
    console.warn("Received JSON without type or message:", messageObj);
    return;
  }

  if (messageObj.type === "process") {
    // Thêm nội dung processing vào log
    appendLogText(messageObj.message, logContainer);
  } else if (messageObj.type === "result") {
    // Cập nhật header với kết quả cuối cùng
    headerElement.textContent = messageObj.message;
    // Ẩn log container; cho phép click vào header để mở rộng xem chi tiết
    logContainer.style.display = "none";
    headerElement.style.cursor = "pointer";
    headerElement.addEventListener('click', function() {
      logContainer.style.display = (logContainer.style.display === "none") ? "block" : "none";
    });
  } else {
    console.warn("Unknown message type:", messageObj.type);
  }
}

/**
 * Hàm gửi task qua WebSocket và xử lý phản hồi.
 */
function sendTask() {
  const task = chatInput.value.trim();
  if (!task) return;

  // Hiển thị tin nhắn của người dùng
  const userMessage = document.createElement('div');
  userMessage.classList.add('message', 'user');
  userMessage.textContent = task;
  chatContainer.appendChild(userMessage);
  chatContainer.scrollTop = chatContainer.scrollHeight;
  
  chatInput.value = '';
  sendButton.disabled = true;

  // Tạo khối Bot message với header "Thinking..." và log rỗng
  const botMessage = createBotMessage();

  // Mở kết nối WebSocket tới ws://localhost:8888/ws/run
  const socket = new WebSocket("ws://localhost:8888/ws/run");

  socket.onopen = () => {
    console.log("WebSocket connection opened.");
    // Gửi task dưới dạng JSON
    socket.send(JSON.stringify({ task: task }));
  };

  socket.onmessage = (event) => {
    console.log("Received message:", event.data);
    processIncomingJSON(event.data, botMessage.log, botMessage.header);
  };

  socket.onerror = (error) => {
    console.error("WebSocket error:", error);
    appendLogText("WebSocket error occurred.", botMessage.log);
  };

  socket.onclose = () => {
    console.log("WebSocket connection closed.");
    sendButton.disabled = false;
  };
}

sendButton.addEventListener('click', sendTask);
chatInput.addEventListener('keydown', (e) => {
  if (e.key === 'Enter') sendTask();
});
