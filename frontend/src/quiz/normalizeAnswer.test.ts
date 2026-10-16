import assert from "node:assert/strict";
import test from "node:test";
import { normalizeAnswer } from "./normalizeAnswer.ts";

test("normalizes case and whitespace", () => {
  assert.equal(normalizeAnswer("  THE   NETHERLANDS  "), "the netherlands");
});

test("removes periods from abbreviations", () => {
  assert.equal(normalizeAnswer("U.S.A."), "usa");
});

test("folds diacritics and apostrophes", () => {
  assert.equal(normalizeAnswer("Côte d’Ivoire"), "cote divoire");
});

test("normalizes separators", () => {
  assert.equal(normalizeAnswer("Bosnia-Herzegovina"), "bosnia herzegovina");
});
