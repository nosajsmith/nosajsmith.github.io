import test from "node:test";
import assert from "node:assert/strict";

import {
  buildInitialMapCamera,
  buildMapScene,
  buildOperationalOverlayState,
  clampMapCamera,
  projectScenePoint,
  projectMapCameraPoint,
  summarizeMapZoomPresentation,
  unprojectScenePoint,
} from "../src/components/shell/map_scene.js";

test("map scene keeps clustered label placement deterministic without changing marker anchors", () => {
  const snapshot = {
    units: [
      { id: "u1", name: "Alpha Company", side: "ALLIED", kind: "land", x: 4, y: 4 },
      { id: "u2", name: "Bravo Company", side: "ALLIED", kind: "land", x: 4, y: 4 },
      { id: "u3", name: "Charlie Company", side: "ALLIED", kind: "land", x: 8, y: 5 },
    ],
    objectives: [
      { id: "o1", name: "Henderson Field", state: "held_allied", side: "ALLIED", x: 4, y: 4 },
    ],
  };

  const scene = buildMapScene(snapshot, { width: 1000, height: 620, inset: 60 });
  const objective = scene.objectives[0];
  const alpha = scene.units.find((unit) => unit.id === "u1");
  const bravo = scene.units.find((unit) => unit.id === "u2");
  const charlie = scene.units.find((unit) => unit.id === "u3");

  assert.ok(objective);
  assert.ok(alpha);
  assert.ok(bravo);
  assert.ok(charlie);

  assert.deepEqual(objective.anchor, objective.baseAnchor);
  assert.notDeepEqual(objective.displayAnchor, objective.anchor);
  assert.equal(objective.labelAnchor, "start");
  assert.equal(objective.labelX, 12);
  assert.equal(objective.labelY, -12);
  assert.equal(objective.stateAnchor, "start");
  assert.equal(objective.stateY, 14);
  assert.equal(alpha.labelAnchor, "end");
  assert.equal(alpha.labelOffsetX, -24);
  assert.equal(alpha.labelOffsetY, 4);
  assert.equal(bravo.labelAnchor, "start");
  assert.equal(bravo.labelOffsetX, 24);
  assert.equal(bravo.labelOffsetY, 4);
  assert.equal(charlie.labelAnchor, "middle");
  assert.equal(charlie.labelOffsetX, 0);
});

test("map scene round-trips scene projection for stable overlay world coordinates", () => {
  const snapshot = {
    units: [{ id: "u1", name: "1st Marines", side: "ALLIED", kind: "land", x: 4, y: 6 }],
    objectives: [{ id: "o1", name: "Henderson", state: "held_allied", side: "ALLIED", x: 8, y: 5 }],
  };

  const scene = buildMapScene(snapshot, { width: 1000, height: 620, inset: 60 });
  const worldPoint = { x: 6.5, y: 5.5 };
  const scenePoint = projectScenePoint(worldPoint, scene);
  const restoredPoint = unprojectScenePoint(scenePoint, scene);

  assert.ok(Math.abs(restoredPoint.x - worldPoint.x) < 0.01);
  assert.ok(Math.abs(restoredPoint.y - worldPoint.y) < 0.01);
});

test("map scene plots airfields and ports as infrastructure markers without needing unit counters", () => {
  const snapshot = {
    units: [],
    objectives: [],
    airfields: [{ id: "af-1", name: "Kimpo", x: 7, y: 4 }],
    ports: [{ id: "pt-1", name: "Inchon", x: 3, y: 5 }],
  };

  const scene = buildMapScene(snapshot, { width: 1000, height: 620, inset: 60 });

  assert.equal(scene.emptyState, null);
  assert.equal(scene.airfields.length, 1);
  assert.equal(scene.ports.length, 1);
  assert.equal(scene.stats.visibleAirfields, 1);
  assert.equal(scene.stats.visiblePorts, 1);
  assert.equal(scene.airfields[0].name, "Kimpo");
  assert.equal(scene.ports[0].name, "Inchon");
  assert.ok(scene.airfields[0].displayAnchor);
  assert.ok(scene.ports[0].displayAnchor);
  assert.equal(scene.airfields[0].airfield?.tier, "operational_airfield");
  assert.match(scene.airfields[0].labelAnchor, /middle|start|end/);
  assert.match(scene.ports[0].labelAnchor, /middle|start|end/);
});

test("map scene derives runway-tier and control metadata for airfields from authoritative nearby context", () => {
  const snapshot = {
    units: [{
      id: "air-1",
      name: "Cactus Air Wing",
      kind: "air",
      location_id: "HENDERSON_FIELD",
      readiness: 72,
      inspector: { orders: { action: "sortie launch", status: "executing" }, operational_state: { posture: "Sortie" } },
    }],
    objectives: [{ id: "o1", name: "Henderson Field", state: "held_allied", side: "ALLIED", value: 100, x: 5, y: 3 }],
    airfields: [{ id: "HENDERSON_FIELD", name: "Henderson Field", x: 5, y: 3 }],
    ports: [],
  };

  const scene = buildMapScene(snapshot, { width: 1000, height: 620, inset: 60 });
  const airfield = scene.airfields[0];

  assert.equal(airfield.airfield?.tier, "major_airbase");
  assert.equal(airfield.airfield?.controlState, "friendly");
  assert.equal(airfield.airfield?.readinessBand, "ready");
  assert.equal(airfield.airfield?.sortieActive, true);
});

test("map scene derives compact legend sections from the symbols present in the active slice", () => {
  const snapshot = {
    units: [
      { id: "u1", name: "1st Marines", side: "ALLIED", kind: "land", unit_type: "INFANTRY", x: 4, y: 4 },
      { id: "u2", name: "Division HQ", side: "ALLIED", kind: "land", unit_type: "HEADQUARTERS", x: 4, y: 4 },
      { id: "u3", name: "Recon Troop", side: "AXIS", kind: "recon", unit_type: "RECON", x: 8, y: 5 },
    ],
    objectives: [
      { id: "o1", name: "Henderson", state: "held_allied", side: "ALLIED", x: 5, y: 3 },
      { id: "o2", name: "Bloody Ridge", state: "unheld", side: "ALLIED", x: 7, y: 6 },
    ],
    airfields: [{ id: "af-1", name: "Henderson Field", x: 6, y: 4 }],
    ports: [{ id: "pt-1", name: "Lunga Point", x: 3, y: 6 }],
  };

  const scene = buildMapScene(snapshot, { width: 1000, height: 620, inset: 60 });

  assert.deepEqual(scene.legend.map((section) => section.title), ["Forces", "Symbols", "Map Marks"]);
  assert.deepEqual(
    scene.legend[0].rows.map((row) => row.label),
    ["Allied formations", "Axis formations"],
  );
  assert.deepEqual(
    scene.legend[1].rows.map((row) => row.label),
    ["HQ / command", "Marine / infantry", "Recon"],
  );
  assert.match(scene.legend[2].rows.map((row) => row.label).join(" | "), /Friendly-controlled locality/);
  assert.match(scene.legend[2].rows.map((row) => row.label).join(" | "), /Contested locality/);
  assert.match(scene.legend[2].rows.map((row) => row.label).join(" | "), /Airfield/);
  assert.match(scene.legend[2].rows.map((row) => row.label).join(" | "), /Port \/ shore point/);
  assert.match(scene.legend[2].rows.map((row) => row.label).join(" | "), /Leader line/);
});

test("map scene derives scalable settlement metadata for objective localities", () => {
  const snapshot = {
    units: [],
    objectives: [
      { id: "o1", name: "Henderson Field", value: 100, state: "held_allied", side: "ALLIED", x: 4, y: 4 },
      { id: "o2", name: "Kokumbona", value: 75, state: "held_axis", side: "AXIS", x: 8, y: 5 },
      { id: "o3", name: "Bloody Ridge", value: 45, state: "unheld", side: "ALLIED", x: 10, y: 7 },
    ],
  };

  const scene = buildMapScene(snapshot, { width: 1000, height: 620, inset: 60 });

  assert.equal(scene.objectives.find((objective) => objective.id === "o1")?.settlement?.tier, "capital");
  assert.equal(scene.objectives.find((objective) => objective.id === "o1")?.settlement?.controlState, "friendly");
  assert.equal(scene.objectives.find((objective) => objective.id === "o1")?.objectiveOverlay?.category, "strategic");
  assert.match(scene.objectives.find((objective) => objective.id === "o1")?.stateLabel ?? "", /100 VP/i);
  assert.equal(scene.objectives.find((objective) => objective.id === "o2")?.settlement?.tier, "major_city");
  assert.equal(scene.objectives.find((objective) => objective.id === "o2")?.settlement?.controlState, "enemy");
  assert.equal(scene.objectives.find((objective) => objective.id === "o2")?.objectiveOverlay?.category, "primary");
  assert.equal(scene.objectives.find((objective) => objective.id === "o3")?.settlement?.tier, "town");
  assert.equal(scene.objectives.find((objective) => objective.id === "o3")?.settlement?.controlState, "contested");
  assert.equal(scene.objectives.find((objective) => objective.id === "o3")?.objectiveOverlay?.contested, true);
  assert.match(scene.objectives.find((objective) => objective.id === "o3")?.stateLabel ?? "", /contested/i);
});

test("map scene derives an Inchon-to-Seoul operational axis when Korea slice anchors exist but authored lines do not", () => {
  const snapshot = {
    scenario: { id: "inchon_mvp", name: "Operation Chromite" },
    units: [],
    objectives: [{ id: "o1", name: "Seoul", value: 100, state: "unheld", side: "ALLIED", x: 8, y: 4 }],
    airfields: [{ id: "af1", name: "Kimpo", x: 6, y: 5 }],
    ports: [{ id: "pt1", name: "Inchon", x: 3, y: 6 }],
    named_features: [],
  };

  const scene = buildMapScene(snapshot, { width: 1000, height: 620, inset: 60 });
  const axis = scene.namedFeatures.find((feature) => feature.id === "derived:korea:seoul_axis");

  assert.ok(axis);
  assert.equal(axis.geometryType, "line");
  assert.equal(axis.label, "Seoul Axis");
  assert.equal(axis.important, true);
  assert.equal(axis.visibility, "always");
});

test("map scene computes a tighter initial camera fit for the Inchon Seoul axis instead of centering a loose theater extent", () => {
  const snapshot = {
    scenario: { id: "inchon_mvp", name: "Inchon Demo Vertical Slice" },
    map_presentation: {
      hex_scale_km: 5,
      playable_scale_locked: true,
      world_bounds: { min_x: 14.2, max_x: 51.2, min_y: 31, max_y: 60.8 },
      focus_points: [
        { id: "focus_inchon_harbor", label: "Inchon Harbor", x: 18.2, y: 58.1 },
        { id: "focus_yongdungpo_crossings", label: "Yongdungpo Crossings", x: 39.4, y: 40.6 },
        { id: "focus_seoul", label: "Seoul", x: 46, y: 36 },
        { id: "focus_kpa_reserve", label: "NKPA Reserve Belt", x: 49.1, y: 32.6 },
      ],
    },
    units: [
      { id: "rear-1", name: "NKPA Counterattack Reserve", side: "AXIS", kind: "land", x: 49.1, y: 32.6 },
    ],
    objectives: [
      { id: "o1", name: "Inchon Harbor", value: 70, state: "held_allied", side: "ALLIED", x: 18.2, y: 58.1 },
      { id: "o1b", name: "Kimpo Airfield", value: 80, state: "unheld", side: "ALLIED", x: 31, y: 46 },
      { id: "o1c", name: "Yongdungpo Crossings", value: 70, state: "unheld", side: "ALLIED", x: 39.4, y: 40.6 },
      { id: "o2", name: "Seoul", value: 100, state: "unheld", side: "ALLIED", x: 46, y: 36 },
      { id: "o3", name: "Seoul Defensive Ring", value: 90, state: "held_axis", side: "AXIS", x: 47.2, y: 34.4 },
    ],
    airfields: [{ id: "af1", name: "Kimpo Airfield", x: 31, y: 46 }],
    ports: [{ id: "pt1", name: "Inchon Harbor", x: 18.2, y: 58.1 }],
    local_pressure_areas: [
      { id: "lp1", label: "Kimpo Corridor", x: 31, y: 46 },
      { id: "lp2", label: "Yongdungpo Crossings", x: 39.4, y: 40.6 },
      { id: "lp3", label: "Seoul Defensive Ring", x: 47.2, y: 34.4 },
    ],
    named_features: [
      {
        id: "inchon_beachhead_feature",
        label: "Inchon Beachhead",
        kind: "sector",
        geometry_type: "zone",
        points: [{ x: 15.8, y: 60.4 }, { x: 22.4, y: 59.4 }, { x: 24.3, y: 55.1 }, { x: 21, y: 52.4 }, { x: 15.9, y: 53.7 }, { x: 14.4, y: 57.6 }],
        label_priority: 5,
      },
      {
        id: "seoul_axis",
        label: "Seoul Axis",
        kind: "phase_line",
        geometry_type: "line",
        points: [{ x: 18.2, y: 58.2 }, { x: 25.1, y: 52.1 }, { x: 31, y: 46 }, { x: 39.4, y: 40.6 }, { x: 46, y: 36 }],
        label_priority: 5,
      },
      {
        id: "han_river",
        label: "Han River",
        kind: "waterway",
        geometry_type: "line",
        points: [{ x: 27.4, y: 47.8 }, { x: 33.2, y: 44.7 }, { x: 39, y: 41.6 }, { x: 45.4, y: 38.3 }, { x: 50.8, y: 36.8 }],
        label_priority: 4,
      },
      {
        id: "seoul_defensive_belt_feature",
        label: "Seoul Defensive Belt",
        kind: "sector",
        geometry_type: "zone",
        points: [{ x: 42.6, y: 38.8 }, { x: 47.8, y: 39.1 }, { x: 49.8, y: 35.4 }, { x: 47.8, y: 32.5 }, { x: 43.2, y: 32.8 }, { x: 41.1, y: 35.9 }],
        label_priority: 4,
      },
    ],
  };

  const scene = buildMapScene(snapshot, { width: 1000, height: 620, inset: 60 });
  const camera = buildInitialMapCamera(snapshot, scene);
  const inchon = projectMapCameraPoint(projectScenePoint({ x: 18, y: 58 }, scene), camera);
  const seoul = projectMapCameraPoint(projectScenePoint({ x: 46, y: 36 }, scene), camera);
  const midpoint = {
    x: (inchon.x + seoul.x) / 2,
    y: (inchon.y + seoul.y) / 2,
  };

  assert.equal(scene.namedFeatures.filter((feature) => feature.label === "Seoul Axis").length, 1);
  assert.deepEqual(scene.viewport, { minX: 14.2, maxX: 51.2, minY: 31, maxY: 60.8 });
  assert.ok(camera.zoom > 1.05);
  assert.ok(Math.abs(midpoint.x - scene.width / 2) < 55);
  assert.ok(Math.abs(midpoint.y - scene.height / 2) < 50);
  assert.ok(inchon.x > 55 && seoul.x < scene.width - 75);
});

test("map scene honors authored objective categories and builds named feature geometry rows", () => {
  const snapshot = {
    units: [
      {
        id: "u1",
        name: "1st Marine Division",
        map_label: "1ST MAR DIV",
        label_priority: 4,
        side: "ALLIED",
        kind: "land",
        x: 4,
        y: 4,
      },
    ],
    objectives: [
      {
        id: "o1",
        name: "Seoul",
        map_label: "SEOUL",
        value: 100,
        state: "unheld",
        side: "ALLIED",
        x: 4,
        y: 4,
        objective_type: "political",
        importance_tier: 3,
        visibility: "always",
        label_offset_x: -14,
        label_offset_y: -18,
        label_anchor: "end",
      },
    ],
    named_features: [
      {
        id: "f1",
        label: "Hill 902",
        map_label: "HILL 902",
        kind: "hill",
        geometry_type: "point",
        x: 5,
        y: 5,
        visibility: "operational",
        label_priority: 2,
        label_offset_x: 8,
        label_offset_y: -14,
        label_anchor: "middle",
        aliases: [{ name: "Height 902", era: "historical" }],
      },
      {
        id: "f2",
        label: "Phase Line Bravo",
        map_label: "PHASE LINE BRAVO",
        kind: "phase_line",
        geometry_type: "line",
        x: 7,
        y: 6,
        points: [{ x: 4, y: 6 }, { x: 7, y: 6 }, { x: 10, y: 7 }],
        visibility: "always",
        label_priority: 3,
        label_offset_x: 12,
        label_offset_y: -8,
        label_anchor: "end",
      },
    ],
  };

  const scene = buildMapScene(snapshot, { width: 1000, height: 620, inset: 60 });

  assert.equal(scene.objectives[0].objectiveOverlay?.category, "political");
  assert.equal(scene.objectives[0].objectiveOverlay?.importanceTier, 3);
  assert.equal(scene.objectives[0].map_label, "SEOUL");
  assert.equal(scene.namedFeatures[0].geometryType, "point");
  assert.equal(scene.namedFeatures[0].map_label, "HILL 902");
  assert.equal(scene.namedFeatures[0].labelOffsetY, -14);
  assert.equal(scene.namedFeatures[1].geometryType, "line");
  assert.equal(scene.namedFeatures[1].important, true);
  assert.equal(scene.namedFeatures[1].labelAnchor, "end");
  assert.equal(scene.units[0].labelForceVisible, true);
  assert.equal(scene.stats.visibleNamedFeatures, 2);
});

test("map scene derives echelon-aware counter frame metadata for units", () => {
  const snapshot = {
    units: [
      { id: "u1", name: "Alpha Company", side: "ALLIED", kind: "land", unit_type: "INFANTRY", x: 2, y: 2 },
      { id: "u2", name: "1st Marines", side: "ALLIED", kind: "land", unit_type: "INFANTRY", x: 4, y: 4 },
      { id: "u3", name: "Division HQ", side: "ALLIED", kind: "land", unit_type: "HEADQUARTERS", x: 6, y: 6 },
      { id: "u4", name: "XIV Corps", side: "ALLIED", kind: "land", unit_type: "HEADQUARTERS", x: 8, y: 8 },
    ],
    objectives: [],
  };

  const scene = buildMapScene(snapshot, { width: 1000, height: 620, inset: 60 });

  assert.equal(scene.units.find((unit) => unit.id === "u1")?.counterFrame?.echelon, "company");
  assert.equal(scene.units.find((unit) => unit.id === "u2")?.counterFrame?.echelon, "regiment");
  assert.equal(scene.units.find((unit) => unit.id === "u3")?.counterFrame?.echelon, "division");
  assert.equal(scene.units.find((unit) => unit.id === "u3")?.counterFrame?.isHeadquarters, true);
  assert.equal(scene.units.find((unit) => unit.id === "u4")?.counterFrame?.echelon, "corps");
});

test("map scene derives counter appearance metadata for service and faction colors", () => {
  const snapshot = {
    units: [
      { id: "u1", name: "1st Marines", side: "ALLIED", kind: "land", unit_type: "INFANTRY", x: 2, y: 2 },
      { id: "u2", name: "Task Force 77", side: "ALLIED", kind: "naval", unit_type: "NAVAL", x: 4, y: 4 },
      { id: "u3", name: "5th Air Wing", side: "ALLIED", kind: "air", unit_type: "AIR", x: 6, y: 6 },
      { id: "u4", name: "ROK Regiment", side: "ROK", kind: "land", unit_type: "INFANTRY", x: 8, y: 8 },
      { id: "u5", name: "Unknown Contact", side: "", kind: "land", unit_type: "INFANTRY", x: 10, y: 10 },
      { id: "u6", name: "Broken Battalion", side: "ALLIED", kind: "land", unit_type: "INFANTRY", status: "active", x: 12, y: 12, inspector: { operational_state: { loc: { state: "broken" } } } },
    ],
    objectives: [],
  };

  const scene = buildMapScene(snapshot, { width: 1000, height: 620, inset: 60 });

  assert.equal(scene.units.find((unit) => unit.id === "u1")?.counterAppearance?.service, "marines");
  assert.equal(scene.units.find((unit) => unit.id === "u2")?.counterAppearance?.service, "navy");
  assert.equal(scene.units.find((unit) => unit.id === "u3")?.counterAppearance?.service, "air_force");
  assert.equal(scene.units.find((unit) => unit.id === "u4")?.counterAppearance?.faction, "partner");
  assert.equal(scene.units.find((unit) => unit.id === "u5")?.counterAppearance?.faction, "unknown");
  assert.equal(scene.units.find((unit) => unit.id === "u6")?.counterAppearance?.outOfCommand, true);
});

test("map scene derives counter symbols for core land roles without needing labels", () => {
  const snapshot = {
    units: [
      { id: "u1", name: "1st Marines", side: "ALLIED", kind: "land", unit_type: "INFANTRY", x: 2, y: 2 },
      { id: "u2", name: "1st Tank Battalion", side: "AXIS", kind: "land", unit_type: "TANK_BATTALION", x: 4, y: 4 },
      { id: "u3", name: "7th Mechanized Brigade", side: "ALLIED", kind: "mechanized", unit_type: "MECHANIZED_INFANTRY", x: 6, y: 6 },
      { id: "u4", name: "11th Marines Battery", side: "ALLIED", kind: "artillery", unit_type: "ARTILLERY_BATTALION", x: 8, y: 8 },
      { id: "u5", name: "Americal Division HQ", side: "ALLIED", kind: "land", unit_type: "HEADQUARTERS", x: 10, y: 10 },
      { id: "u6", name: "Recon Troop", side: "AXIS", kind: "recon", unit_type: "RECON", x: 12, y: 12 },
      { id: "u7", name: "11th Engineers", side: "ALLIED", kind: "engineer", unit_type: "ENGINEER_BATTALION", x: 14, y: 14 },
    ],
    objectives: [],
  };

  const scene = buildMapScene(snapshot, { width: 1000, height: 620, inset: 60 });

  assert.equal(scene.units.find((unit) => unit.id === "u1")?.counterSymbol?.id, "infantry");
  assert.equal(scene.units.find((unit) => unit.id === "u2")?.counterSymbol?.id, "armor");
  assert.equal(scene.units.find((unit) => unit.id === "u3")?.counterSymbol?.id, "mechanized");
  assert.equal(scene.units.find((unit) => unit.id === "u4")?.counterSymbol?.id, "artillery");
  assert.equal(scene.units.find((unit) => unit.id === "u5")?.counterSymbol?.id, "headquarters");
  assert.equal(scene.units.find((unit) => unit.id === "u6")?.counterSymbol?.id, "recon");
  assert.equal(scene.units.find((unit) => unit.id === "u7")?.counterSymbol?.id, "engineer");
});

test("map scene derives scan-friendly counter status overlays from exposed readiness, supply, and order state", () => {
  const snapshot = {
    units: [
      {
        id: "u1",
        name: "Moving Battalion",
        side: "ALLIED",
        kind: "land",
        unit_type: "INFANTRY",
        x: 2,
        y: 2,
        inspector: {
          operational_state: { readiness: 69, fatigue: 18, morale: 72, cohesion: 68, loc: { state: "connected" } },
          supply: { supply_pct: 79, supply_days_current: 4.1 },
          orders: { action: "move", lifecycle_state: "moving to start line", status: "executing" },
        },
      },
      {
        id: "u2",
        name: "Critical Regiment",
        side: "ALLIED",
        kind: "land",
        unit_type: "INFANTRY",
        x: 4,
        y: 4,
        inspector: {
          operational_state: { readiness: 29, fatigue: 71, morale: 33, cohesion: 31, loc: { state: "broken" } },
          supply: { supply_pct: 26, supply_days_current: 1.2 },
          orders: { action: "counterattack", status: "engaged" },
        },
      },
      {
        id: "u3",
        name: "Damaged Battery",
        side: "ALLIED",
        kind: "artillery",
        unit_type: "ARTILLERY_BATTALION",
        x: 6,
        y: 6,
        status: "degraded after contact",
        inspector: {
          operational_state: { readiness: 50, fatigue: 47, morale: 54, cohesion: 56, loc: { state: "connected" } },
          supply: { supply_pct: 61, supply_days_current: 2.8 },
          orders: { action: "hold", status: "recovering" },
        },
      },
    ],
    objectives: [],
  };

  const scene = buildMapScene(snapshot, { width: 1000, height: 620, inset: 60 });

  assert.equal(scene.units.find((unit) => unit.id === "u1")?.counterStatusOverlay?.edgeState, "moving");
  assert.equal(scene.units.find((unit) => unit.id === "u2")?.counterStatusOverlay?.edgeState, "critical");
  assert.equal(scene.units.find((unit) => unit.id === "u2")?.counterStatusOverlay?.lowSupply, true);
  assert.equal(scene.units.find((unit) => unit.id === "u2")?.counterStatusOverlay?.outOfCommand, true);
  assert.equal(scene.units.find((unit) => unit.id === "u3")?.counterStatusOverlay?.damaged, true);
});

test("operational overlay state exposes only authoritative plotted overlays", () => {
  const snapshot = {
    time: { current_hours: 12 },
    weather: {
      condition: "Overcast",
      ground: "mud",
      forecast: [
        { id: "wx-1", hour: 12, visibility: "limited" },
      ],
    },
    units: [
      {
        id: "hq-1",
        name: "1st Marine Division HQ",
        side: "ALLIED",
        kind: "land",
        unit_type: "HEADQUARTERS",
        x: 2,
        y: 3,
        inspector: {
          operational_state: {
            readiness: 78,
            cohesion: 74,
            loc: {
              state: "threatened",
              detail: "Threatened on supply route",
            },
          },
          supply: {
            supply_pct: 68,
            supply_days_current: 3.1,
          },
          command: {
            superior: null,
            hq_unit_id: null,
            subordinates: [{ id: "u2", name: "1st Marines", side: "ALLIED", kind: "land" }],
          },
          branch_specific: {
            artillery: null,
          },
        },
      },
      {
        id: "u2",
        name: "1st Marines",
        side: "ALLIED",
        kind: "land",
        x: 4,
        y: 6,
        inspector: {
          operational_state: {
            readiness: 72,
            cohesion: 69,
            loc: {
              state: "connected",
              detail: "Connected to division rear",
            },
          },
          supply: {
            supply_pct: 81,
            supply_days_current: 4.4,
          },
          movement: {
            remaining: "mobile",
            km_remaining: 18,
          },
          orders: {
            action: "move to Henderson",
            lifecycle_state: "executing",
            status: "advancing",
          },
          command: {
            superior: { id: "hq-1", name: "1st Marine Division HQ", side: "ALLIED", kind: "land" },
            hq_unit_id: "hq-1",
            subordinates: [],
          },
          branch_specific: {
            artillery: null,
          },
        },
      },
      {
        id: "u3",
        name: "11th Marines Battery",
        side: "ALLIED",
        kind: "artillery",
        unit_type: "ARTILLERY_BATTALION",
        x: 6,
        y: 4,
        inspector: {
          operational_state: {
            readiness: 64,
            cohesion: 58,
            loc: {
              state: "connected",
              detail: "Connected to division rear",
            },
          },
          supply: {
            supply_pct: 61,
            supply_days_current: 2.7,
          },
          movement: {
            remaining: "restricted",
            km_remaining: 6,
          },
          orders: {
            action: "counterattack Ilu Crossing",
            lifecycle_state: "queued",
            status: "preparing",
          },
          command: {
            superior: { id: "hq-1", name: "1st Marine Division HQ", side: "ALLIED", kind: "land" },
            hq_unit_id: "hq-1",
            subordinates: [],
          },
          branch_specific: {
            artillery: {
              fire_policy: "General Support",
            },
          },
        },
      },
    ],
    objectives: [
      { id: "obj-1", name: "Henderson", value: 100, state: "held_allied", side: "ALLIED", x: 5, y: 3 },
    ],
    airfields: [{ id: "HENDERSON_FIELD", name: "Henderson Field", x: 5, y: 3 }],
    ports: [{ id: "pt-1", name: "Lunga Point", x: 1, y: 7 }],
    reports: {
      recent: [
        { id: "r1", kind: "contact", title: "Creek contact", summary: "Enemy probes remain active near Alligator Creek.", severity: "info", time: 11, local_area_id: "a1" },
        { id: "r2", kind: "warning", title: "Ilu attack", summary: "Heavy contact confirms an attack at Ilu Crossing.", severity: "warning", time: 12, local_area_id: "a2" },
      ],
    },
    local_pressure_areas: [
      { id: "a1", label: "Alligator Creek", kind: "approach", x: 3, y: 4, pressure_reasons: [], location_id: null, objective_id: null, defensive_preparation: { obstacle_state: null, fortification_state: null, engineer_state: null, state: null } },
      { id: "a2", label: "Ilu Crossing", kind: "approach", x: 4.5, y: 5, pressure_reasons: [], location_id: null, objective_id: null, defensive_preparation: { obstacle_state: "Bridge prepared", fortification_state: null, engineer_state: null, state: null } },
      { id: "a3", label: "Matanikau Forks", kind: "approach", x: 6, y: 5.2, pressure_reasons: [], location_id: null, objective_id: null, defensive_preparation: { obstacle_state: null, fortification_state: null, engineer_state: null, state: null } },
    ],
  };

  const scene = buildMapScene(snapshot, { width: 1000, height: 620, inset: 60 });
  const overlays = buildOperationalOverlayState(snapshot, scene);

  assert.equal(overlays.historicalUnderlay.available, false);
  assert.equal(overlays.terrainEmphasis.available, true);
  assert.equal(overlays.weatherWash.available, true);
  assert.equal(overlays.objectives.available, true);
  assert.equal(overlays.infrastructure.available, true);
  assert.equal(overlays.infrastructure.nodes.length, 3);
  assert.match(overlays.infrastructure.status, /1 port/i);
  assert.equal(overlays.barriers.available, true);
  assert.equal(overlays.barriers.features.length, 3);
  assert.equal(overlays.movementIntent.available, true);
  assert.equal(overlays.movementIntent.paths.length, 2);
  assert.match(overlays.movementIntent.status, /movement/i);
  assert.equal(overlays.frontline.available, true);
  assert.equal(overlays.frontline.sectors.length, 3);
  assert.equal(overlays.frontline.segments.length, 2);
  assert.match(overlays.frontline.status, /hot/i);
  assert.equal(overlays.supply.available, true);
  assert.equal(overlays.supply.markers.length, 3);
  assert.equal(overlays.supply.sources.length, 2);
  assert.equal(overlays.supply.corridors.length, 3);
  assert.match(overlays.supply.status, /well/i);
  assert.equal(overlays.command.available, true);
  assert.equal(overlays.command.hqs.length, 1);
  assert.equal(overlays.command.links.length, 2);
  assert.equal(overlays.artillery.available, true);
  assert.equal(overlays.artillery.markers.length, 1);
  assert.equal(overlays.artillery.status, "1 formations");
  assert.equal(overlays.fogIntel.available, true);
  assert.equal(overlays.fogIntel.contacts.length, 2);
  assert.equal(overlays.fogIntel.status, "1 confirmed • 1 tentative");
  assert.equal(overlays.weatherImpact.available, true);
  assert.equal(overlays.weatherImpact.current, "Overcast");
  assert.equal(overlays.weatherImpact.timeState, "Daylight");
  assert.equal(overlays.weatherImpact.operations, "Context exposed");
  assert.equal(overlays.weatherImpact.visibility, "Limited");
  assert.equal(overlays.weatherImpact.nightOperations, "Not modeled");
  assert.equal(overlays.weatherImpact.air, "Weather cue only");
  assert.equal(overlays.weatherImpact.groundMovement, "Mud");
  assert.match(overlays.weatherImpact.note, /ground state Mud and visibility Limited/i);
  assert.equal(overlays.reconIntel.available, false);
  assert.equal(overlays.reconIntel.status, "Not exposed");
  assert.equal(overlays.airInfluence.available, false);
  assert.equal(overlays.navalSupport.available, false);
  assert.equal(overlays.objectives.available, true);
  assert.equal(overlays.objectives.counts.strategic, 1);
});

test("operational overlay state stays honest when overlay data is unavailable", () => {
  const snapshot = {
    scenario: { id: "mini_gc_1942", name: "Mini GC 1942" },
    units: [
      {
        id: "u1",
        name: "Service Group",
        side: "ALLIED",
        kind: "logistics",
        x: 1,
        y: 1,
        inspector: {
          operational_state: {
            loc: {
              state: "unavailable",
              detail: "LOC state unavailable",
            },
          },
          branch_specific: {
            artillery: null,
          },
        },
      },
    ],
    objectives: [],
  };

  const overlays = buildOperationalOverlayState(snapshot, buildMapScene(snapshot, { width: 1000, height: 620, inset: 60 }));

  assert.equal(overlays.supply.available, false);
  assert.equal(overlays.supply.status, "Unavailable");
  assert.match(overlays.supply.detail, /not exposed/i);
  assert.equal(overlays.command.available, false);
  assert.equal(overlays.movementIntent.available, false);
  assert.equal(overlays.frontline.available, false);
  assert.equal(overlays.infrastructure.available, false);
  assert.equal(overlays.barriers.available, false);
  assert.equal(overlays.artillery.available, false);
  assert.equal(overlays.artillery.status, "Unavailable");
  assert.equal(overlays.fogIntel.available, true);
  assert.equal(overlays.fogIntel.status, "Wash only");
  assert.equal(overlays.weatherImpact.available, false);
  assert.equal(overlays.weatherImpact.timeState, "Time unavailable");
  assert.equal(overlays.weatherImpact.operations, "Unavailable");
  assert.equal(overlays.weatherImpact.visibility, "Not exposed");
  assert.equal(overlays.weatherImpact.nightOperations, "Not modeled");
  assert.equal(overlays.weatherImpact.groundMovement, "Not exposed");
  assert.match(overlays.weatherImpact.note, /weather impact is not exposed/i);
});

test("operational overlay state surfaces night conditions without inventing visibility penalties", () => {
  const snapshot = {
    time: { current_hours: 21 },
    weather: {
      condition: "Humid Overcast",
    },
    local_pressure_areas: [
      { id: "henderson-field", label: "Henderson Field", kind: "objective", location_id: "HENDERSON_FIELD", objective_id: "o1", pressure_reasons: [] },
    ],
    units: [],
    objectives: [],
  };

  const overlays = buildOperationalOverlayState(snapshot, buildMapScene(snapshot, { width: 1000, height: 620, inset: 60 }));

  assert.equal(overlays.weatherImpact.available, true);
  assert.equal(overlays.weatherImpact.current, "Humid Overcast");
  assert.equal(overlays.weatherImpact.timeState, "Night");
  assert.equal(overlays.weatherImpact.visibility, "Not exposed");
  assert.equal(overlays.weatherImpact.nightOperations, "Not modeled");
  assert.match(overlays.weatherImpact.note, /Night conditions are visible over the current front/i);
  assert.doesNotMatch(overlays.weatherImpact.note, /reduced visibility/i);
});

test("map scene exposes the Lunga underlay only for the Henderson slice", () => {
  const lungaScene = buildMapScene({
    scenario: { id: "lunga_point_slice_1942", name: "Lunga Point 1942 (Vertical Slice)" },
    units: [],
    objectives: [{ id: "o1", name: "Henderson Field", state: "held_allied", side: "ALLIED", x: 0, y: 0 }],
  }, { width: 1000, height: 620, inset: 60 });

  const otherScene = buildMapScene({
    scenario: { id: "inchon_mvp", name: "Inchon MVP" },
    units: [],
    objectives: [{ id: "o2", name: "Inchon", state: "held_allied", side: "ALLIED", x: 0, y: 0 }],
  }, { width: 1000, height: 620, inset: 60 });

  assert.equal(lungaScene.underlay.available, true);
  assert.equal(lungaScene.underlay.id, "lunga_point_henderson");
  assert.match(lungaScene.underlay.label, /Lunga Point \/ Henderson Field/i);
  assert.equal(otherScene.underlay.available, false);
  assert.equal(otherScene.underlay.id, null);
});

test("map camera clamps zoom and keeps the map bounded or centered", () => {
  const scene = buildMapScene({
    units: [{ id: "u1", name: "Alpha Company", side: "ALLIED", kind: "land", x: 4, y: 4 }],
    objectives: [{ id: "o1", name: "Henderson Field", state: "held_allied", side: "ALLIED", x: 4, y: 4 }],
  }, { width: 1000, height: 620, inset: 60 });

  const zoomedOut = clampMapCamera({ zoom: 0.2, offsetX: 0, offsetY: 0 }, scene);
  const zoomedIn = clampMapCamera({ zoom: 3.4, offsetX: 400, offsetY: 300 }, scene);

  assert.equal(zoomedOut.zoom, 0.72);
  assert.equal(zoomedOut.offsetX, 140);
  assert.equal(zoomedOut.offsetY, 86.8);
  assert.equal(zoomedIn.zoom, 1.85);
  assert.equal(zoomedIn.offsetX, 0);
  assert.equal(zoomedIn.offsetY, 0);
});

test("map zoom presentation keeps counters near screen-stable while trimming minor labels", () => {
  const broadView = summarizeMapZoomPresentation(0.78);
  const operationalView = summarizeMapZoomPresentation(1.08);
  const closeView = summarizeMapZoomPresentation(1.55);
  const point = projectMapCameraPoint({ x: 200, y: 100 }, { zoom: 1.2, offsetX: -40, offsetY: 15 });

  assert.equal(broadView.counterScale, 0.98);
  assert.equal(broadView.labelPolicy.zoomTier, "far");
  assert.equal(broadView.showUnitLabels, false);
  assert.equal(broadView.showSiteLabels, false);
  assert.equal(broadView.showAirfieldLabels, false);
  assert.equal(broadView.showAirfieldMarkers, false);
  assert.equal(broadView.showObjectiveState, false);
  assert.equal(broadView.showObjectiveLabels, false);
  assert.equal(broadView.showObjectiveMarkers, false);
  assert.match(broadView.labelPolicy.settlementLabels, /selected and key objective/i);
  assert.equal(operationalView.labelPolicy.zoomTier, "operational");
  assert.equal(operationalView.showObjectiveLabels, false);
  assert.equal(operationalView.showObjectiveMarkers, true);
  assert.equal(operationalView.showAirfieldLabels, false);
  assert.equal(operationalView.showAirfieldMarkers, true);
  assert.equal(closeView.counterScale, 1.12);
  assert.equal(closeView.labelPolicy.zoomTier, "close");
  assert.equal(closeView.showUnitLabels, true);
  assert.equal(closeView.showSiteLabels, true);
  assert.equal(closeView.showAirfieldLabels, true);
  assert.equal(closeView.showAirfieldMarkers, true);
  assert.equal(closeView.showObjectiveState, true);
  assert.equal(closeView.showObjectiveLabels, true);
  assert.equal(closeView.showObjectiveMarkers, true);
  assert.match(closeView.labelPolicy.unitLabels, /visible/i);
  assert.deepEqual(point, { x: 200, y: 135 });
});
