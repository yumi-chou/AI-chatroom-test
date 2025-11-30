const API_BASE = "https://ai-chatroom-test.vercel.app";

let accessToken = null;


const loginSection = document.getElementById("login-section");
const chatSection = document.getElementById("chat-section");
const loginForm = document.getElementById("login-form");
const loginStatus = document.getElementById("login-status");
const logoutBtn = document.getElementById("logout-btn");

const chatWindow = document.getElementById("chat-window");
const chatForm = document.getElementById("chat-form");
const messageInput = document.getElementById("message-input");
const rememberHistoryCheckbox = document.getElementById("remember-history");


loginForm.addEventListener("submit", async (e) => {
  e.preventDefault();
  const username = document.getElementById("username").value.trim();
  const password = document.getElementById("password").value.trim();

  loginStatus.textContent = "登入中…";
  loginStatus.className = "status";

  try {
    const res = await fetch(`${API_BASE}/auth/login`, {
      method: "POST",
      headers: {
        "Content-Type": "application/json",
      },
      body: JSON.stringify({ username, password }),
    });

    if (!res.ok) {
      const data = await res.json();
      throw new Error(data.detail || "Login failed");
    }

    const data = await res.json();
    accessToken = data.access_token;
    loginStatus.textContent = "登入成功";
    loginStatus.className = "status success";


    loginSection.classList.add("hidden");
    chatSection.classList.remove("hidden");


    chatWindow.innerHTML = "";
    appendMessage("system", `已登入為 ${username}，可以開始聊天囉！`);
  } catch (err) {
    loginStatus.textContent = `登入失敗：${err.message}`;
    loginStatus.className = "status error";
  }
});

logoutBtn.addEventListener("click", () => {
  accessToken = null;
  chatSection.classList.add("hidden");
  loginSection.classList.remove("hidden");
  chatWindow.innerHTML = "";
  loginStatus.textContent = "";
});

chatForm.addEventListener("submit", async (e) => {
  e.preventDefault();
  if (!accessToken) return;

  const message = messageInput.value.trim();
  if (!message) return;

  appendMessage("user", message);
  messageInput.value = "";


  try {
    appendMessage("system", "（思考中…）");
    scrollToBottom();

    const res = await fetch(`${API_BASE}/chat`, {
      method: "POST",
      headers: {
        "Content-Type": "application/json",
        Authorization: `Bearer ${accessToken}`,
      },
      body: JSON.stringify({
        message,
        remember_history: rememberHistoryCheckbox.checked,
      }),
    });

    removeLastSystemMessage();

    if (!res.ok) {
      const data = await res.json();
      throw new Error(data.detail || "Chat failed");
    }

    const data = await res.json();
    appendMessage("assistant", data.reply);
    scrollToBottom();
  } catch (err) {
    removeLastSystemMessage();
    appendMessage("system", `錯誤：${err.message}`);
    scrollToBottom();
  }
});

function appendMessage(role, content) {
  const div = document.createElement("div");
  div.classList.add("msg", role);
  div.textContent = content;
  chatWindow.appendChild(div);
}

function scrollToBottom() {
  chatWindow.scrollTop = chatWindow.scrollHeight;
}

function removeLastSystemMessage() {
  const msgs = chatWindow.querySelectorAll(".msg.system");
  if (msgs.length > 0) {
    const last = msgs[msgs.length - 1];
    chatWindow.removeChild(last);
  }
}
