import type { HeadOfStatePrompt, ImageManifest } from "../types/snapshot";

interface LeaderPromptProps {
  prompt: HeadOfStatePrompt;
  images: ImageManifest;
}

export function LeaderPrompt({ prompt, images }: LeaderPromptProps) {
  return (
    <section className="leader-prompt" aria-label="Current head or heads of state">
      <p className="eyebrow">Which sovereign state are these head(s) of state from?</p>
      <div className="leader-grid">
        {prompt.heads.map((head) => {
          const image = head.imageId ? images[head.imageId] : undefined;

          return (
            <article className="leader-card" key={head.entityQid}>
              {image ? (
                <img src={image.path} alt={head.displayName} />
              ) : (
                <div className="leader-placeholder" aria-hidden="true">
                  <span>{head.displayName.slice(0, 1)}</span>
                </div>
              )}
              <h2>{head.displayName}</h2>
              {image && (
                <a
                  className="image-credit"
                  href={image.commonsPage}
                  target="_blank"
                  rel="noreferrer"
                >
                  Image credit
                </a>
              )}
            </article>
          );
        })}
      </div>
    </section>
  );
}
