const API_BASE = "https://apsei-api.onrender.com/api/v1";

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
        ${technology.url ? `<a class="button button-secondary card-external-link" href="${technology.url}" target="_blank" rel="noopener noreferrer">View on source ↗</a>` : ""}
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

const REDIRECT_SOURCE_INFO = {
  wipo_patentscope: {
    size: "128M+ patents",
    coverage: "International patent applications from 150+ countries via the PCT system.",
    cards: [
      {
        title: "International Patent Applications (PCT)",
        sector: "Patents",
        org: "World Intellectual Property Organization",
        country: "International",
        description: "Search PCT applications and national patents across Asia-Pacific member states including Japan, Korea, China, India, Australia, and 145+ other countries.",
      },
      {
        title: "Asia-Pacific Technology Filings",
        sector: "Patents — AP Region",
        org: "WIPO PATENTSCOPE",
        country: "Asia-Pacific",
        description: "Filter by Asia-Pacific offices (JP, KR, CN, IN, AU, SG, TH, VN and more) to find regionally relevant technology filings.",
      },
    ],
  },
};

function buildRedirectUrl(source, query) {
  const q = encodeURIComponent(query || "");
  if (source.id === "wipo_patentscope" && q) {
    return `https://patentscope.wipo.int/search/en/result.jsf?query=${q}`;
  }
  return source.url;
}

function sourceGroup(source, results, totalCount) {
  const isMetadata = source.status === "Metadata search";
  const fetchedLabel = `${results.length} result${results.length === 1 ? "" : "s"}`;
  const countLabel = totalCount && totalCount > results.length
    ? `${results.length} of ${totalCount.toLocaleString()}`
    : fetchedLabel;
  const info = REDIRECT_SOURCE_INFO[source.id];
  const content = isMetadata
    ? `<div class="technology-list">${results.map((item) => technologyCard(item, source)).join("")}</div>`
    : `<div class="technology-list">
        ${info ? info.cards.map((card) => `
          <article class="technology-card external-card">
            <span class="card-sector">${card.sector}</span>
            <h4 class="card-title">${card.title}</h4>
            <p class="card-summary">${card.description}</p>
            <div class="card-details">
              <span>${card.country}</span>
              <span>${card.org}</span>
            </div>
            <div class="card-actions">
              <a class="button button-secondary card-external-link"
                 href="${buildRedirectUrl(source, state.query)}"
                 target="_blank" rel="noopener noreferrer">
                Search on ${source.name}&nbsp; →
              </a>
            </div>
          </article>`).join("") : ""}
      </div>`;

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
          <span class="result-count">${isMetadata ? countLabel : (info ? info.size : "External source")}</span>
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
        <p>The search service is temporarily unavailable. It may be starting up — please wait 30 seconds and refresh.</p>
      </div>`;
    return;
  }

  const { results, total, sources_hit, source_totals = {} } = data;

  els.summary.textContent =
    `${total} technolog${total === 1 ? "y" : "ies"} across ` +
    `${sources_hit} source platform${sources_hit === 1 ? "" : "s"}.`;

  // Group metadata results by source_id
  const groups = {};
  results.forEach((tech) => {
    if (!groups[tech.source_id]) groups[tech.source_id] = [];
    groups[tech.source_id].push(tech);
  });

  const sourceMap = Object.fromEntries(sourcesCache.map((s) => [s.id, s]));

  // Always include redirect sources so their cards appear even with zero metadata results
  const activeSourceFilter = state.source;
  sourcesCache.forEach((s) => {
    if (s.status === "Search redirect") {
      if (!activeSourceFilter || activeSourceFilter === s.id) {
        if (!groups[s.id]) groups[s.id] = [];
      }
    }
  });

  if (!Object.keys(groups).length) {
    els.results.innerHTML = `
      <div class="empty-state">
        <h3>No matching technologies found</h3>
        <p>Try a broader keyword or clear one of the filters.</p>
      </div>`;
    return;
  }

  els.results.innerHTML = Object.entries(groups)
    .map(([sourceId, techs]) => {
      const source = sourceMap[sourceId] || {
        id: sourceId,
        name: techs[0]?.source_name || sourceId,
        country: techs[0]?.country || "",
        institution: "",
        status: "Metadata search",
        url: "#",
      };
      return sourceGroup(source, techs, source_totals[sourceId]);
    })
    .join("");
}

// Rich detail info per source — shown on the source cards page
const SOURCE_DETAIL = {
  korea_ntb: {
    flag: "🇰🇷",
    size: "128,000+",
    sizeLabel: "technologies",
    description: "Korea's national repository for technology transfer offers from universities, research institutes, and public R&D institutions. Technologies span manufacturing, ICT, biotech, energy, and more.",
    coverage: "Republic of Korea — domestic technologies available for licensing, joint development, or transfer to domestic and international partners.",
    searchHint: "Search in English — queries are automatically translated to Korean.",
  },
  wipo_patentscope: {
    flag: "🌏",
    size: "128M+",
    sizeLabel: "patents",
    description: "WIPO PATENTSCOPE provides access to international patent applications filed via the PCT system, as well as national patent collections from 50+ offices.",
    coverage: "Global — includes Asia-Pacific offices: JP, KR, CN, IN, AU, SG, TH, VN, PH, MY, ID, NZ and 140+ other countries.",
    searchHint: "Clicking 'Search on WIPO' will open PATENTSCOPE with your query pre-filled.",
  },
  ip_australia: {
    flag: "🇦🇺",
    size: "6,000+",
    sizeLabel: "patents (test DB)",
    description: "Australian patent applications and grants searched via the IP Australia Patent Search API. Covers innovation patents, standard patents, and PCT national phase entries.",
    coverage: "Australia — all patent applications lodged with IP Australia, including PCT applications entering the national phase.",
    searchHint: "Results link directly to the Australian Patent Search portal for full specifications.",
  },
};

function sourceDetailCard(source) {
  const detail = SOURCE_DETAIL[source.id] || {};
  const initials = sourceInitials(source.name);
  return `
    <article class="source-detail-card" id="source-${source.id}">
      <div class="sdc-header">
        <div class="sdc-identity">
          <span class="source-initial sdc-initial" aria-hidden="true">${initials}</span>
          <div>
            <h3 class="sdc-name">${source.name}</h3>
            <p class="sdc-country">${detail.flag || ""} ${source.country}</p>
          </div>
        </div>
        <span class="status ${statusClass(source.status)}">${source.status}</span>
      </div>

      ${detail.size ? `
      <div class="sdc-stat">
        <span class="sdc-stat-number">${detail.size}</span>
        <span class="sdc-stat-label">${detail.sizeLabel}</span>
      </div>` : ""}

      <p class="sdc-description">${detail.description || ""}</p>

      <div class="sdc-meta">
        <div class="sdc-meta-row">
          <span class="sdc-meta-label">Institution</span>
          <span class="sdc-meta-value">${source.institution}</span>
        </div>
        <div class="sdc-meta-row">
          <span class="sdc-meta-label">Coverage</span>
          <span class="sdc-meta-value">${detail.coverage || source.country}</span>
        </div>
        ${detail.searchHint ? `
        <div class="sdc-meta-row">
          <span class="sdc-meta-label">Search tip</span>
          <span class="sdc-meta-value sdc-hint">${detail.searchHint}</span>
        </div>` : ""}
      </div>

      <div class="sdc-actions">
        <button class="button button-primary sdc-search-btn"
          onclick="runSearch(''); document.querySelector('#search-results').scrollIntoView({behavior:'smooth'}); document.querySelector('#source-filter').value='${source.id}'; state.source='${source.id}'; renderResults();">
          Search this source
        </button>
        <a class="button button-secondary" href="${source.url}" target="_blank" rel="noopener noreferrer">
          Visit source ↗
        </a>
      </div>
    </article>
  `;
}

async function renderSourcesTable() {
  const grid = document.querySelector("#source-cards-grid");
  const badge = document.querySelector("#source-count-badge strong");
  try {
    const sources = await fetchSources();
    sourcesCache = sources;

    // Populate filter dropdowns
    const countries = [...new Set(sources.map((s) => s.country))].sort();
    populateSelect(els.country, countries);
    populateSelect(els.source, sources, (s) => s.name);

    if (badge) badge.textContent = sources.length;
    if (grid) grid.innerHTML = sources.map(sourceDetailCard).join("");
  } catch {
    if (grid) grid.innerHTML = `<p>Could not load sources.</p>`;
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
