import MapDataQAScene from "./MapDataQAScene";
import {
  MAP_KOREA_OPERATIONAL_BENCHMARK_SUITE,
  MAP_KOREA_OPERATIONAL_CAPTURE_SPECS,
  MAP_KOREA_OPERATIONAL_READINESS_CHECKLIST,
} from "../readabilityQaConfig.js";

const KOREA_THEATER_ID = "korea_peninsula_coarse_v1";

export default function KoreaOperationalBasemapScene() {
  return (
    <MapDataQAScene
      theaterId={KOREA_THEATER_ID}
      snapshot={null}
      title="Korea Operational QA"
      note="First-pass Korea operational QA view. This scene validates that the peninsula package loads terrain, hydro, transport corridors, settlements, airfields, and crossing cues coherently before any historical correction work begins."
      benchmarkSuite={MAP_KOREA_OPERATIONAL_BENCHMARK_SUITE}
      captureSpecs={MAP_KOREA_OPERATIONAL_CAPTURE_SPECS}
      readinessChecklist={MAP_KOREA_OPERATIONAL_READINESS_CHECKLIST}
    />
  );
}
