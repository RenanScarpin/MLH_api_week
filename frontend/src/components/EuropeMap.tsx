import { useMemo } from "react";
import type { Position, QuizMapFeature, QuizMapGeoJson } from "../types/snapshot";

interface EuropeMapProps {
  map: QuizMapGeoJson;
  highlightedTargetIds: Set<string>;
}

interface Bounds {
  minX: number;
  maxX: number;
  minY: number;
  maxY: number;
}

function pointsOfFeature(feature: QuizMapFeature): Position[] {
  if (feature.geometry.type === "Polygon") {
    return feature.geometry.coordinates.flat();
  }
  return feature.geometry.coordinates.flat(2);
}

function calculateBounds(map: QuizMapGeoJson): Bounds {
  if (map.bbox) {
    const [minX, minY, maxX, maxY] = map.bbox;
    return { minX, maxX, minY, maxY };
  }

  const points = map.features.flatMap(pointsOfFeature);
  const xs = points.map(([x]) => x);
  const ys = points.map(([, y]) => y);
  return {
    minX: Math.min(...xs),
    maxX: Math.max(...xs),
    minY: Math.min(...ys),
    maxY: Math.max(...ys),
  };
}

function createProjector(bounds: Bounds, width: number, height: number, padding: number) {
  const dataWidth = Math.max(bounds.maxX - bounds.minX, 0.0001);
  const dataHeight = Math.max(bounds.maxY - bounds.minY, 0.0001);
  const scale = Math.min((width - padding * 2) / dataWidth, (height - padding * 2) / dataHeight);
  const projectedWidth = dataWidth * scale;
  const projectedHeight = dataHeight * scale;
  const offsetX = (width - projectedWidth) / 2;
  const offsetY = (height - projectedHeight) / 2;

  return ([lon, lat]: Position): Position => [
    offsetX + (lon - bounds.minX) * scale,
    offsetY + (bounds.maxY - lat) * scale,
  ];
}

function ringPath(ring: Position[], project: (position: Position) => Position): string {
  return ring
    .map((point, index) => {
      const [x, y] = project(point);
      return `${index === 0 ? "M" : "L"}${x.toFixed(2)},${y.toFixed(2)}`;
    })
    .join(" ") + " Z";
}

function featurePath(feature: QuizMapFeature, project: (position: Position) => Position): string {
  if (feature.geometry.type === "Polygon") {
    return feature.geometry.coordinates.map((ring) => ringPath(ring, project)).join(" ");
  }

  return feature.geometry.coordinates
    .flatMap((polygon) => polygon.map((ring) => ringPath(ring, project)))
    .join(" ");
}

export function EuropeMap({ map, highlightedTargetIds }: EuropeMapProps) {
  const width = 720;
  const height = 430;

  const paths = useMemo(() => {
    const bounds = calculateBounds(map);
    const project = createProjector(bounds, width, height, 34);
    return map.features.map((feature) => ({
      id: feature.properties.targetId,
      d: featurePath(feature, project),
    }));
  }, [map]);

  return (
    <section className="map-panel" aria-label="Europe map">
      <svg viewBox={`0 0 ${width} ${height}`} role="img" aria-label="Map of Europe">
        {paths.map((path) => (
          <path
            key={path.id}
            d={path.d}
            className={highlightedTargetIds.has(path.id) ? "country solved" : "country"}
            fillRule="evenodd"
            clipRule="evenodd"
          />
        ))}
      </svg>
      <p className="fixture-note">Natural Earth Admin 0 geometry.</p>
    </section>
  );
}
