const test = require("node:test");
const assert = require("node:assert/strict");

const compare = require("../frontend/compare-utils.js");

function technology(overrides = {}) {
  return {
    id: "technology-1",
    sourceId: "source-a",
    sourceName: "Source A",
    title: "Solar cold storage",
    summary: "Off-grid cooling for agricultural supply chains.",
    country: "India",
    sectors: "Energy and heat transfer engineering",
    organisation: "Example institute",
    recordDate: "2026-08-01",
    lastIndexed: "2026-08-10",
    language: "English",
    url: "https://example.org/technology-1",
    linkLabel: "View original source ↗",
    ...overrides,
  };
}

test("normalizes a comparison item and strips unsafe URLs", () => {
  const item = compare.normalizeItem(technology({
    title: "  Solar\n  cold storage  ",
    url: "javascript:alert(1)",
  }));

  assert.equal(item.title, "Solar cold storage");
  assert.equal(item.url, "");
  assert.equal(compare.itemKey(item), "source-a:technology-1");
});

test("adds and removes an item using its source-qualified identifier", () => {
  const first = compare.toggleItem([], technology());
  assert.equal(first.status, "added");
  assert.equal(first.items.length, 1);

  const secondSource = compare.toggleItem(first.items, technology({ sourceId: "source-b" }));
  assert.equal(secondSource.status, "added");
  assert.equal(secondSource.items.length, 2);

  const removed = compare.toggleItem(secondSource.items, technology());
  assert.equal(removed.status, "removed");
  assert.deepEqual(removed.items.map(compare.itemKey), ["source-b:technology-1"]);
});

test("enforces the three-item comparison limit", () => {
  const items = [1, 2, 3].map((id) => technology({ id: `technology-${id}` }));
  const result = compare.toggleItem(items, technology({ id: "technology-4" }));

  assert.equal(result.status, "limit");
  assert.equal(result.items.length, compare.LIMIT);
});

test("restores only valid, unique items from browser storage", () => {
  const storage = {
    getItem(key) {
      assert.equal(key, compare.STORAGE_KEY);
      return JSON.stringify([
        technology(),
        technology(),
        technology({ id: "" }),
        technology({ id: "technology-2" }),
      ]);
    },
  };

  assert.deepEqual(
    compare.readItems(storage).map(compare.itemKey),
    ["source-a:technology-1", "source-a:technology-2"]
  );
});

test("writes a sanitized comparison snapshot without exceeding the limit", () => {
  let stored = "";
  const storage = {
    setItem(key, value) {
      assert.equal(key, compare.STORAGE_KEY);
      stored = value;
    },
  };
  const items = [1, 2, 3, 4].map((id) => technology({ id: `technology-${id}` }));
  const normalized = compare.writeItems(storage, items);

  assert.equal(normalized.length, 3);
  assert.equal(JSON.parse(stored).length, 3);
});
