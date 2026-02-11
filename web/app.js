const defaultConfig = {
  concrete_keywords: ["concrete", "pour"],
  max_major_pours_per_day: 1,
  min_duration_by_keyword: { concrete: 3, commissioning: 5 },
  min_lead_time_days: { steel: 14, switchgear: 45 },
};

const sampleCsv = `task_id,name,start_date,finish_date,duration_days,resource,discipline,location,predecessors
A100,Procure structural steel,2026-03-01,2026-03-05,5,Procurement,Structural,Zone A,
A110,Erect steel framing,2026-03-08,2026-03-10,2,Steel Crew,Structural,Zone A,A100
B200,Main slab concrete pour,2026-04-12,2026-04-12,1,Concrete Crew,Civil,Zone B,
B210,Podium concrete pour,2026-04-12,2026-04-12,1,Concrete Crew,Civil,Zone B,
C300,Switchgear installation,2026-05-10,2026-05-11,2,Electrical,MEP,Plantroom,A110`;

const csvInput = document.getElementById("csvInput");
const configInput = document.getElementById("configInput");
const csvFile = document.getElementById("csvFile");
const findingsBody = document.getElementById("findingsBody");
const findingsTable = document.getElementById("findingsTable");
const summary = document.getElementById("summary");

configInput.value = JSON.stringify(defaultConfig, null, 2);

csvFile.addEventListener("change", async (evt) => {
  const [file] = evt.target.files;
  if (!file) return;
  csvInput.value = await file.text();
});

document.getElementById("loadSampleBtn").addEventListener("click", () => {
  csvInput.value = sampleCsv;
  configInput.value = JSON.stringify(defaultConfig, null, 2);
});

document.getElementById("analyzeBtn").addEventListener("click", () => {
  try {
    const tasks = parseCsv(csvInput.value);
    const config = parseConfig(configInput.value);
    const findings = reviewSchedule(tasks, config);
    renderFindings(findings);
  } catch (error) {
    summary.textContent = `Error: ${error.message}`;
    findingsTable.hidden = true;
  }
});

function parseCsv(text) {
  const lines = text.trim().split(/\r?\n/).filter(Boolean);
  if (!lines.length) {
    throw new Error("Please provide CSV input.");
  }

  const headers = lines[0].split(",").map((h) => h.trim());
  const rows = lines.slice(1).map((line) => splitCsvLine(line));

  return rows.map((values) => {
    const row = Object.fromEntries(headers.map((h, i) => [h, (values[i] || "").trim()]));
    return {
      task_id: row.task_id,
      name: row.name,
      start_date: new Date(`${row.start_date}T00:00:00`),
      finish_date: new Date(`${row.finish_date}T00:00:00`),
      duration_days: Number(row.duration_days || 0),
      location: row.location || "",
      predecessors: (row.predecessors || "")
        .split(";")
        .map((s) => s.trim())
        .filter(Boolean),
    };
  });
}

function splitCsvLine(line) {
  const out = [];
  let current = "";
  let inQuotes = false;

  for (let i = 0; i < line.length; i += 1) {
    const ch = line[i];
    if (ch === '"') {
      inQuotes = !inQuotes;
      continue;
    }
    if (ch === "," && !inQuotes) {
      out.push(current);
      current = "";
      continue;
    }
    current += ch;
  }
  out.push(current);
  return out;
}

function parseConfig(text) {
  if (!text.trim()) return { ...defaultConfig };
  const cfg = JSON.parse(text);
  return {
    concrete_keywords: cfg.concrete_keywords || defaultConfig.concrete_keywords,
    max_major_pours_per_day: Number(cfg.max_major_pours_per_day || 1),
    min_duration_by_keyword: cfg.min_duration_by_keyword || {},
    min_lead_time_days: cfg.min_lead_time_days || {},
  };
}

function reviewSchedule(tasks, config) {
  return [
    ...checkOverlappingConcretePours(tasks, config),
    ...checkUnrealisticDurations(tasks, config),
    ...checkLeadTimeConstraints(tasks, config),
  ].sort((a, b) => rank(a.severity) - rank(b.severity));
}

function checkOverlappingConcretePours(tasks, config) {
  const dayMap = new Map();
  const terms = (config.concrete_keywords || []).map((s) => s.toLowerCase());

  tasks.forEach((task) => {
    const isConcrete = terms.some((term) => task.name.toLowerCase().includes(term));
    if (!isConcrete) return;

    const day = task.start_date.toISOString().slice(0, 10);
    const key = `${day}__${task.location.toLowerCase()}`;
    const existing = dayMap.get(key) || [];
    existing.push(task);
    dayMap.set(key, existing);
  });

  const findings = [];
  dayMap.forEach((dayTasks, key) => {
    if (dayTasks.length > config.max_major_pours_per_day) {
      const [day, location] = key.split("__");
      findings.push({
        code: "LOGIC_CONCRETE_OVERLAP",
        severity: "high",
        task_ids: dayTasks.map((t) => t.task_id),
        message: `${dayTasks.length} concrete pours are scheduled on ${day} at ${location || "unspecified location"}; limit is ${config.max_major_pours_per_day}.`,
      });
    }
  });

  return findings;
}

function checkUnrealisticDurations(tasks, config) {
  const thresholds = config.min_duration_by_keyword || {};
  const findings = [];

  tasks.forEach((task) => {
    Object.entries(thresholds).forEach(([keyword, minimum]) => {
      if (task.name.toLowerCase().includes(keyword.toLowerCase()) && task.duration_days < Number(minimum)) {
        findings.push({
          code: "DURATION_UNREALISTIC",
          severity: "medium",
          task_ids: [task.task_id],
          message: `Task '${task.name}' has duration ${task.duration_days} days, below configured minimum of ${Number(minimum)} for keyword '${keyword}'.`,
        });
      }
    });
  });

  return findings;
}

function checkLeadTimeConstraints(tasks, config) {
  const rules = config.min_lead_time_days || {};
  const byId = Object.fromEntries(tasks.map((t) => [t.task_id, t]));
  const findings = [];

  tasks.forEach((task) => {
    Object.entries(rules).forEach(([keyword, minDays]) => {
      if (!task.name.toLowerCase().includes(keyword.toLowerCase())) return;

      const predecessorFinishes = task.predecessors
        .map((id) => byId[id])
        .filter(Boolean)
        .map((pred) => pred.finish_date.getTime());

      if (!predecessorFinishes.length) {
        findings.push({
          code: "LEAD_TIME_MISSING_PREDECESSOR",
          severity: "medium",
          task_ids: [task.task_id],
          message: `Task '${task.name}' requires lead-time rule '${keyword}' but has no valid predecessor to measure from.`,
        });
        return;
      }

      const latestFinish = Math.max(...predecessorFinishes);
      const actualGap = Math.round((task.start_date.getTime() - latestFinish) / (1000 * 60 * 60 * 24));
      if (actualGap < Number(minDays)) {
        findings.push({
          code: "LEAD_TIME_TOO_SHORT",
          severity: "high",
          task_ids: [task.task_id],
          message: `Task '${task.name}' has only ${actualGap} days from predecessor finish to start; requires at least ${Number(minDays)} days for '${keyword}'.`,
        });
      }
    });
  });

  return findings;
}

function rank(severity) {
  if (severity === "high") return 0;
  if (severity === "medium") return 1;
  return 2;
}

function renderFindings(findings) {
  findingsBody.innerHTML = "";
  if (!findings.length) {
    summary.textContent = "No findings. Schedule passed configured checks.";
    findingsTable.hidden = true;
    return;
  }

  summary.textContent = `${findings.length} finding(s) detected.`;
  findingsTable.hidden = false;

  findings.forEach((finding) => {
    const tr = document.createElement("tr");
    tr.innerHTML = `
      <td><span class="badge ${finding.severity}">${finding.severity.toUpperCase()}</span></td>
      <td>${escapeHtml(finding.code)}</td>
      <td>${escapeHtml((finding.task_ids || []).join(", "))}</td>
      <td>${escapeHtml(finding.message)}</td>
    `;
    findingsBody.appendChild(tr);
  });
}

function escapeHtml(value) {
  return String(value)
    .replaceAll("&", "&amp;")
    .replaceAll("<", "&lt;")
    .replaceAll(">", "&gt;")
    .replaceAll('"', "&quot;")
    .replaceAll("'", "&#039;");
}
