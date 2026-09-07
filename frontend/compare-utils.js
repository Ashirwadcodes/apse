(function initAptgCompare(root, factory) {
  "use strict";

  const api = factory();
  root.AptgCompare = api;
  if (typeof module !== "undefined" && module.exports) {
    module.exports = api;
  }
})(typeof globalThis !== "undefined" ? globalThis : window, function createAptgCompare() {
  "use strict";

  const STORAGE_KEY = "aptg_compare_v1";
  const LIMIT = 3;

  function cleanText(value, maxLength = 1200) {
    return String(value ?? "")
      .replace(/[\u0000-\u001f\u007f]/g, " ")
      .replace(/\s+/g, " ")
      .trim()
      .slice(0, maxLength);
  }

  function safeHttpUrl(value) {
    const raw = cleanText(value, 2000);
    if (!raw) return "";
    try {
      const parsed = new URL(raw);
      if (!["http:", "https:"].includes(parsed.protocol)) return "";
      if (parsed.username || parsed.password) return "";
      return parsed.href;
    } catch {
      return "";
    }
  }

  function itemKey(item) {
    const sourceId = cleanText(item?.sourceId, 100);
    const id = cleanText(item?.id, 240);
    return sourceId && id ? `${sourceId}:${id}` : "";
  }

  function normalizeItem(raw) {
    if (!raw || typeof raw !== "object") return null;
    const item = {
      id: cleanText(raw.id, 240),
      sourceId: cleanText(raw.sourceId, 100),
      sourceName: cleanText(raw.sourceName, 180),
      title: cleanText(raw.title, 500),
      summary: cleanText(raw.summary, 1800),
      country: cleanText(raw.country, 120),
      sectors: cleanText(raw.sectors, 700),
      organisation: cleanText(raw.organisation, 500),
      recordDate: cleanText(raw.recordDate, 100),
      lastIndexed: cleanText(raw.lastIndexed, 100),
      language: cleanText(raw.language, 80),
      url: safeHttpUrl(raw.url),
      linkLabel: cleanText(raw.linkLabel, 100),
    };
    if (!item.id || !item.sourceId || !item.title) return null;
    return item;
  }

  function normalizeItems(items, limit = LIMIT) {
    const normalized = [];
    const keys = new Set();
    for (const raw of Array.isArray(items) ? items : []) {
      const item = normalizeItem(raw);
      const key = itemKey(item);
      if (!item || !key || keys.has(key)) continue;
      keys.add(key);
      normalized.push(item);
      if (normalized.length >= limit) break;
    }
    return normalized;
  }

  function readItems(storage, limit = LIMIT) {
    if (!storage || typeof storage.getItem !== "function") return [];
    try {
      return normalizeItems(JSON.parse(storage.getItem(STORAGE_KEY) || "[]"), limit);
    } catch {
      return [];
    }
  }

  function writeItems(storage, items, limit = LIMIT) {
    const normalized = normalizeItems(items, limit);
    if (!storage || typeof storage.setItem !== "function") return normalized;
    try {
      storage.setItem(STORAGE_KEY, JSON.stringify(normalized));
    } catch {
      // Comparison still works for the current page when browser storage is blocked.
    }
    return normalized;
  }

  function toggleItem(items, rawItem, limit = LIMIT) {
    const current = normalizeItems(items, limit);
    const item = normalizeItem(rawItem);
    const key = itemKey(item);
    if (!item || !key) return { items: current, status: "invalid" };

    const existingIndex = current.findIndex((candidate) => itemKey(candidate) === key);
    if (existingIndex >= 0) {
      return {
        items: current.filter((_, index) => index !== existingIndex),
        status: "removed",
      };
    }
    if (current.length >= limit) return { items: current, status: "limit" };
    return { items: [...current, item], status: "added" };
  }

  return Object.freeze({
    STORAGE_KEY,
    LIMIT,
    cleanText,
    itemKey,
    normalizeItem,
    normalizeItems,
    readItems,
    safeHttpUrl,
    toggleItem,
    writeItems,
  });
});
