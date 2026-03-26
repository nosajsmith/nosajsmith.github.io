import MapDataQAScene from "./MapDataQAScene";
import {
  MAP_KOREA_PHYSICAL_BENCHMARK_SUITE,
  MAP_KOREA_PHYSICAL_CAPTURE_SPECS,
  MAP_KOREA_PHYSICAL_READINESS_CHECKLIST,
} from "../readabilityQaConfig.js";

const KOREA_THEATER_ID = "korea_peninsula_coarse_v1";

export default function KoreaPhysicalBasemapScene() {
  return (
    <MapDataQAScene
      theaterId={KOREA_THEATER_ID}
      snapshot={null}
      title="Korea Physical QA"
      note="Coarse peninsula physical basemap QA view. This scene validates that the production Korea package loads terrain-bearing data, renders relief and hydro coherently, and stays free of fallback failure before roads, settlements, and historical correction are added."
      benchmarkSuite={MAP_KOREA_PHYSICAL_BENCHMARK_SUITE}
      captureSpecs={MAP_KOREA_PHYSICAL_CAPTURE_SPECS}
      readinessChecklist={MAP_KOREA_PHYSICAL_READINESS_CHECKLIST}
    />
  );
}
