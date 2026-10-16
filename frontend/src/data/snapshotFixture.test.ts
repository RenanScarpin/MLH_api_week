import assert from "node:assert/strict";
import { readFile } from "node:fs/promises";
import test from "node:test";
import { normalizeAnswer } from "../quiz/normalizeAnswer.ts";
import type { ImageManifest, QuizMapGeoJson, QuizSnapshot } from "../types/snapshot.ts";

async function readJson<T>(relativePath: string): Promise<T> {
  const url = new URL(`../../public/snapshots/demo-v1/${relativePath}`, import.meta.url);
  return JSON.parse(await readFile(url, "utf8")) as T;
}

test("fixture references only existing map targets and images", async () => {
  const [quiz, map, images] = await Promise.all([
    readJson<QuizSnapshot>("quizzes/europe-leader.json"),
    readJson<QuizMapGeoJson>("maps/europe.geojson"),
    readJson<ImageManifest>("assets/images.json"),
  ]);

  const targetIds = new Set(map.features.map((feature) => feature.properties.targetId));

  for (const subject of quiz.subjects) {
    for (const targetId of subject.mapTargetIds) {
      assert.ok(targetIds.has(targetId), `${subject.id} references missing map target ${targetId}`);
    }

    assert.deepEqual(
      subject.acceptedAnswers,
      subject.acceptedAnswers.map(normalizeAnswer),
      `${subject.id} contains an answer that was not pre-normalized`,
    );

    if (subject.prompt.kind === "head_of_state") {
      for (const head of subject.prompt.heads) {
        if (head.imageId !== null) {
          assert.ok(images[head.imageId], `${head.entityQid} references missing image ${head.imageId}`);
        }
      }
    }
  }
});
