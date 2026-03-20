let leaderboardData = [];
let leaderboardSort = { key: "overall_score", dir: -1 }; // Default score descending
let customComparison = [];

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
      } else if (key === "ppg") {
        td.textContent = Number(row[key] || 0).toFixed(3);
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

  customComparison.forEach((row, idx) => {
    const tr = document.createElement("tr");
    tr.innerHTML = `
      <td>${row.season_id}</td>
      <td>${row.team_name_canonical}</td>
      <td>${row.position}</td>
      <td>${row.played}</td>
      <td>${row.wins}</td>
      <td>${row.draws}</td>
      <td>${row.losses}</td>
      <td>${row.points}</td>
      <td>${row.goals_for}</td>
      <td>${row.goals_against}</td>
      <td>${row.goal_diff}</td>
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

  const managersDiv = document.getElementById("context-managers");
  const scorersDiv = document.getElementById("context-scorers");
  const hint = document.getElementById("context-hint");
  if (hint) hint.style.display = "none";

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
      } else {
        const map = {
          pos: "position",
          team: "team_name_canonical",
          p: "played",
          w: "wins",
          d: "draws",
          l: "losses",
          pts: "points",
          gf: "goals_for",
          ga: "goals_against",
          gd: "goal_diff",
        };
        const key = map[text] || text;
        td.textContent = row[key] ?? "";
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

loadLeaderboard();
populateSeasonsDropdown().then(loadSeasonCompare);
