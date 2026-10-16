interface ProgressIndicatorProps {
  solved: number;
  total: number;
  wrongAttempts: number;
}

export function ProgressIndicator({ solved, total, wrongAttempts }: ProgressIndicatorProps) {
  return (
    <div className="progress" aria-label={`${solved} of ${total} countries solved`}>
      <div>
        <strong>{solved}</strong> / {total} solved
      </div>
      <div>{wrongAttempts} wrong attempt{wrongAttempts === 1 ? "" : "s"}</div>
    </div>
  );
}
