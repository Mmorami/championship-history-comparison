let leaderboardData = [];
let leaderboardSort = { key: "overall_score", dir: -1 }; // Default score descending
let customComparison = [];

// Normalization States
let leaderboardNorm = false;
let seasonNorm = false;
let comparisonNorm = false;

function getNormVal(val, pl, type) {
  if (!pl) return "0.0";
  if (type === 'pct') return (val / pl * 100).toFixed(1) + '%';
  if (type === 'pts_pct') return (val / (pl * 3) * 100).toFixed(1) + '%';
  if (type === 'rate') return (val / pl).toFixed(2);
  return val;
}

async function loadLeaderboard() {
  const res = await fetch("/api/leaderboard");
  const data = await res.json();
  const meta = document.getElementById("meta");
  meta.textContent = `Run: ${data.metadata.run_id || "n/a"} | Cutoff: ${data.metadata.data_cutoff_utc || "n/a"}`;

  leaderboardData = data.rows || [];
  renderLeaderboard();

  // Attach sorting listeners to headers
  const headers = document.querySelectorAll("#leaderboard thead th[data-key]");
  headers.forEach(th => {
    th.addEventListener("click", () => {
      const key = th.getAttribute("data-key");
      if (leaderboardSort.key === key) {
        leaderboardSort.dir *= -1;
      } else {
        leaderboardSort.key = key;
        leaderboardSort.dir = -1; // Default to DESC for most things
      }
      renderLeaderboard();
    });
  });
}

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

      if (key === "rank") {
        td.textContent = leaderboardData.indexOf(row) + 1;
      } else if (key === "goals_for") {
        if (leaderboardNorm) {
          td.textContent = `${(row.goals_for / row.played).toFixed(2)}-${(row.goals_against / row.played).toFixed(2)}`;
        } else {
          td.textContent = `${row.goals_for}-${row.goals_against}`;
        }
      } else if (leaderboardNorm && ["wins", "draws", "losses", "goal_diff", "points"].includes(key)) {
        if (key === "points") td.textContent = getNormVal(row[key], row.played, 'pts_pct');
        else if (key === "goal_diff") td.textContent = getNormVal(row[key], row.played, 'rate');
        else td.textContent = getNormVal(row[key], row.played, 'pct');
      } else {
        td.textContent = row[key] ?? "";
      }
      tr.appendChild(td);
    });
    tbody.appendChild(tr);
  });

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

function addToCustomComparison(teamData) {
  const exists = customComparison.some(c => c.season_id === teamData.season_id && c.team_id === teamData.team_id);
  if (exists) return;

  customComparison.push(teamData);
  renderCustomComparison();
}

function renderCustomComparison() {
  const tbody = document.querySelector("#custom-comparison tbody");
  tbody.innerHTML = "";

  document.getElementById("comparison-count").textContent = customComparison.length;

  customComparison.forEach((row, idx) => {
    const tr = document.createElement("tr");
    const pl = row.played;

    const display = (val, type) => comparisonNorm ? getNormVal(val, pl, type) : val;
    const goalsDisplay = comparisonNorm
      ? `${(row.goals_for / pl).toFixed(2)}-${(row.goals_against / pl).toFixed(2)}`
      : `${row.goals_for}-${row.goals_against}`;

    tr.innerHTML = `
      <td>${row.season_id}</td>
      <td>${row.team_name_canonical}</td>
      <td>${row.position}</td>
      <td>${pl}</td>
      <td>${display(row.wins, 'pct')}</td>
      <td>${display(row.draws, 'pct')}</td>
      <td>${display(row.losses, 'pct')}</td>
      <td>${goalsDisplay}</td>
      <td>${display(row.goal_diff, 'rate')}</td>
      <td>${display(row.points, 'pts_pct')}</td>
      <td><button class="danger-small" onclick="removeFromCustomComparison(${idx})">Remove</button></td>
    `;
    tbody.appendChild(tr);
  });
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
  const tbody = document.querySelector("#season-table tbody");
  const headers = Array.from(document.querySelectorAll("#season-table thead th"));
  tbody.innerHTML = "";

  data.rows.forEach((row) => {
    const tr = document.createElement("tr");
    tr.style.cursor = "pointer";
    tr.addEventListener("click", (e) => {
      if (e.target.tagName !== "BUTTON") loadTeamContext(row.team_id);
    });

    headers.forEach((th) => {
      const td = document.createElement("td");
      const text = th.textContent.toLowerCase();
      if (text === "add") {
        const btn = document.createElement("button");
        btn.textContent = "+";
        btn.className = "add-btn";
        btn.addEventListener("click", (e) => {
          e.stopPropagation();
          addToCustomComparison(row);
        });
        td.appendChild(btn);
      } else if (text === "+/-") {
        if (seasonNorm) {
          td.textContent = `${(row.goals_for / row.played).toFixed(2)}-${(row.goals_against / row.played).toFixed(2)}`;
        } else {
          td.textContent = `${row.goals_for}-${row.goals_against}`;
        }
      } else {
        const map = {
          pos: "position",
          team: "team_name_canonical",
          pl: "played",
          w: "wins",
          d: "draws",
          l: "losses",
          pts: "points",
          gd: "goal_diff",
        };
        const key = map[text] || text;
        let val = row[key] ?? "";

        if (seasonNorm && ["wins", "draws", "losses", "goal_diff", "points"].includes(key)) {
          if (key === "points") val = getNormVal(val, row.played, 'pts_pct');
          else if (key === "goal_diff") val = getNormVal(val, row.played, 'rate');
          else val = getNormVal(val, row.played, 'pct');
        }
        td.textContent = val;
      }
      tr.appendChild(td);
    });
    tbody.appendChild(tr);
  });
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

loadLeaderboard();
populateSeasonsDropdown().then(loadSeasonCompare);
