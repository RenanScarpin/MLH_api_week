import type { QuizSnapshot, QuizSubject } from "../types/snapshot.ts";
import { normalizeAnswer } from "./normalizeAnswer.ts";

export type QuizSessionStatus = "active" | "completed";

export interface QuizSessionState {
  quizId: string;
  snapshotId: string;
  startedAt: string;
  completedAt: string | null;
  status: QuizSessionStatus;
  subjectOrder: string[];
  currentPosition: number;
  solvedSubjectIds: string[];
  correctAnswers: number;
  wrongAttempts: number;
}

export type SubmitOutcome = "correct" | "incorrect" | "completed";

export interface SubmitAnswerResult {
  outcome: SubmitOutcome;
  matchedSubjectIds: string[];
  session: QuizSessionState;
}

function shuffled<T>(values: readonly T[], random: () => number): T[] {
  const result = [...values];
  for (let i = result.length - 1; i > 0; i -= 1) {
    const j = Math.floor(random() * (i + 1));
    [result[i], result[j]] = [result[j], result[i]];
  }
  return result;
}

export function createSession(
  quiz: QuizSnapshot,
  snapshotId: string,
  options: { random?: () => number; startedAt?: string } = {},
): QuizSessionState {
  const random = options.random ?? Math.random;
  const startedAt = options.startedAt ?? new Date().toISOString();
  const subjectIds = quiz.subjects.map((subject) => subject.id);
  const subjectOrder =
    quiz.progressionKind === "sequential"
      ? shuffled(subjectIds, random)
      : subjectIds;

  return {
    quizId: quiz.id,
    snapshotId,
    startedAt,
    completedAt: subjectOrder.length === 0 ? startedAt : null,
    status: subjectOrder.length === 0 ? "completed" : "active",
    subjectOrder,
    currentPosition: 0,
    solvedSubjectIds: [],
    correctAnswers: 0,
    wrongAttempts: 0,
  };
}

export function getCurrentSubject(
  quiz: QuizSnapshot,
  session: QuizSessionState,
): QuizSubject | null {
  if (session.status === "completed") {
    return null;
  }

  const subjectId = session.subjectOrder[session.currentPosition];
  return quiz.subjects.find((subject) => subject.id === subjectId) ?? null;
}

export function getHighlightedTargetIds(
  quiz: QuizSnapshot,
  session: QuizSessionState,
): Set<string> {
  const solved = new Set(session.solvedSubjectIds);
  return new Set(
    quiz.subjects
      .filter((subject) => solved.has(subject.id))
      .flatMap((subject) => subject.mapTargetIds),
  );
}

function accepts(subject: QuizSubject, rawInput: string): boolean {
  const normalized = normalizeAnswer(rawInput);
  return subject.acceptedAnswers.includes(normalized);
}

export function submitTextAnswer(
  quiz: QuizSnapshot,
  session: QuizSessionState,
  rawInput: string,
  completedAt = new Date().toISOString(),
): SubmitAnswerResult {
  if (session.status === "completed") {
    return { outcome: "completed", matchedSubjectIds: [], session };
  }

  if (quiz.interactionKind !== "text") {
    throw new Error("submitTextAnswer called for a non-text quiz");
  }

  if (quiz.progressionKind === "sequential") {
    const current = getCurrentSubject(quiz, session);
    if (!current || !accepts(current, rawInput)) {
      return {
        outcome: "incorrect",
        matchedSubjectIds: [],
        session: { ...session, wrongAttempts: session.wrongAttempts + 1 },
      };
    }

    const solvedSubjectIds = [...session.solvedSubjectIds, current.id];
    const isComplete = solvedSubjectIds.length === quiz.subjects.length;

    return {
      outcome: "correct",
      matchedSubjectIds: [current.id],
      session: {
        ...session,
        solvedSubjectIds,
        correctAnswers: session.correctAnswers + 1,
        currentPosition: isComplete
          ? session.currentPosition
          : session.currentPosition + 1,
        status: isComplete ? "completed" : "active",
        completedAt: isComplete ? completedAt : null,
      },
    };
  }

  const solved = new Set(session.solvedSubjectIds);
  const matches = quiz.subjects.filter(
    (subject) => !solved.has(subject.id) && accepts(subject, rawInput),
  );

  if (matches.length === 0) {
    return {
      outcome: "incorrect",
      matchedSubjectIds: [],
      session: { ...session, wrongAttempts: session.wrongAttempts + 1 },
    };
  }

  const sovereigns = new Set(matches.map((subject) => subject.sovereignQid));
  if (sovereigns.size > 1) {
    // Cross-sovereign collisions such as "Congo" stay unresolved.
    return {
      outcome: "incorrect",
      matchedSubjectIds: [],
      session: session,
    };
  }

  const matchedSubjectIds = matches.map((subject) => subject.id);
  const solvedSubjectIds = [...session.solvedSubjectIds, ...matchedSubjectIds];
  const isComplete = solvedSubjectIds.length === quiz.subjects.length;

  return {
    outcome: "correct",
    matchedSubjectIds,
    session: {
      ...session,
      solvedSubjectIds,
      correctAnswers: session.correctAnswers + 1,
      status: isComplete ? "completed" : "active",
      completedAt: isComplete ? completedAt : null,
    },
  };
}
