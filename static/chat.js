document.addEventListener('DOMContentLoaded', () => {
  const sendBtn = document.getElementById('sendBtn');
  const input = document.getElementById('messageInput');
  const messages = document.getElementById('messages');

  function appendMessage(who, text, isHtml = false) {
    const el = document.createElement('div');
    el.className = 'message ' + who;
    if (isHtml) {
      el.innerHTML = text;
    } else {
      el.textContent = text;
    }
    messages.appendChild(el);
    messages.scrollTop = messages.scrollHeight;
  }

  sendBtn.addEventListener('click', async () => {
    const text = input.value.trim();
    if (!text) return;
    appendMessage('user', text);
    input.value = '';
    try {
      const res = await fetch('/chat', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ message: text }),
      });
      const data = await res.json();
      appendMessage('bot', data.reply || 'No reply', true);
    } catch (err) {
      appendMessage('bot', 'Error contacting server');
    }
  });

  input.addEventListener('keyup', (e) => {
    if (e.key === 'Enter') sendBtn.click();
  });
});
