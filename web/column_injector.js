window.ColumnInjector = {
  getColumns() {
    return JSON.parse(localStorage.getItem("custom_columns") || "[]");
  },

  saveColumns(cols) {
    localStorage.setItem("custom_columns", JSON.stringify(cols));
  },

  injectHeaders(tableId, activeCols) {
    const table = document.getElementById(tableId);
    if (!table) return;
    const theadTr = table.querySelector("thead tr");
    
    // Remove existing custom headers
    theadTr.querySelectorAll(".custom-injected-header").forEach(el => el.remove());
    
    activeCols.forEach(col => {
      const th = document.createElement("th");
      th.className = "custom-injected-header";
      th.setAttribute("data-key", col.id);
      th.setAttribute("data-col", col.id);
      th.textContent = col.name;
      th.title = col.description;
      
      if (tableId === "leaderboard") {
        th.addEventListener("click", () => {
          if (window.leaderboardSort && window.leaderboardSort.key === col.id) {
            window.leaderboardSort.dir *= -1;
          } else if (window.leaderboardSort) {
            window.leaderboardSort.key = col.id;
            window.leaderboardSort.dir = -1;
          }
          window.renderLeaderboard();
        });
      }
      
      theadTr.appendChild(th);
    });
  },

  async applyToTable(tableId, targetDataArray, renderCallback) {
    const cols = this.getColumns().filter(c => c.appliedTo && c.appliedTo.includes(tableId));
    
    if (cols.length === 0) {
      this.injectHeaders(tableId, []);
      renderCallback();
      return;
    }
    
    for (const col of cols) {
      try {
        const res = await fetch("/api/column/preview", {
          method: "POST",
          headers: { "Content-Type": "application/json" },
          body: JSON.stringify({ sql: col.sql })
        });
        const data = await res.json();
        
        if (data.rows) {
          targetDataArray.forEach(row => {
            const match = data.rows.find(pr => {
              for (const key in pr) {
                 if (key === 'value') continue;
                 if (row[key] !== undefined && pr[key] != row[key]) {
                   return false; // mismatch on join key
                 }
              }
              return true; // all returned keys matched the row
            });
            row[col.id] = match ? match.value : null;
          });
        }
      } catch (e) {
        console.error("Failed to load custom column", col.name, e);
      }
    }
    
    this.injectHeaders(tableId, cols);
    renderCallback();
  },

  renderToggleUI(containerId, tableId, reloadCallback) {
    const container = document.getElementById(containerId);
    if (!container) return;
    container.innerHTML = "";
    
    const cols = this.getColumns();
    if (cols.length === 0) {
      container.innerHTML = `<span style="color:var(--text-secondary);font-size:0.85rem;">No custom columns.</span>`;
      return;
    }
    
    cols.forEach(col => {
      const isApplied = col.appliedTo && col.appliedTo.includes(tableId);
      const label = document.createElement("label");
      const checkbox = document.createElement("input");
      checkbox.type = "checkbox";
      checkbox.checked = isApplied;
      checkbox.addEventListener("change", (e) => {
        let allCols = this.getColumns();
        let targetCol = allCols.find(c => c.id === col.id);
        if (!targetCol.appliedTo) targetCol.appliedTo = [];
        
        if (e.target.checked) {
          if (!targetCol.appliedTo.includes(tableId)) targetCol.appliedTo.push(tableId);
        } else {
          targetCol.appliedTo = targetCol.appliedTo.filter(t => t !== tableId);
        }
        this.saveColumns(allCols);
        
        reloadCallback();
      });
      
      label.appendChild(checkbox);
      label.append(` ${col.name}`);
      container.appendChild(label);
    });
  }
};
