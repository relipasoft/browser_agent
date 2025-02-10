// sidepanel.js

const chatContainer = document.getElementById('chat-container');
const chatInput = document.getElementById('chat-input');
const sendButton = document.getElementById('send-button');

/**
 * Hàm thêm tin nhắn vào container chat.
 * @param {string} text - Nội dung tin nhắn.
 * @param {string} sender - Người gửi ('user' hoặc 'bot').
 */
function appendMessage(text, sender) {
  const messageElem = document.createElement('div');
  messageElem.classList.add('message', sender);
  messageElem.innerText = text;
  chatContainer.appendChild(messageElem);
  // Cuộn xuống tin nhắn mới nhất
  chatContainer.scrollTop = chatContainer.scrollHeight;
}

/**
 * Hàm gửi task đến API và hiển thị phản hồi.
 */
async function sendMessage() {
  const task = chatInput.value.trim();
  if (!task) return;
  
  // Hiển thị tin nhắn của người dùng
  appendMessage(task, 'user');
  chatInput.value = '';
  sendButton.disabled = true;
  
  try {
    console.log("Gửi task tới API:", task);
    const response = await fetch('http://localhost:8888/run', {
      method: 'POST',
      headers: {
        'Content-Type': 'application/json'
      },
      body: JSON.stringify({ task: task })
    });
    console.log("Trạng thái phản hồi API:", response.status);
    if (!response.ok) {
      throw new Error('Network response was not ok');
    }
    const data = await response.json();
    console.log("Dữ liệu nhận từ API:", data);
    // Hiển thị phản hồi từ API (trong thuộc tính "result")
    appendMessage(data.result, 'bot');
  } catch (error) {
    console.error('Lỗi khi gửi task:', error);
    appendMessage('Có lỗi xảy ra khi gửi task.', 'bot');
  } finally {
    sendButton.disabled = false;
  }
}

// Đăng ký sự kiện gửi task khi nhấn nút hoặc phím Enter
sendButton.addEventListener('click', sendMessage);
chatInput.addEventListener('keydown', (e) => {
  if (e.key === 'Enter') {
    sendMessage();
  }
});
