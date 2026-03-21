const chatHistory = document.getElementById("chat-history");
const chatInput = document.getElementById("chat-input");
const chatSend = document.getElementById("chat-send");
const savedList = document.getElementById("saved-columns-list");

function getSavedColumns() {
  const data = localStorage.getItem("custom_columns");
  return data ? JSON.parse(data) : [];
}

function saveColumn(columnData) {
  const cols = getSavedColumns();
  columnData.id = crypto.randomUUID();
  columnData.createdAt = new Date().toISOString();
  columnData.appliedTo = [];
  cols.push(columnData);
  localStorage.setItem("custom_columns", JSON.stringify(cols));
  renderSavedColumns();
  showToast("Column saved successfully!");
}

function deleteColumn(id) {
  let cols = getSavedColumns();
  cols = cols.filter(c => c.id !== id);
  localStorage.setItem("custom_columns", JSON.stringify(cols));
  renderSavedColumns();
  showToast("Column deleted.");
}

function renderSavedColumns() {
  const cols = getSavedColumns();
  savedList.innerHTML = "";
  if (cols.length === 0) {
    savedList.innerHTML = '<p class="empty-state">No custom columns saved yet.</p>';
    return;
  }
  
  cols.forEach(col => {
    const el = document.createElement("div");
    el.className = "saved-column-card";
    el.innerHTML = `
      <h3>${col.name}</h3>
      <p>${col.description}</p>
      <div class="card-actions">
        <button class="danger-small" onclick="deleteColumn('${col.id}')">Delete</button>
      </div>
    `;
    savedList.appendChild(el);
  });
}

function appendMessage(text, role, isHtml = false) {
  const bubble = document.createElement("div");
  bubble.className = `message-bubble ${role}`;
  if (isHtml) {
    bubble.innerHTML = text;
  } else {
    bubble.textContent = text;
  }
  chatHistory.appendChild(bubble);
  chatHistory.scrollTop = chatHistory.scrollHeight;
  return bubble;
}

function showToast(message) {
  const toast = document.getElementById("toast");
  toast.textContent = message;
  toast.classList.remove("hidden");
  toast.style.opacity = "1";
  setTimeout(() => {
    toast.style.opacity = "0";
    setTimeout(() => toast.classList.add("hidden"), 300);
  }, 3000);
}

// Ensure globally accessible for onclick
window.deleteColumn = deleteColumn;

chatSend.addEventListener("click", async () => {
    const prompt = chatInput.value.trim();
    if (!prompt) return;
    
    chatInput.value = "";
    appendMessage(prompt, "user");
    
    const loadingBubble = appendMessage("Generating SQL logic...", "bot");
    
    try {
        const res = await fetch("/api/column/generate", {
            method: "POST",
            headers: { "Content-Type": "application/json" },
            body: JSON.stringify({ prompt })
        });
        
        const data = await res.json();
        if (data.error) throw new Error(data.error);
        
        loadingBubble.innerHTML = `
            <strong>${data.name}</strong><br>
            <p>${data.description}</p>
            <pre class="sql-code"><code>${data.sql}</code></pre>
            <p class="preview-status" id="preview-${data.name.replace(/\\s+/g,'-')}"><em>Running preview...</em></p>
        `;
        
        // Run preview
        const previewRes = await fetch("/api/column/preview", {
            method: "POST",
            headers: { "Content-Type": "application/json" },
            body: JSON.stringify({ sql: data.sql })
        });
        const previewData = await previewRes.json();
        const previewStatus = loadingBubble.querySelector(".preview-status");
        
        if (previewData.error) {
            previewStatus.innerHTML = `<span style="color:var(--danger);">${previewData.error}</span>`;
        } else {
            previewStatus.innerHTML = `✅ Preview successful: returned ${previewData.count} rows.`;
            
            const btnContainer = document.createElement("div");
            btnContainer.className = "bubble-actions";
            const saveBtn = document.createElement("button");
            saveBtn.textContent = "Save Column";
            saveBtn.onclick = () => {
                saveColumn({ name: data.name, description: data.description, sql: data.sql });
                saveBtn.disabled = true;
                saveBtn.textContent = "Saved";
            };
            btnContainer.appendChild(saveBtn);
            loadingBubble.appendChild(btnContainer);
        }
        
    } catch (e) {
        loadingBubble.innerHTML = `<span style="color:var(--danger);">Error: ${e.message}</span>`;
    }
    chatHistory.scrollTop = chatHistory.scrollHeight;
});

chatInput.addEventListener("keydown", (e) => {
    if (e.key === "Enter") chatSend.click();
});

renderSavedColumns();
