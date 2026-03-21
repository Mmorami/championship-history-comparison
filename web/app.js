let leaderboardData = [];
let leaderboardSort = { key: "overall_score", dir: -1 }; // Default score descending
let customComparison = [];

window.leaderboardSort = leaderboardSort;
window.renderLeaderboard = renderLeaderboard;
window.loadLeaderboard = loadLeaderboard;
window.loadSeasonCompare = loadSeasonCompare;

// Normalization States
let leaderboardNorm = false;
let seasonNorm = false;
let comparisonNorm = false;

function getNormVal(val, pl, type) {
  if (!pl) return "0.000";
  if (type === 'pct') return (val / pl * 100).toFixed(1) + '%';
  if (type === 'ppg') return (val / pl).toFixed(3);
  if (type === 'rate') return (val / pl).toFixed(2);
  return val;
}

async function loadLeaderboard() {
  const res = await fetch("/api/leaderboard");
  const data = await res.json();
  const meta = document.getElementById("meta");
  meta.textContent = `Run: ${data.metadata.run_id || "n/a"} | Cutoff: ${data.metadata.data_cutoff_utc || "n/a"}`;

  leaderboardData = data.rows || [];
  
  if (window.ColumnInjector) {
    window.ColumnInjector.applyToTable("leaderboard", leaderboardData, () => {
      window.ColumnInjector.renderToggleUI("injector-toggle-leaderboard", "leaderboard", loadLeaderboard);
      renderLeaderboard();
    });
  } else {
    renderLeaderboard();
  }
}

// Attach sorting listener using event delegation
document.getElementById("leaderboard").addEventListener("click", (e) => {
  const th = e.target.closest("th[data-key]");
  if (!th) return;
  const key = th.getAttribute("data-key");
  if (leaderboardSort.key === key) {
    leaderboardSort.dir *= -1;
  } else {
    leaderboardSort.key = key;
    leaderboardSort.dir = -1;
  }
  renderLeaderboard();
});

function renderLeaderboard() {
  const tbody = document.querySelector("#leaderboard tbody");
  const headers = Array.from(document.querySelectorAll("#leaderboard thead th[data-key]"));
  tbody.innerHTML = "";

  const sortedRows = [...leaderboardData].sort((a, b) => {
    let valA = a[leaderboardSort.key];
    let valB = b[leaderboardSort.key];

    if (leaderboardSort.key === "rank") {
      valA = leaderboardData.indexOf(a);
      valB = leaderboardData.indexOf(b);
    }

    if (valA < valB) return -1 * leaderboardSort.dir;
    if (valA > valB) return 1 * leaderboardSort.dir;
    return 0;
  });

  sortedRows.forEach((row) => {
    const tr = document.createElement("tr");
    headers.forEach(th => {
      const key = th.getAttribute("data-key");
      const td = document.createElement("td");
      td.setAttribute("data-col", key);

      if (key === "rank") {
        td.textContent = leaderboardData.indexOf(row) + 1;
      } else if (leaderboardNorm && ["wins", "draws", "losses", "goals_for", "goals_against", "goal_diff", "points"].includes(key)) {
        if (key === "points") td.textContent = getNormVal(row[key], row.played, 'ppg');
        else if (["goals_for", "goals_against", "goal_diff"].includes(key)) td.textContent = getNormVal(row[key], row.played, 'rate');
        else td.textContent = getNormVal(row[key], row.played, 'pct');
      } else {
        td.textContent = row[key] ?? "";
      }
      tr.appendChild(td);
    });
    tbody.appendChild(tr);
  });

  document.getElementById("header-leaderboard-pts").textContent = leaderboardNorm ? "PPG" : "Pts";

  // Update header classes
  headers.forEach(th => {
    th.classList.remove("sorted-asc", "sorted-desc");
    if (th.getAttribute("data-key") === leaderboardSort.key) {
      th.classList.add(leaderboardSort.dir === 1 ? "sorted-asc" : "sorted-desc");
    }
  });
}

async function populateSeasonsDropdown() {
  const select = document.getElementById("season");
  const customSelect = document.getElementById("custom-season");
  select.innerHTML = "";
  customSelect.innerHTML = "";
  const res = await fetch("/api/seasons");
  const data = await res.json();
  const seasons = data.rows || [];

  seasons.forEach((sid) => {
    const opt = document.createElement("option");
    opt.value = sid;
    opt.textContent = sid;
    select.appendChild(opt);

    const optCustom = opt.cloneNode(true);
    customSelect.appendChild(optCustom);
  });

  if (seasons.length > 0) {
    select.value = seasons[seasons.length - 1];
    customSelect.value = seasons[seasons.length - 1];
    updateCustomTeamDropdown();
  }
}

async function updateCustomTeamDropdown() {
  const seasonId = document.getElementById("custom-season").value;
  const select = document.getElementById("custom-team");
  if (!seasonId) return;
  select.innerHTML = '<option value="">Loading...</option>';

  const res = await fetch(`/api/season/${seasonId}/compare?slice=all`);
  const data = await res.json();
  const rows = data.rows || [];

  rows.sort((a, b) => a.team_name_canonical.localeCompare(b.team_name_canonical));

  select.innerHTML = "";
  rows.forEach(row => {
    const opt = document.createElement("option");
    opt.value = JSON.stringify(row);
    opt.textContent = row.team_name_canonical;
    select.appendChild(opt);
  });
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

function addToCustomComparison(teamData) {
  const exists = customComparison.some(c => c.season_id === teamData.season_id && c.team_id === teamData.team_id);
  if (exists) {
    showToast(`${teamData.team_name_canonical} (${teamData.season_id}) is already in comparison.`);
    return;
  }

  customComparison.push(teamData);
  renderCustomComparison();
  showToast(`Added ${teamData.team_name_canonical} (${teamData.season_id}) to bench!`);
}

function renderCustomComparison() {
  const finishRender = (augmentedData) => {
    const tbody = document.querySelector("#custom-comparison tbody");
    const headers = Array.from(document.querySelectorAll("#custom-comparison thead th"));
    tbody.innerHTML = "";

    document.getElementById("comparison-count").textContent = augmentedData.length;

    augmentedData.forEach((row, idx) => {
      const tr = document.createElement("tr");
      const pl = row.played;
      const display = (val, type) => comparisonNorm ? getNormVal(val, pl, type) : val;

      headers.forEach(th => {
        const td = document.createElement("td");
        const key = th.getAttribute("data-key");
        if (!key) return;
        
        td.setAttribute("data-col", key);
        
        if (key === "action") {
          td.innerHTML = `<button class="danger-small" onclick="removeFromCustomComparison(${idx})">Remove</button>`;
        } else if (key === "points") {
          td.textContent = display(row.points, 'ppg');
        } else if (["wins", "draws", "losses"].includes(key)) {
          td.textContent = display(row[key], 'pct');
        } else if (["goals_for", "goals_against", "goal_diff"].includes(key)) {
          td.textContent = display(row[key], 'rate');
        } else {
          td.textContent = row[key] ?? "";
        }
        tr.appendChild(td);
      });
      tbody.appendChild(tr);
    });

    document.getElementById("header-comparison-pts").textContent = comparisonNorm ? "PPG" : "Pts";
  };

  if (window.ColumnInjector) {
    window.ColumnInjector.applyToTable("custom-comparison", customComparison, () => {
      window.ColumnInjector.renderToggleUI("injector-toggle-comparison", "custom-comparison", renderCustomComparison);
      finishRender(customComparison);
    });
  } else {
    finishRender(customComparison);
  }
}

window.removeFromCustomComparison = function (idx) {
  customComparison.splice(idx, 1);
  renderCustomComparison();
};

async function loadTeamContext(teamId) {
  if (!teamId) return;

  const slice = document.getElementById("slice").value;
  const res = await fetch(`/api/team/${teamId}/context`);
  const data = await res.json();

  const drawer = document.getElementById("context-drawer");
  const managersDiv = document.getElementById("context-managers");
  const scorersDiv = document.getElementById("context-scorers");
  const hint = document.getElementById("context-hint");

  if (hint) hint.style.display = "none";
  drawer.classList.add("open");

  const managers = data.managers || [];
  if (!managers.length) {
    managersDiv.textContent = "No manager context data ingested yet for this team/season.";
  } else {
    managersDiv.innerHTML = `
      <h3>Managers</h3>
      <ul>
        ${managers
        .slice(0, 8)
        .map(
          (m) =>
            `<li>${m.season_id}: ${m.manager_name}${m.source_confidence ? ` (conf ${m.source_confidence})` : ""}</li>`
        )
        .join("")}
      </ul>
    `;
  }

  const scorers = data.top_scorers || [];
  if (!scorers.length) {
    scorersDiv.textContent = "No top-scorer data ingested yet for this team/season.";
  } else {
    scorersDiv.innerHTML = `
      <h3>Top Scorers (team)</h3>
      <ul>
        ${scorers
        .slice(0, 8)
        .map(
          (s) =>
            `<li>${s.season_id}: ${s.player_name} (${s.goals || 0} goals${s.assists != null ? `, ${s.assists} assists` : ""})</li>`
        )
        .join("")}
      </ul>
    `;
  }
}

async function loadSeasonCompare() {
  const season = document.getElementById("season").value.trim();
  const slice = document.getElementById("slice").value;
  const res = await fetch(`/api/season/${season}/compare?slice=${slice}`);
  const data = await res.json();
  
  let seasonData = data.rows || [];
  
  const finishRender = (augmentedData) => {
    const tbody = document.querySelector("#season-table tbody");
    const headers = Array.from(document.querySelectorAll("#season-table thead th"));
    tbody.innerHTML = "";

    augmentedData.forEach((row) => {
    const tr = document.createElement("tr");
    tr.style.cursor = "pointer";
    tr.addEventListener("click", (e) => {
      if (e.target.tagName !== "BUTTON") loadTeamContext(row.team_id);
    });

    headers.forEach((th) => {
      const td = document.createElement("td");
      const dataCol = th.getAttribute("data-col");
      const text = th.textContent.toLowerCase();
      
      if (dataCol === "add") {
        td.setAttribute("data-col", "add");
        const btn = document.createElement("button");
        btn.textContent = "+";
        btn.className = "add-btn";
        btn.addEventListener("click", (e) => {
          e.stopPropagation();
          addToCustomComparison(row);
        });
        td.appendChild(btn);
      } else {
        const map = {
          pos: "position",
          team: "team_name_canonical",
          pl: "played",
          w: "wins",
          d: "draws",
          l: "losses",
          gf: "goals_for",
          ga: "goals_against",
          pts: "points",
          gd: "goal_diff",
        };
        const dataKey = th.getAttribute("data-key");
        const key = dataKey || map[text] || text;
        td.setAttribute("data-col", key);
        let val = row[key] ?? "";

        if (seasonNorm && ["wins", "draws", "losses", "goals_for", "goals_against", "goal_diff", "points"].includes(key)) {
          if (key === "points") val = getNormVal(val, row.played, 'ppg');
          else if (["goals_for", "goals_against", "goal_diff"].includes(key)) val = getNormVal(val, row.played, 'rate');
          else val = getNormVal(val, row.played, 'pct');
        }
        td.textContent = val;
      }
      tr.appendChild(td);
    });
    tbody.appendChild(tr);
  });

  document.getElementById("header-season-pts").textContent = seasonNorm ? "PPG" : "Pts";
  };
  
  if (window.ColumnInjector) {
    window.ColumnInjector.applyToTable("season-table", seasonData, () => {
      window.ColumnInjector.renderToggleUI("injector-toggle-season", "season-table", loadSeasonCompare);
      finishRender(seasonData);
    });
  } else {
    finishRender(seasonData);
  }
}

document.getElementById("load-season").addEventListener("click", loadSeasonCompare);
document.getElementById("custom-season").addEventListener("change", updateCustomTeamDropdown);
document.getElementById("add-custom").addEventListener("click", () => {
  const select = document.getElementById("custom-team");
  if (!select.value) return;
  addToCustomComparison(JSON.parse(select.value));
});
document.getElementById("clear-custom").addEventListener("click", () => {
  customComparison = [];
  renderCustomComparison();
});

// Layout Interactions
document.querySelectorAll(".nav-item").forEach(item => {
  item.addEventListener("click", () => {
    document.querySelectorAll(".nav-item").forEach(nav => nav.classList.remove("active"));
    item.classList.add("active");

    const targetId = item.getAttribute("data-target");
    document.querySelectorAll(".view-section").forEach(view => {
      view.style.display = view.id === targetId ? "block" : "none";
    });

    document.getElementById("view-title").textContent = item.textContent === "Dashboard" ? "Promotion Power Leaderboard" : "Season Explorer";
  });
});

document.getElementById("close-drawer").addEventListener("click", () => {
  document.getElementById("context-drawer").classList.remove("open");
});

document.getElementById("toggle-comparison").addEventListener("click", () => {
  document.getElementById("comparison-tray-overlay").classList.remove("hidden");
});

document.getElementById("close-comparison").addEventListener("click", () => {
  document.getElementById("comparison-tray-overlay").classList.add("hidden");
});

document.getElementById("toggle-leaderboard-norm").addEventListener("change", (e) => {
  leaderboardNorm = e.target.checked;
  renderLeaderboard();
});

document.getElementById("toggle-season-norm").addEventListener("change", (e) => {
  seasonNorm = e.target.checked;
  loadSeasonCompare();
});

document.getElementById("toggle-comparison-norm").addEventListener("change", (e) => {
  comparisonNorm = e.target.checked;
  renderCustomComparison();
});

// Gear Menu Logic
document.querySelectorAll(".gear-menu-container").forEach(container => {
  const btn = container.querySelector(".btn-icon");
  const dropdown = container.querySelector(".gear-dropdown");
  
  if (btn && dropdown) {
    btn.addEventListener("click", () => {
      // close others
      document.querySelectorAll(".gear-dropdown").forEach(d => {
        if (d !== dropdown) d.classList.add("hidden");
      });
      dropdown.classList.toggle("hidden");
    });
    
    document.addEventListener("click", (e) => {
      if (!container.contains(e.target)) {
        dropdown.classList.add("hidden");
      }
    });
  }
});

// Column Visibility Logic
const colListControls = document.querySelectorAll("#col-dropdown input[type='checkbox']");
colListControls.forEach(checkbox => {
  checkbox.addEventListener("change", (e) => {
    const colKey = e.target.value;
    if (e.target.checked) {
      document.body.classList.remove(`hide-${colKey}`);
    } else {
      document.body.classList.add(`hide-${colKey}`);
    }
  });
});

loadLeaderboard();
populateSeasonsDropdown().then(loadSeasonCompare);
