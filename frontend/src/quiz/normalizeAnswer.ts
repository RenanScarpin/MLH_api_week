export const ANSWER_NORMALIZATION_VERSION = 1;

/**
 * Deliberately permissive normalization for typed geography answers.
 * Source aliases still determine what is valid; normalization only makes
 * formatting differences irrelevant.
 */
export function normalizeAnswer(value: string): string {
  return value
    .normalize("NFKD")
    .replace(/\p{M}/gu, "")
    .toLocaleLowerCase("en-US")
    .replace(/[.’'`]/gu, "")
    .replace(/[-_/(),:;]+/gu, " ")
    .replace(/[^\p{L}\p{N}\s]+/gu, " ")
    .trim()
    .replace(/\s+/gu, " ");
}
