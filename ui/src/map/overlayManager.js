const BASE_MAP_LAYER_REGISTRY = [
  { id: "basemap", label: "Packaged basemap", group: "terrain", priority: 5, defaultEnabled: true, toggleable: true },
  { id: "historicalUnderlay", label: "Historical underlay", group: "terrain", priority: 10, defaultEnabled: false, toggleable: true },
  { id: "terrainField", label: "Terrain field wash", group: "terrain", priority: 20, defaultEnabled: true, toggleable: false },
  { id: "terrainEmphasis", label: "Terrain emphasis", group: "terrain", priority: 25, defaultEnabled: false, toggleable: true },
  { id: "grid", label: "Hex grid", group: "terrain", priority: 30, defaultEnabled: true, toggleable: true },
  { id: "weatherWash", label: "Weather wash", group: "overlay", priority: 40, defaultEnabled: false, toggleable: true },
  { id: "barriers", label: "Barriers", group: "overlay", priority: 45, defaultEnabled: false, toggleable: true },
  { id: "infrastructure", label: "Infrastructure", group: "overlay", priority: 50, defaultEnabled: false, toggleable: true },
  { id: "supply", label: "Supply", group: "overlay", priority: 60, defaultEnabled: false, toggleable: true },
  { id: "command", label: "Command", group: "overlay", priority: 70, defaultEnabled: false, toggleable: true },
  { id: "frontline", label: "Front / Sectors", group: "overlay", priority: 75, defaultEnabled: false, toggleable: true },
  { id: "movementIntent", label: "Movement / Orders", group: "overlay", priority: 78, defaultEnabled: false, toggleable: true },
  { id: "artillery", label: "Artillery", group: "overlay", priority: 80, defaultEnabled: false, toggleable: true },
  { id: "fogIntel", label: "Fog / Intel", group: "overlay", priority: 90, defaultEnabled: false, toggleable: true },
  { id: "greasePlanning", label: "Planning markup", group: "planning", priority: 100, defaultEnabled: false, toggleable: true },
  { id: "objectives", label: "Objectives", group: "markers", priority: 110, defaultEnabled: true, toggleable: true },
  { id: "units", label: "Unit counters", group: "markers", priority: 120, defaultEnabled: true, toggleable: false },
  { id: "labels", label: "Labels and leader lines", group: "labels", priority: 130, defaultEnabled: true, toggleable: false },
  { id: "ui", label: "Map UI chrome", group: "ui", priority: 140, defaultEnabled: true, toggleable: false },
];

function normalizeLayer(layer) {
  return {
    ...layer,
    group: layer.group || "overlay",
    priority: Number.isFinite(Number(layer.priority)) ? Number(layer.priority) : 100,
    defaultEnabled: layer.defaultEnabled !== false,
    toggleable: layer.toggleable !== false,
  };
}

export const MAP_LAYER_REGISTRY = Object.freeze(
  [...BASE_MAP_LAYER_REGISTRY]
    .map(normalizeLayer)
    .sort((left, right) => left.priority - right.priority),
);

function layerById(registry, id) {
  return registry.find((layer) => layer.id === id) || null;
}

export function buildMapOverlayManager(options = {}) {
  const extraLayers = Array.isArray(options.layers) ? options.layers.map(normalizeLayer) : [];
  const registry = [...MAP_LAYER_REGISTRY, ...extraLayers].sort((left, right) => left.priority - right.priority);
  const toggles = {};

  for (const layer of registry) {
    toggles[layer.id] = Boolean(
      Object.prototype.hasOwnProperty.call(options.toggles || {}, layer.id)
        ? options.toggles[layer.id]
        : layer.defaultEnabled,
    );
  }

  return {
    registry,
    toggles,
    orderedLayers: registry.filter((layer) => toggles[layer.id]),
  };
}

export function isMapLayerEnabled(manager, layerId) {
  return Boolean(manager?.toggles?.[layerId]);
}

export function toggleMapLayer(currentToggles, layerId, registry = MAP_LAYER_REGISTRY) {
  const layer = layerById(registry, layerId);
  const current = currentToggles && Object.prototype.hasOwnProperty.call(currentToggles, layerId)
    ? currentToggles[layerId]
    : layer?.defaultEnabled;

  return {
    ...(currentToggles || {}),
    [layerId]: !current,
  };
}
