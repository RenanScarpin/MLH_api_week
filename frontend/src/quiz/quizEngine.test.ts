import assert from "node:assert/strict";
import test from "node:test";
import type { QuizSnapshot } from "../types/snapshot.ts";
import { createSession, getHighlightedTargetIds, submitTextAnswer } from "./quizEngine.ts";

const quiz: QuizSnapshot = {
  id: "test",
  title: "Test",
  scope: { kind: "continent", id: "europe", mapId: "europe" },
  subjectKind: "sovereign_state",
  promptKind: "head_of_state",
  interactionKind: "text",
  progressionKind: "sequential",
  completionRule: "all_subjects",
  subjects: [
    {
      id: "Q142",
      entityQid: "Q142",
      sovereignQid: "Q142",
      displayName: "France",
      acceptedAnswers: ["france", "fra"],
      mapTargetIds: ["france"],
      prompt: { kind: "head_of_state", heads: [] },
    },
    {
      id: "Q183",
      entityQid: "Q183",
      sovereignQid: "Q183",
      displayName: "Germany",
      acceptedAnswers: ["germany", "deu"],
      mapTargetIds: ["germany"],
      prompt: { kind: "head_of_state", heads: [] },
    },
  ],
};

test("sequential answer checking only accepts current subject", () => {
  const session = createSession(quiz, "s1", {
    random: () => 0.999,
    startedAt: "2026-01-01T00:00:00Z",
  });

  const wrong = submitTextAnswer(quiz, session, "Germany");
  assert.equal(wrong.outcome, "incorrect");
  assert.equal(wrong.session.wrongAttempts, 1);

  const correct = submitTextAnswer(quiz, session, "FRA");
  assert.equal(correct.outcome, "correct");
  assert.deepEqual(correct.session.solvedSubjectIds, ["Q142"]);
  assert.deepEqual([...getHighlightedTargetIds(quiz, correct.session)], ["france"]);
});

test("completes after all sequential subjects", () => {
  let session = createSession(quiz, "s1", {
    random: () => 0.999,
    startedAt: "2026-01-01T00:00:00Z",
  });
  session = submitTextAnswer(quiz, session, "France").session;
  const result = submitTextAnswer(quiz, session, "DEU", "2026-01-01T00:01:00Z");

  assert.equal(result.session.status, "completed");
  assert.equal(result.session.completedAt, "2026-01-01T00:01:00Z");
});
