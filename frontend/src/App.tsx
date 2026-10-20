import { useEffect, useMemo, useState } from "react";
import { AnswerInput } from "./components/AnswerInput";
import { EuropeMap } from "./components/EuropeMap";
import { LeaderPrompt } from "./components/LeaderPrompt";
import { ProgressIndicator } from "./components/ProgressIndicator";
import { SnapshotLoader } from "./data/SnapshotLoader";
import {
  createSession,
  getCurrentSubject,
  getHighlightedTargetIds,
  submitTextAnswer,
  type QuizSessionState,
} from "./quiz/quizEngine";
import type { HeadOfStatePrompt, LoadedSnapshot } from "./types/snapshot";

const loader = new SnapshotLoader();

export default function App() {
  const [loaded, setLoaded] = useState<LoadedSnapshot | null>(null);
  const [session, setSession] = useState<QuizSessionState | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [feedback, setFeedback] = useState<string>("");

  useEffect(() => {
    let cancelled = false;

    loader
      .loadLatest("europe-leader")
      .then((snapshot) => {
        if (cancelled) return;
        setLoaded(snapshot);
        setSession(createSession(snapshot.quiz, snapshot.manifest.snapshotId));
      })
      .catch((reason: unknown) => {
        if (cancelled) return;
        setError(reason instanceof Error ? reason.message : String(reason));
      });

    return () => {
      cancelled = true;
    };
  }, []);

  const highlightedTargetIds = useMemo(() => {
    if (!loaded || !session) return new Set<string>();
    return getHighlightedTargetIds(loaded.quiz, session);
  }, [loaded, session]);

  if (error) {
    return <main className="status-screen">Failed to load snapshot: {error}</main>;
  }

  if (!loaded || !session) {
    return <main className="status-screen">Loading immutable quiz snapshot…</main>;
  }

  const currentSubject = getCurrentSubject(loaded.quiz, session);

  function handleSubmit(value: string) {
    if (!loaded || !session) return;
    const result = submitTextAnswer(loaded.quiz, session, value);
    setSession(result.session);
    setFeedback(result.outcome === "correct" ? "Correct." : "Not this one.");
  }

  function restart() {
    setSession(createSession(loaded.quiz, loaded.manifest.snapshotId));
    setFeedback("");
  }

  return (
    <main className="app-shell">
      <header className="page-header">
        <div>
          <p className="eyebrow">Europe · immutable snapshot</p>
          <h1>{loaded.quiz.title}</h1>
        </div>
        <ProgressIndicator
          solved={session.solvedSubjectIds.length}
          total={loaded.quiz.subjects.length}
          wrongAttempts={session.wrongAttempts}
        />
      </header>

      <div className="game-grid">
        <section className="quiz-panel">
          {session.status === "completed" ? (
            <div className="completion-card">
              <p className="eyebrow">Quiz complete</p>
              <h2>You solved all {loaded.quiz.subjects.length} countries.</h2>
              <p>{session.wrongAttempts} wrong attempt{session.wrongAttempts === 1 ? "" : "s"}.</p>
              <button onClick={restart}>Play again</button>
            </div>
          ) : currentSubject?.prompt.kind === "head_of_state" ? (
            <>
              <LeaderPrompt
                prompt={currentSubject.prompt as HeadOfStatePrompt}
                images={loaded.images}
              />
              <AnswerInput onSubmit={handleSubmit} />
              <p className="feedback" aria-live="polite">{feedback}</p>
            </>
          ) : (
            <p>Unsupported prompt in this MVP fixture.</p>
          )}
        </section>

        <EuropeMap map={loaded.map} highlightedTargetIds={highlightedTargetIds} />
      </div>

      <footer>
        Snapshot {loaded.manifest.snapshotId} · Natural Earth version {loaded.manifest.sources.naturalEarthVersion}
      </footer>
    </main>
  );
}
