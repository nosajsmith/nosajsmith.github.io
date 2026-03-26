import { MAP_BASEMAP_TOKENS, MAP_SIZE_TOKENS, getMapZoomTier } from "../designTokens.js";

export const MAP_BASEMAP_STYLE_SPEC = Object.freeze({
  far: {
    tileTier: "far",
    showContours: false,
    showContourMajor: true,
    showContourMinor: false,
    showSettlements: true,
    showSettlementNames: false,
    showAirfields: true,
    showCrossings: false,
    showRoads: true,
    showRail: true,
  },
  operational: {
    tileTier: "operational",
    showContours: true,
    showContourMajor: true,
    showContourMinor: false,
    showSettlements: true,
    showSettlementNames: false,
    showAirfields: true,
    showCrossings: true,
    showRoads: true,
    showRail: true,
  },
  close: {
    tileTier: "close",
    showContours: true,
    showContourMajor: true,
    showContourMinor: true,
    showSettlements: true,
    showSettlementNames: true,
    showAirfields: true,
    showCrossings: true,
    showRoads: true,
    showRail: true,
  },
});

function widthForTier(source, tierId) {
  return source[tierId] ?? source.operational;
}

export function resolveBasemapStyle(zoom) {
  const zoomTier = getMapZoomTier(zoom);
  const tierId = zoomTier.id;
  const spec = MAP_BASEMAP_STYLE_SPEC[tierId] || MAP_BASEMAP_STYLE_SPEC.operational;

  return {
    tier: tierId,
    tileTier: spec.tileTier,
    terrainOpacity: MAP_BASEMAP_TOKENS.terrainOpacityByTier[tierId],
    waterFillOpacityFactor: MAP_BASEMAP_TOKENS.waterFillOpacityFactorByTier[tierId],
    coastFillOpacityFactor: MAP_BASEMAP_TOKENS.coastFillOpacityFactorByTier[tierId],
    hypsometricOpacity: MAP_BASEMAP_TOKENS.hypsometricOpacityByTier[tierId],
    reliefOpacity: MAP_BASEMAP_TOKENS.reliefOpacityByTier[tierId],
    reliefShadeMix: MAP_BASEMAP_TOKENS.reliefShadeMixByTier[tierId],
    hydroOpacity: MAP_BASEMAP_TOKENS.hydroOpacityByTier[tierId],
    coastOpacityFactor: MAP_BASEMAP_TOKENS.coastOpacityFactorByTier[tierId],
    coastCasingOpacityFactor: MAP_BASEMAP_TOKENS.coastCasingOpacityFactorByTier[tierId],
    riverCasingOpacityFactor: MAP_BASEMAP_TOKENS.riverCasingOpacityFactorByTier[tierId],
    contourOpacity: MAP_BASEMAP_TOKENS.contourOpacityByTier[tierId],
    transportOpacity: MAP_BASEMAP_TOKENS.transportOpacityByTier[tierId],
    transportCasingOpacityFactor: MAP_BASEMAP_TOKENS.transportCasingOpacityFactorByTier[tierId],
    roadPrimaryOpacityFactor: MAP_BASEMAP_TOKENS.roadPrimaryOpacityFactorByTier[tierId],
    roadSecondaryOpacityFactor: MAP_BASEMAP_TOKENS.roadSecondaryOpacityFactorByTier[tierId],
    railOpacityFactor: MAP_BASEMAP_TOKENS.railOpacityFactorByTier[tierId],
    crossingOpacityFactor: MAP_BASEMAP_TOKENS.crossingOpacityFactorByTier[tierId],
    crossingHaloOpacityFactor: MAP_BASEMAP_TOKENS.crossingHaloOpacityFactorByTier[tierId],
    nodeOpacity: MAP_BASEMAP_TOKENS.nodeOpacityByTier[tierId],
    lineWidthPx: {
      coast: widthForTier(MAP_BASEMAP_TOKENS.lineWidthPx.coast, tierId),
      coastCasing: widthForTier(MAP_BASEMAP_TOKENS.lineWidthPx.coastCasing, tierId),
      riverMajor: widthForTier(MAP_BASEMAP_TOKENS.lineWidthPx.riverMajor, tierId),
      riverMinor: widthForTier(MAP_BASEMAP_TOKENS.lineWidthPx.riverMinor, tierId),
      riverCasing: widthForTier(MAP_BASEMAP_TOKENS.lineWidthPx.riverCasing, tierId),
      roadPrimary: widthForTier(MAP_BASEMAP_TOKENS.lineWidthPx.roadPrimary, tierId),
      roadSecondary: widthForTier(MAP_BASEMAP_TOKENS.lineWidthPx.roadSecondary, tierId),
      roadPrimaryCasing: widthForTier(MAP_BASEMAP_TOKENS.lineWidthPx.roadPrimaryCasing, tierId),
      roadSecondaryCasing: widthForTier(MAP_BASEMAP_TOKENS.lineWidthPx.roadSecondaryCasing, tierId),
      rail: widthForTier(MAP_BASEMAP_TOKENS.lineWidthPx.rail, tierId),
      railCasing: widthForTier(MAP_BASEMAP_TOKENS.lineWidthPx.railCasing, tierId),
      contourMinor: widthForTier(MAP_BASEMAP_TOKENS.lineWidthPx.contourMinor, tierId),
      contourMajor: widthForTier(MAP_BASEMAP_TOKENS.lineWidthPx.contourMajor, tierId),
    },
    markerSizePx: {
      settlement: widthForTier(MAP_BASEMAP_TOKENS.markerSizePx.settlement, tierId),
      airfield: widthForTier(MAP_BASEMAP_TOKENS.markerSizePx.airfield, tierId),
      crossing: widthForTier(MAP_BASEMAP_TOKENS.markerSizePx.crossing, tierId),
    },
    hexOutlinePx: MAP_SIZE_TOKENS.hexOutline.majorPx,
    ...spec,
  };
}
