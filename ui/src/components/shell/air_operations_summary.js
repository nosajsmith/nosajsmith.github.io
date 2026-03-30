import { humanizeToken, inferScenarioPresentation } from "../../lib/view_snapshot.js";

function toNumber(value) {
  return typeof value === "number" && Number.isFinite(value) ? value : null;
}

function average(values) {
  const numbers = values.map(toNumber).filter((value) => value != null);
  if (!numbers.length) {
    return null;
  }
  return numbers.reduce((sum, value) => sum + value, 0) / numbers.length;
}

function unitKind(unit) {
  return String(unit?.kind ?? "").trim().toLowerCase();
}

function unitName(unit) {
  return String(unit?.name ?? unit?.id ?? "Formation").trim() || "Formation";
}

function weatherCondition(snapshot) {
  return typeof snapshot?.weather?.condition === "string" ? snapshot.weather.condition.trim() : null;
}

function localAirfieldIds(snapshot) {
  const localAreaIds = new Set(
    (Array.isArray(snapshot?.local_pressure_areas) ? snapshot.local_pressure_areas : [])
      .map((area) => String(area?.location_id ?? "").trim().toUpperCase())
      .filter(Boolean),
  );

  return (Array.isArray(snapshot?.airfields) ? snapshot.airfields : [])
    .map((field) => String(field?.id ?? "").trim().toUpperCase())
    .filter((id) => localAreaIds.has(id));
}

function airfieldById(snapshot) {
  const fields = Array.isArray(snapshot?.airfields) ? snapshot.airfields : [];
  return new Map(fields.map((field) => [String(field?.id ?? "").trim().toUpperCase(), field]));
}

function airfieldStatus(field) {
  if (!field || typeof field !== "object") {
    return "State not exposed";
  }
  if (field.destroyed === true) {
    return "Destroyed";
  }
  if (field.damage_state) {
    return humanizeToken(field.damage_state);
  }
  if (field.damaged === true) {
    return "Damaged";
  }
  if (field.sortie_active === true) {
    return "Sorties active";
  }
  if (field.sortie_status) {
    return humanizeToken(field.sortie_status);
  }
  if (field.state || field.control_state) {
    return humanizeToken(field.state ?? field.control_state);
  }
  if (typeof field.readiness === "number" && Number.isFinite(field.readiness)) {
    return `${Math.round(field.readiness)} readiness`;
  }
  return "State not exposed";
}

function airUnitRole(unit) {
  const action = String(unit?.inspector?.orders?.action ?? "").trim();
  const status = String(unit?.inspector?.operational_state?.status ?? "").trim();
  const posture = String(unit?.inspector?.operational_state?.posture ?? unit?.posture ?? "").trim();

  if (action) {
    return humanizeToken(action);
  }
  if (status) {
    return humanizeToken(status);
  }
  if (posture) {
    return `${humanizeToken(posture)} posture`;
  }
  if (unit?.unit_type) {
    return humanizeToken(unit.unit_type);
  }
  return "Role not exposed";
}

function airUnitSorties(unit, baseStatus) {
  const lifecycle = String(unit?.inspector?.orders?.lifecycle_state ?? unit?.inspector?.orders?.status ?? "").trim();
  if (lifecycle) {
    return humanizeToken(lifecycle);
  }
  const posture = String(unit?.inspector?.operational_state?.posture ?? "").trim();
  if (posture) {
    return humanizeToken(posture);
  }
  if (baseStatus && baseStatus !== "State not exposed") {
    return baseStatus;
  }
  return "Sortie posture not exposed";
}

function localAreaCue(snapshot, locationIds) {
  const areas = Array.isArray(snapshot?.local_pressure_areas) ? snapshot.local_pressure_areas : [];
  const match = areas.find((area) => locationIds.has(String(area?.location_id ?? "").trim().toUpperCase())) ?? null;
  if (!match) {
    return "";
  }
  const label = String(match?.label ?? "").trim();
  const reason = Array.isArray(match?.pressure_reasons) ? String(match.pressure_reasons[0] ?? "").trim() : "";
  if (label && reason) {
    return `${label} currently reflects ${humanizeToken(reason).toLowerCase()}.`;
  }
  if (label) {
    return `${label} remains the current local air-support axis.`;
  }
  return "";
}

function collectAirUnits(snapshot) {
  const units = Array.isArray(snapshot?.units) ? snapshot.units : [];
  return units.filter((unit) => {
    const kind = unitKind(unit);
    return kind.includes("air") || kind.includes("aviation");
  });
}

function summarizeSortiePosture(units) {
  const postures = units
    .map((unit) => String(unit?.inspector?.operational_state?.posture ?? "").trim())
    .filter(Boolean);
  if (!postures.length) {
    return "Sortie posture not exposed";
  }
  const unique = [...new Set(postures.map((posture) => posture.toUpperCase()))];
  if (unique.length === 1) {
    return humanizeToken(unique[0].toLowerCase());
  }
  return "Mixed posture";
}

export function summarizeLocalAirSupport(snapshot) {
  const presentation = inferScenarioPresentation(snapshot);
  const localFieldIds = localAirfieldIds(snapshot);
  const fields = (Array.isArray(snapshot?.airfields) ? snapshot.airfields : []).filter((field) => localFieldIds.includes(String(field?.id ?? "").trim().toUpperCase()));
  const theaterAirUnits = collectAirUnits(snapshot);
  const localAirUnits = theaterAirUnits.filter((unit) => localFieldIds.includes(String(unit?.location_id ?? "").trim().toUpperCase()));
  const avgReadiness = average(localAirUnits.map((unit) => unit?.readiness));
  const weather = weatherCondition(snapshot);
  const anchorLabel = fields.map((field) => field.name).join(", ");
  const fieldStatus = fields.map((field) => airfieldStatus(field)).find((value) => value && value !== "State not exposed") || "";
  const areaCue = localAreaCue(snapshot, new Set(localFieldIds));

  let availability = "Not exposed";
  if (!fields.length) {
    availability = "Unavailable";
  } else if (localAirUnits.length && avgReadiness != null) {
    availability = avgReadiness >= 65 ? "Available" : avgReadiness >= 50 ? "Limited" : "Unavailable";
  } else if (fieldStatus) {
    availability = "Context exposed";
  }

  const readinessLimit = localAirUnits.filter((unit) => {
    const readiness = toNumber(unit?.readiness);
    return readiness != null && readiness < 60;
  }).length;

  let constraint = "Weather-linked local air-response limits are not exposed on the current shell path.";
  if (readinessLimit) {
    constraint = `${readinessLimit} locally based air formation${readinessLimit === 1 ? " falls" : "s fall"} below 60 readiness.`;
  } else if (weather) {
    constraint = fieldStatus
      ? `Weather ${weather} and ${fieldStatus.toLowerCase()} at ${anchorLabel || "the local airfield"} are the current air-response cues.`
      : `Weather ${weather} is the only currently exposed local air-response cue.`;
  } else if (fieldStatus) {
    constraint = `${anchorLabel || "Local airfield"} currently reports ${fieldStatus.toLowerCase()}.`;
  }

  let supportingFormation = "No locally based air formation is exposed for the active scenario.";
  if (localAirUnits.length) {
    supportingFormation = localAirUnits.map((unit) => unitName(unit)).join(", ");
  } else if (theaterAirUnits.length) {
    supportingFormation = `${theaterAirUnits.length} theater air formation${theaterAirUnits.length === 1 ? "" : "s"} tracked; local assignment not exposed.`;
  }

  let availabilityNote = `Local air-support availability is not exposed beyond current ${presentation.theaterLabel.toLowerCase()} airfield context.`;
  if (!fields.length) {
    availabilityNote = `No local airfield support context is exposed for the current ${presentation.frontLabel.toLowerCase()} picture.`;
  } else if (localAirUnits.length) {
    availabilityNote = `${anchorLabel} anchors the currently exposed local air-support picture.`;
  } else if (anchorLabel) {
    availabilityNote = `${anchorLabel} is present on the current operational axis even though based air formations are not yet exposed.`;
  }

  return {
    available: fields.length > 0,
    availability,
    note: availabilityNote,
    sortiePosture: localAirUnits.length ? summarizeSortiePosture(localAirUnits) : (fieldStatus || "Sortie posture not exposed"),
    constraint: [constraint, areaCue].filter(Boolean).join(" "),
    supportingFormation,
    anchorLabel,
  };
}

export function summarizeAirOperations(snapshot) {
  const airUnits = collectAirUnits(snapshot);
  const airfields = Array.isArray(snapshot?.airfields) ? snapshot.airfields : [];
  const airfieldIndex = airfieldById(snapshot);
  const avgReadiness = average(airUnits.map((unit) => unit?.readiness));
  const avgSupplyDays = average(airUnits.map((unit) => unit?.inspector?.supply?.supply_days_current));
  const lowReadiness = airUnits.filter((unit) => {
    const readiness = toNumber(unit?.readiness);
    return readiness != null && readiness < 60;
  });
  const locWarnings = airUnits.filter((unit) => {
    const state = String(unit?.inspector?.operational_state?.loc?.state ?? "").trim().toLowerCase();
    return state === "threatened" || state === "broken";
  });
  const condition = weatherCondition(snapshot);

  const concerns = [];
  if (condition) {
    concerns.push(`Weather ${condition} is the only currently exposed air-operations environmental cue.`);
  } else {
    concerns.push("Authoritative weather-limited sortie effects are not exposed on the current shell path.");
  }
  if (lowReadiness.length) {
    concerns.push(`${lowReadiness.length} air formations fall below 60 readiness.`);
  }
  if (locWarnings.length) {
    concerns.push(`${locWarnings.length} air formations report threatened or broken LOC status.`);
  }
  if (!airUnits.length) {
    concerns.push("No air formations are exposed in the active scenario snapshot.");
  }

  return {
    overview: {
      formationsTracked: airUnits.length,
      airfieldsTracked: airfields.length,
      readinessAverage: avgReadiness,
      sustainmentAverageDays: avgSupplyDays,
      statusLine: airUnits.length
        ? "Air picture built from currently exposed air-capable unit rows."
        : "The current shell path exposes airfield context, but no dedicated air formations.",
    },
    formations: airUnits.map((unit) => {
      const base = airfieldIndex.get(String(unit?.location_id ?? "").trim().toUpperCase()) ?? null;
      const baseStatus = airfieldStatus(base);
      return {
        id: unit.id,
        name: unitName(unit),
        readiness: unit?.readiness ?? null,
        supply: unit?.inspector?.supply?.supply_days_current ?? null,
        role: airUnitRole(unit),
        sorties: airUnitSorties(unit, baseStatus),
        aircraft: typeof unit?.strength === "number" && Number.isFinite(unit.strength)
          ? `${Math.round(unit.strength)} strength exposed`
          : "Aircraft counts not exposed",
        base: base?.name
          ? `${base.name}${baseStatus && baseStatus !== "State not exposed" ? ` • ${baseStatus}` : ""}`
          : (unit?.location_id ? humanizeToken(unit.location_id) : "Airfield assignment not exposed"),
      };
    }),
    aircraft: {
      status: "Aircraft type counts not exposed",
      detail: "Aircraft by type, serviceability, and maintenance-capable inventory are not exposed on the current shell path.",
    },
    basing: {
      airfields: airfields.map((field) => ({
        id: field.id,
        name: field.name,
        location: [
          field.x != null && field.y != null ? `${field.x}, ${field.y}` : "",
          airfieldStatus(field) !== "State not exposed" ? airfieldStatus(field) : "",
        ].filter(Boolean).join(" • ") || "Coordinates unavailable",
      })),
      detail: airfields.length
        ? `${airfields.length} authored airfield locations are available as basing context.`
        : "No authored airfields are exposed for the active scenario.",
    },
    operations: {
      sorties: airUnits.length
        ? summarizeSortiePosture(airUnits)
        : airfields.map((field) => airfieldStatus(field)).find((value) => value && value !== "State not exposed") || "Sortie counts not exposed",
      tempo: avgSupplyDays != null ? `${avgSupplyDays.toFixed(1)} days sustainment at current tempo.` : "Mission tempo not exposed on current shell path.",
      support: airfields.length
        ? `${airfields.length} airfield${airfields.length === 1 ? "" : "s"} currently anchor the aviation picture.`
        : "Aviation support and maintenance state not exposed",
    },
    concerns,
  };
}
