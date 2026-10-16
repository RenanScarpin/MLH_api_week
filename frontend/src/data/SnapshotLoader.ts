import type {
  ImageManifest,
  LatestSnapshotPointer,
  LoadedSnapshot,
  QuizMapGeoJson,
  QuizSnapshot,
  SnapshotManifest,
} from "../types/snapshot";

async function loadJson<T>(path: string): Promise<T> {
  const response = await fetch(path, { cache: "no-store" });
  if (!response.ok) {
    throw new Error(`Failed to load ${path}: ${response.status} ${response.statusText}`);
  }
  return (await response.json()) as T;
}

export class SnapshotLoader {
  async loadLatest(quizId: string): Promise<LoadedSnapshot> {
    const pointer = await loadJson<LatestSnapshotPointer>("/latest.json");
    const manifest = await loadJson<SnapshotManifest>(pointer.manifest);

    if (manifest.snapshotId !== pointer.snapshotId) {
      throw new Error("latest.json and manifest.json refer to different snapshots");
    }

    const quizPath = manifest.quizzes[quizId];
    if (!quizPath) {
      throw new Error(`Quiz ${quizId} is not present in snapshot ${manifest.snapshotId}`);
    }

    const quiz = await loadJson<QuizSnapshot>(quizPath);
    const mapPath = manifest.maps[quiz.scope.mapId];
    if (!mapPath) {
      throw new Error(`Map ${quiz.scope.mapId} is not present in the snapshot manifest`);
    }

    const [map, images] = await Promise.all([
      loadJson<QuizMapGeoJson>(mapPath),
      loadJson<ImageManifest>(manifest.images),
    ]);

    return { pointer, manifest, quiz, map, images };
  }
}
