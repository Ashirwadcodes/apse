const API_BASE = "http://localhost:8000/api/v1";

// Runtime state — sources populated on init, technologies fetched on each search
let sourcesCache = [];

const state = {
  query: "",
  country: "",
  sector: "",
  source: "",
  language: "",
};

const els = {
  form: document.querySelector("#search-form"),
  input: document.querySelector("#search-input"),
  results: document.querySelector("#results-container"),
  title: document.querySelector("#results-title"),
  summary: document.querySelector("#results-summary"),
  country: document.querySelector("#country-filter"),
  sector: document.querySelector("#sector-filter"),
  source: document.querySelector("#source-filter"),
  language: document.querySelector("#language-filter"),
  clear: document.querySelector("#clear-filters"),
  sourceTable: document.querySelector("#sources-table"),
  filters: document.querySelector(".filters"),
};

// ── Helpers (unchanged) ──────────────────────────────────────────────────────

const statusClass = (status) => {
  if (status === "Metadata search") return "status-metadata";
  if (status === "Search redirect") return "status-redirect";
  return "status-listed";
};

const sourceInitials = (name) =>
  name
    .split(" ")
    .filter((word) => word.length > 3)
    .slice(0, 2)
    .map((word) => word[0])
    .join("");

function populateSelect(select, values, labelAccessor = (item) => item) {
  const options = values
    .map((item) => {
      const value = typeof item === "object" ? item.id : item;
      return `<option value="${value}">${labelAccessor(item)}</option>`;
    })
    .join("");
  select.insertAdjacentHTML("beforeend", options);
}

// ── Render functions (unchanged) ─────────────────────────────────────────────

function technologyCard(technology, source) {
  const techId = technology.id.replace("ntb_", "");
  const keywords = technology.keywords.slice(0, 6);

  const detailRows = [
    ["Organisation",      technology.org_name],
    ["Transfer type",     technology.transfer_type],
    ["Dev. status",       technology.dev_status],
    ["Sub-sector",        technology.sub_sector],
    ["Registered",        technology.reg_date],
    ["Tech ID",           techId],
  ]
    .filter(([, v]) => v)
    .map(([label, value]) => `
      <div class="detail-row">
        <span class="detail-label">${label}</span>
        <span class="detail-value detail-translatable">${value}</span>
      </div>`)
    .join("");

  return `
    <article class="technology-card" data-tech-id="${technology.id}">
      <span class="card-sector">${technology.sector}</span>
      <h4 class="card-title">${technology.title}</h4>
      <p class="card-summary">${technology.summary || "No summary available."}</p>
      ${keywords.length ? `
        <div class="card-keywords">
          ${keywords.map((k) => `<span class="keyword-tag">${k}</span>`).join("")}
        </div>` : ""}
      <div class="card-details">
        <span>${source.country}</span>
        <span>${technology.language}</span>
        <span>${source.name}</span>
      </div>
      <div class="card-detail-panel" hidden>
        ${detailRows}
      </div>
      <div class="card-actions">
        <button class="card-translate-btn" onclick="translateCard(this, '${technology.id}')">
          Translate to English
        </button>
        <button class="card-details-btn" onclick="toggleDetails(this, '${technology.id}')">
          Full record ↓
        </button>
      </div>
    </article>
  `;
}

function toggleDetails(btn, techId) {
  const card = document.querySelector(`[data-tech-id="${techId}"]`);
  const panel = card.querySelector(".card-detail-panel");
  const hidden = panel.hasAttribute("hidden");
  if (hidden) {
    panel.removeAttribute("hidden");
    btn.textContent = "Hide record ↑";
  } else {
    panel.setAttribute("hidden", "");
    btn.textContent = "Full record ↓";
  }
}

async function translateText(text) {
  if (!text || text.trim().length < 2) return text;
  const url = `https://api.mymemory.translated.net/get?q=${encodeURIComponent(text.slice(0, 500))}&langpair=ko|en`;
  const r = await fetch(url);
  const data = await r.json();
  return data.responseData?.translatedText || text;
}

async function translateCard(btn, techId) {
  const card = document.querySelector(`[data-tech-id="${techId}"]`);
  const titleEl = card.querySelector(".card-title");
  const summaryEl = card.querySelector(".card-summary");
  const tags = card.querySelectorAll(".keyword-tag");

  btn.textContent = "Translating…";
  btn.disabled = true;

  try {
    const [translatedTitle, translatedSummary] = await Promise.all([
      translateText(titleEl.textContent),
      translateText(summaryEl.textContent),
    ]);
    titleEl.textContent = translatedTitle;
    summaryEl.textContent = translatedSummary;

    // Translate keyword tags and detail values individually
    for (const tag of tags) {
      translateText(tag.textContent).then((t) => { tag.textContent = t; });
    }
    card.querySelectorAll(".detail-translatable").forEach((el) => {
      translateText(el.textContent).then((t) => { el.textContent = t; });
    });

    btn.textContent = "✓ Translated";
    card.classList.add("translated");
  } catch {
    btn.textContent = "Translation failed — retry";
    btn.disabled = false;
  }
}

function sourceGroup(source, results) {
  const isMetadata = source.status === "Metadata search";
  const countLabel = `${results.length} result${results.length === 1 ? "" : "s"}`;
  const content = isMetadata
    ? `<div class="technology-list">${results.map((item) => technologyCard(item, source)).join("")}</div>`
    : `
      <div class="redirect-card">
        <div>
          <h4>Continue your search on ${source.name}</h4>
          <p>Direct metadata is not yet available for this source.</p>
        </div>
        <a class="button button-secondary" href="${source.url}" target="_blank" rel="noopener noreferrer">
          Search this platform externally&nbsp; →
        </a>
      </div>
    `;

  return `
    <section class="source-group">
      <header class="group-header">
        <div class="group-source">
          <span class="source-initial" aria-hidden="true">${sourceInitials(source.name)}</span>
          <div>
            <h3>${source.name}</h3>
            <p>${source.country}</p>
          </div>
        </div>
        <div class="group-meta">
          <span class="result-count">${isMetadata ? countLabel : "External source"}</span>
          <span class="status ${statusClass(source.status)}">${source.status}</span>
        </div>
      </header>
      ${content}
    </section>
  `;
}

// ── API fetch layer ───────────────────────────────────────────────────────────

async function fetchSources() {
  const res = await fetch(`${API_BASE}/sources`);
  if (!res.ok) throw new Error("Sources fetch failed");
  return res.json();
}

async function fetchResults() {
  const params = new URLSearchParams();
  if (state.query)    params.set("q", state.query);
  if (state.country)  params.set("country", state.country);
  if (state.sector)   params.set("sector", state.sector);
  if (state.source)   params.set("source", state.source);
  if (state.language) params.set("language", state.language);
  const res = await fetch(`${API_BASE}/search?${params}`);
  if (!res.ok) throw new Error(`Search failed: ${res.status}`);
  return res.json();
}

// ── Rendering ─────────────────────────────────────────────────────────────────

async function renderResults() {
  els.title.textContent = state.query ? `Results for "${state.query}"` : "Technology search results";
  els.summary.textContent = "Searching across source platforms…";
  els.results.innerHTML = `<div class="empty-state"><p>Loading results…</p></div>`;

  let data;
  try {
    data = await fetchResults();
  } catch {
    els.results.innerHTML = `
      <div class="empty-state">
        <h3>Could not connect to the search service</h3>
        <p>Make sure the backend is running on port 8000.</p>
      </div>`;
    return;
  }

  const { results, total, sources_hit } = data;

  els.summary.textContent =
    `${total} technolog${total === 1 ? "y" : "ies"} across ` +
    `${sources_hit} source platform${sources_hit === 1 ? "" : "s"}.`;

  if (!results.length) {
    els.results.innerHTML = `
      <div class="empty-state">
        <h3>No matching technologies found</h3>
        <p>Try a broader keyword or clear one of the filters.</p>
      </div>`;
    return;
  }

  // Group by source_id, build a source-like object from the technology data
  const groups = {};
  results.forEach((tech) => {
    if (!groups[tech.source_id]) groups[tech.source_id] = [];
    groups[tech.source_id].push(tech);
  });

  const sourceMap = Object.fromEntries(sourcesCache.map((s) => [s.id, s]));

  els.results.innerHTML = Object.entries(groups)
    .map(([sourceId, techs]) => {
      const source = sourceMap[sourceId] || {
        id: sourceId,
        name: techs[0].source_name,
        country: techs[0].country,
        institution: "",
        status: "Metadata search",
        url: "#",
      };
      return sourceGroup(source, techs);
    })
    .join("");
}

async function renderSourcesTable() {
  try {
    const sources = await fetchSources();
    sourcesCache = sources;

    // Populate filter dropdowns
    const countries = [...new Set(sources.map((s) => s.country))].sort();
    populateSelect(els.country, countries);
    populateSelect(els.source, sources, (s) => s.name);

    els.sourceTable.innerHTML = sources
      .map(
        (source) => `
          <tr>
            <td>${source.name}</td>
            <td>${source.country}</td>
            <td>${source.institution}</td>
            <td><span class="status ${statusClass(source.status)}">${source.status}</span></td>
            <td>
              <a class="table-link" href="${source.url}" target="_blank" rel="noopener noreferrer">
                Visit source&nbsp; ↗
              </a>
            </td>
          </tr>
        `
      )
      .join("");
  } catch {
    els.sourceTable.innerHTML = `<tr><td colspan="5">Could not load sources.</td></tr>`;
  }
}

// ── Event listeners (unchanged) ───────────────────────────────────────────────

function runSearch(query) {
  state.query = query.trim();
  els.input.value = state.query;
  renderResults();
  document.querySelector("#search-results").scrollIntoView({ behavior: "smooth" });
}

els.form.addEventListener("submit", (event) => {
  event.preventDefault();
  runSearch(els.input.value);
});

document.querySelector("#popular-chips").addEventListener("click", (event) => {
  const chip = event.target.closest("[data-keyword]");
  if (chip) runSearch(chip.dataset.keyword);
});

[
  [els.country, "country"],
  [els.sector, "sector"],
  [els.source, "source"],
  [els.language, "language"],
].forEach(([select, key]) => {
  select.addEventListener("change", () => {
    state[key] = select.value;
    renderResults();
  });
});

els.clear.addEventListener("click", () => {
  Object.keys(state).forEach((key) => { state[key] = ""; });
  els.input.value = "";
  [els.country, els.sector, els.source, els.language].forEach((select) => {
    select.value = "";
  });
  renderResults();
});

document.querySelector(".mobile-filter-button").addEventListener("click", () => {
  els.filters.classList.add("open");
});

document.querySelector(".filter-close").addEventListener("click", () => {
  els.filters.classList.remove("open");
});

// ── Boot ─────────────────────────────────────────────────────────────────────

renderSourcesTable().then(() => renderResults());
