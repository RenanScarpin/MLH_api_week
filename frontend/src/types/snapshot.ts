export type WikidataQid = `Q${number}`;

export interface LatestSnapshotPointer {
  snapshotId: string;
  manifest: string;
}

export interface SnapshotSources {
  wikidataFetchedAt: string;
  commonsFetchedAt: string | null;
  naturalEarthVersion: string;
}

export interface SnapshotManifest {
  snapshotId: string;
  generatedAt: string;
  sources: SnapshotSources;
  answerNormalizationVersion: number;
  quizzes: Record<string, string>;
  maps: Record<string, string>;
  images: string;
}

export type SubjectKind = "sovereign_state" | "regional_unit";
export type PromptKind =
  | "head_of_state"
  | "flag"
  | "country_name"
  | "country_name_and_flag"
  | "none";
export type InteractionKind = "text" | "map_click";
export type ProgressionKind = "sequential" | "free_recall";
export type CompletionRule = "all_subjects";

export interface QuizScope {
  kind: "world" | "continent";
  id: string;
  mapId: string;
}

export interface QuizSnapshot {
  id: string;
  title: string;
  scope: QuizScope;
  subjectKind: SubjectKind;
  promptKind: PromptKind;
  interactionKind: InteractionKind;
  progressionKind: ProgressionKind;
  completionRule: CompletionRule;
  subjects: QuizSubject[];
}

export interface QuizSubject {
  id: string;
  entityQid: WikidataQid;
  sovereignQid: WikidataQid;
  displayName: string;
  acceptedAnswers: string[];
  mapTargetIds: string[];
  prompt: QuizPrompt;
}

export type QuizPrompt =
  | HeadOfStatePrompt
  | FlagPrompt
  | CountryNamePrompt
  | CountryNameAndFlagPrompt
  | NoPrompt;

export interface HeadOfStatePrompt {
  kind: "head_of_state";
  heads: HeadOfStateCard[];
}

export interface HeadOfStateCard {
  entityQid: WikidataQid;
  displayName: string;
  imageId: string | null;
}

export interface FlagPrompt {
  kind: "flag";
  imageId: string;
}

export interface CountryNamePrompt {
  kind: "country_name";
  displayName: string;
}

export interface CountryNameAndFlagPrompt {
  kind: "country_name_and_flag";
  displayName: string;
  imageId: string;
}

export interface NoPrompt {
  kind: "none";
}

export interface ImageManifest {
  [imageId: string]: ImageAsset;
}

export interface ImageAsset {
  id: string;
  path: string;
  commonsFilename: string;
  commonsPage: string;
  sha1: string;
  attribution: ImageAttribution;
}

export interface ImageAttribution {
  artist: string | null;
  credit: string | null;
  attributionText: string | null;
  attributionRequired: boolean;
  licenseName: string | null;
  licenseUrl: string | null;
}

export type Position = [number, number];

export interface PolygonGeometry {
  type: "Polygon";
  coordinates: Position[][];
}

export interface MultiPolygonGeometry {
  type: "MultiPolygon";
  coordinates: Position[][][];
}

export type QuizMapGeometry = PolygonGeometry | MultiPolygonGeometry;

export interface MapFeatureProperties {
  targetId: string;
  entityQid: WikidataQid | null;
  sovereignQid: WikidataQid | null;
}

export interface QuizMapFeature {
  type: "Feature";
  id: string;
  properties: MapFeatureProperties;
  geometry: QuizMapGeometry;
}

export interface QuizMapGeoJson {
  type: "FeatureCollection";
  bbox?: [number, number, number, number];
  features: QuizMapFeature[];
}

export interface LoadedSnapshot {
  pointer: LatestSnapshotPointer;
  manifest: SnapshotManifest;
  quiz: QuizSnapshot;
  map: QuizMapGeoJson;
  images: ImageManifest;
}
