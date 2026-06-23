const API_BASE = "https://apsei-api.onrender.com/api/v1";

// Runtime state — sources populated on init, technologies fetched on each search
let sourcesCache = [];

const state = {
  query: "",
  country: "",
  sector: "",
  source: "",
  language: "",
  pages: {},   // { source_id: currentPage }
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

  const needsTranslation = technology.language === "Korean";

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
        ${needsTranslation ? `<button class="card-translate-btn" onclick="translateCard(this, '${technology.id}')">Translate to English</button>` : ""}
        <button class="card-details-btn" onclick="toggleDetails(this, '${technology.id}')">
          Full record ↓
        </button>
        ${technology.url ? `<a class="button button-secondary card-external-link" href="${technology.url}" target="_blank" rel="noopener noreferrer">${technology.source_id === "ip_australia" ? "Search patent ↗" : "View on source ↗"}</a>` : ""}
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

window.translateCard = translateCard;

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
  const info = REDIRECT_SOURCE_INFO[source.id];

  const currentPage = state.pages[source.id] || 1;
  const totalPages = isMetadata && totalCount ? Math.ceil(totalCount / 20) : 1;
  const countLabel = totalCount
    ? `Page ${currentPage} of ${totalPages.toLocaleString()} (${totalCount.toLocaleString()} total)`
    : `${results.length} result${results.length === 1 ? "" : "s"}`;

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

  const hasPrev = isMetadata && currentPage > 1;
  const hasNext = isMetadata && totalCount && currentPage < totalPages;

  function pageButtons(srcId, cur, total) {
    const btns = [];
    const add = (p, label, active, disabled) =>
      `<button class="pagination-page-btn${active ? " active" : ""}"
        ${disabled ? "disabled" : `onclick="changePage('${srcId}', ${p})"`}>${label}</button>`;

    btns.push(add(cur - 1, "←", false, cur === 1));

    // Always show first page
    btns.push(add(1, "1", cur === 1, false));
    if (cur > 4) btns.push(`<span class="pagination-ellipsis">…</span>`);

    // Pages around current
    const start = Math.max(2, cur - 2);
    const end = Math.min(total - 1, cur + 2);
    for (let p = start; p <= end; p++) btns.push(add(p, p, p === cur, false));

    if (cur < total - 3) btns.push(`<span class="pagination-ellipsis">…</span>`);

    // Always show last page if more than 1
    if (total > 1) btns.push(add(total, total, cur === total, false));

    btns.push(add(cur + 1, "→", false, cur === total));
    return btns.join("");
  }

  const pagination = (hasPrev || hasNext) ? `
    <div class="pagination-bar">
      ${pageButtons(source.id, currentPage, totalPages)}
    </div>` : "";

  return `
    <section class="source-group" data-source-id="${source.id}">
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
      ${pagination}
    </section>
  `;
}

// ── API fetch layer ───────────────────────────────────────────────────────────

async function fetchSources() {
  const res = await fetch(`${API_BASE}/sources`);
  if (!res.ok) throw new Error("Sources fetch failed");
  return res.json();
}

async function fetchResults(overrides = {}) {
  const params = new URLSearchParams();
  const page = overrides.page || 1;
  const src  = overrides.source !== undefined ? overrides.source : state.source;
  if (state.query)    params.set("q", state.query);
  if (state.country)  params.set("country", state.country);
  if (state.sector)   params.set("sector", state.sector);
  if (src)            params.set("source", src);
  if (state.language) params.set("language", state.language);
  if (page > 1)       params.set("page", page);
  const res = await fetch(`${API_BASE}/search?${params}`);
  if (!res.ok) throw new Error(`Search failed: ${res.status}`);
  return res.json();
}

// ── Rendering ─────────────────────────────────────────────────────────────────

function _renderGroups(results, source_totals, sourceMap, activeSourceFilter) {
  const groups = {};
  results.forEach((tech) => {
    if (!groups[tech.source_id]) groups[tech.source_id] = [];
    groups[tech.source_id].push(tech);
  });
  // Always show redirect sources
  sourcesCache.forEach((s) => {
    if (s.status === "Search redirect") {
      if (!activeSourceFilter || activeSourceFilter === s.id) {
        if (!groups[s.id]) groups[s.id] = [];
      }
    }
  });
  return Object.entries(groups).map(([sourceId, techs]) => {
    const source = sourceMap[sourceId] || {
      id: sourceId, name: techs[0]?.source_name || sourceId,
      country: techs[0]?.country || "", institution: "", status: "Metadata search", url: "#",
    };
    return sourceGroup(source, techs, source_totals[sourceId]);
  }).join("");
}

async function renderResults() {
  els.title.textContent = state.query ? `Results for "${state.query}"` : "Technology search results";
  els.summary.textContent = "Searching across source platforms…";
  els.results.innerHTML = `<div class="empty-state"><p>Loading results…</p></div>`;

  const sourceMap = Object.fromEntries(sourcesCache.map((s) => [s.id, s]));
  const activeSourceFilter = state.source;

  // NTB-only search runs as a separate slow-lane fetch
  const ntbActive = !activeSourceFilter || activeSourceFilter === "korea_ntb";
  const fastSource = activeSourceFilter === "korea_ntb" ? "" : activeSourceFilter;

  // Fast lane: everything except NTB (or the single non-NTB source selected)
  let fastData;
  try {
    fastData = activeSourceFilter === "korea_ntb"
      ? { results: [], total: 0, sources_hit: 0, source_totals: {} }
      : await fetchResults({ source: fastSource });
  } catch {
    els.results.innerHTML = `
      <div class="empty-state">
        <h3>Could not connect to the search service</h3>
        <p>The search service is temporarily unavailable. It may be starting up — please wait 30 seconds and refresh.</p>
      </div>`;
    return;
  }

  // Filter out any NTB results from fast lane (safety — shouldn't appear, but guard it)
  const fastResults = (fastData.results || []).filter(r => r.source_id !== "korea_ntb");
  const fastTotals  = Object.fromEntries(
    Object.entries(fastData.source_totals || {}).filter(([k]) => k !== "korea_ntb")
  );

  // Render fast results + NTB spinner immediately
  const fastHtml = _renderGroups(fastResults, fastTotals, sourceMap, activeSourceFilter);
  const ntbSpinner = ntbActive ? `
    <section class="source-group" data-source-id="korea_ntb">
      <header class="group-header">
        <div class="group-source">
          <span class="source-initial" aria-hidden="true">KN</span>
          <div><h3>Korea National Technology Bank</h3><p>Republic of Korea</p></div>
        </div>
        <div class="group-meta">
          <span class="result-count">Searching…</span>
          <span class="status status-metadata">Metadata search</span>
        </div>
      </header>
      <div class="ntb-spinner">Connecting to Korea NTB — may take up to 25 seconds.</div>
    </section>` : "";

  if (!fastHtml && !ntbActive) {
    els.results.innerHTML = `<div class="empty-state"><h3>No matching technologies found</h3><p>Try a broader keyword or clear one of the filters.</p></div>`;
    return;
  }

  els.results.innerHTML = fastHtml + ntbSpinner;
  els.summary.textContent =
    `${fastResults.length} technolog${fastResults.length === 1 ? "y" : "ies"} loaded` +
    (ntbActive ? " — Korea NTB loading…" : ".");

  // Slow lane: NTB (12–25s)
  if (ntbActive) {
    try {
      const ntbData = await fetchResults({ source: "korea_ntb" });
      const ntbResults = (ntbData.results || []).filter(r => r.source_id === "korea_ntb");
      const ntbTotal   = ntbData.source_totals?.korea_ntb || 0;
      const ntbSrc = sourceMap["korea_ntb"] || {
        id: "korea_ntb", name: "Korea National Technology Bank",
        country: "Republic of Korea", institution: "", status: "Metadata search", url: "https://www.ntb.kr",
      };
      const ntbHtml = ntbResults.length
        ? sourceGroup(ntbSrc, ntbResults, ntbTotal)
        : `<section class="source-group"><header class="group-header"><div class="group-source">
            <span class="source-initial">KN</span>
            <div><h3>Korea National Technology Bank</h3><p>Republic of Korea</p></div>
           </div><div class="group-meta"><span class="result-count">0 results</span>
           <span class="status status-metadata">Metadata search</span></div></header></section>`;
      const ntbSection = document.querySelector('[data-source-id="korea_ntb"]');
      if (ntbSection) ntbSection.outerHTML = ntbHtml;
      const total = fastResults.length + ntbResults.length;
      els.summary.textContent = `${total} technolog${total === 1 ? "y" : "ies"} across ${ntbResults.length ? "2" : "1"} source platform${ntbResults.length ? "s" : ""}.`;
    } catch {
      const ntbSection = document.querySelector('[data-source-id="korea_ntb"]');
      if (ntbSection) ntbSection.querySelector(".ntb-spinner").textContent = "Korea NTB unavailable — try again later.";
    }
  }
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
  csir_india: {
    flag: "🇮🇳",
    size: "1,739",
    sizeLabel: "technologies",
    description: "India's Council of Scientific and Industrial Research (CSIR) technology transfer portal — spanning 30+ national laboratories across agriculture, food, health, energy, materials, ICT, and manufacturing.",
    coverage: "India — technologies from CSIR institutes available for licensing, joint development, and commercialisation by domestic and international partners.",
    searchHint: "Search by technology name, application area, or CSIR institute. Each result links directly to the full technology profile.",
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
          onclick="openSourcePage('${source.id}')">
          View details
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

async function changePage(sourceId, page) {
  const section = document.querySelector(`[data-source-id="${sourceId}"]`);
  if (!section) return;

  section.querySelectorAll(".pagination-page-btn").forEach((b) => { b.disabled = true; });
  const activeBtn = section.querySelector(".pagination-page-btn.active");
  if (activeBtn) activeBtn.textContent = sourceId === "korea_ntb" ? "Connecting…" : "…";
  section.querySelector(".technology-list")?.classList.add("page-loading");

  state.pages[sourceId] = page;

  try {
    const data = await fetchResults({ source: sourceId, page });
    const sourceMap = Object.fromEntries(sourcesCache.map((s) => [s.id, s]));
    const source = sourceMap[sourceId];
    const results = (data.results || []).filter((r) => r.source_id === sourceId);
    const total = data.source_totals?.[sourceId] || 0;
    const newHtml = sourceGroup(source, results, total);
    section.outerHTML = newHtml;
    setTimeout(() => {
      document.querySelector(`[data-source-id="${sourceId}"]`)?.scrollIntoView({ behavior: "smooth", block: "start" });
    }, 0);
  } catch {
    section.querySelector(".technology-list")?.classList.remove("page-loading");
    section.querySelectorAll(".pagination-page-btn").forEach((b) => { b.disabled = false; });
    const label = section.querySelector(".pagination-page-btn.active");
    if (label) label.textContent = "Failed — retry";
  }
}

window.changePage = changePage;

function runSearch(query) {
  state.query = query.trim();
  state.pages = {};  // reset pagination on new search
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
    state.pages = {};
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

// ── Source detail page (hash routing) ────────────────────────────────────────

const sourcePage = document.querySelector("#source-page");
const sourcePageContent = document.querySelector("#source-page-content");

function openSourcePage(sourceId) {
  const source = sourcesCache.find((s) => s.id === sourceId);
  if (!source) return;
  const detail = SOURCE_DETAIL[sourceId] || {};
  sourcePageContent.innerHTML = `
    <div class="sp-back">
      <button class="text-button" onclick="closeSourcePage()">← Back to Gateway</button>
    </div>
    <div class="sp-hero">
      <span class="source-initial sp-initial" aria-hidden="true">${sourceInitials(source.name)}</span>
      <div>
        <span class="status ${statusClass(source.status)}">${source.status}</span>
        <h2 class="sp-name">${source.name}</h2>
        <p class="sp-country">${detail.flag || ""} ${source.country} · ${source.institution}</p>
      </div>
    </div>
    ${detail.size ? `<div class="sp-stat-row">
      <div class="sp-stat"><span class="sdc-stat-number">${detail.size}</span><span class="sdc-stat-label">${detail.sizeLabel}</span></div>
    </div>` : ""}
    <p class="sp-desc">${detail.description || ""}</p>
    <div class="sp-section">
      <h3>Coverage</h3>
      <p>${detail.coverage || source.country}</p>
    </div>
    ${detail.searchHint ? `<div class="sp-section sp-hint-box">
      <h3>Search tip</h3>
      <p>${detail.searchHint}</p>
    </div>` : ""}
    <div class="sp-actions">
      <button class="button button-primary" onclick="closeSourcePage(); state.source='${source.id}'; document.querySelector('#source-filter').value='${source.id}'; runSearch(state.query || ''); ">
        Search ${source.name}
      </button>
      <a class="button button-secondary" href="${source.url}" target="_blank" rel="noopener noreferrer">
        Visit official site ↗
      </a>
    </div>
  `;
  sourcePage.classList.add("open");
  history.pushState({ sourceId }, "", `#source/${sourceId}`);
}

function closeSourcePage() {
  sourcePage.classList.remove("open");
  history.pushState({}, "", "#sources");
}

window.openSourcePage = openSourcePage;
window.closeSourcePage = closeSourcePage;

window.addEventListener("popstate", (e) => {
  if (e.state?.sourceId) {
    openSourcePage(e.state.sourceId);
  } else {
    sourcePage.classList.remove("open");
  }
});

// ── Boot ─────────────────────────────────────────────────────────────────────

renderSourcesTable().then(() => {
  renderResults();
  // Check if URL has a source hash on load
  const match = location.hash.match(/^#source\/(.+)$/);
  if (match) openSourcePage(match[1]);
});
