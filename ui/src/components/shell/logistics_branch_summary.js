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

function countPresent(values) {
  return values.filter((value) => {
    if (Array.isArray(value)) {
      return value.length > 0;
    }
    return value != null && value !== "";
  }).length;
}

function unitKind(unit) {
  return String(unit?.kind ?? "").trim().toLowerCase();
}

function unitName(unit) {
  return String(unit?.name ?? unit?.id ?? "Formation").trim() || "Formation";
}

function localAreaIds(snapshot) {
  return new Set(
    (Array.isArray(snapshot?.local_pressure_areas) ? snapshot.local_pressure_areas : [])
      .map((area) => String(area?.location_id ?? "").trim().toUpperCase())
      .filter(Boolean),
  );
}

function hasAnySupportLinks(unit) {
  const support = unit?.inspector?.attachments_support;
  return countPresent([support?.attachments, support?.support, support?.detached]) > 0;
}

function localSustainmentUnits(snapshot) {
  const units = Array.isArray(snapshot?.units) ? snapshot.units : [];
  const areaIds = localAreaIds(snapshot);
  if (!areaIds.size) {
    return [];
  }
  return units
    .filter((unit) => String(unit?.side || "").toUpperCase() === "ALLIED")
    .filter((unit) => String(unit?.unit_type || "").toUpperCase() !== "HEADQUARTERS")
    .filter((unit) => unit?.inspector && typeof unit.inspector === "object");
}

function formatTrackedCount(count, noun, emptyLabel) {
  return count ? `${count} ${noun}${count === 1 ? "" : "s"} tracked` : emptyLabel;
}

function localRiskEntry(unit) {
  const supply = unit?.inspector?.supply ?? {};
  const loc = unit?.inspector?.operational_state?.loc ?? {};
  const days = toNumber(supply?.supply_days_current);
  const supplyPct = toNumber(supply?.supply_pct);
  const locState = String(loc?.state ?? "").trim().toLowerCase();
  const parts = [];
  let score = 0;

  if (days != null) {
    parts.push(`${days.toFixed(1)} days`);
    if (days < 2) {
      score += 3;
    } else if (days < 3) {
      score += 2;
    }
  }

  if (supplyPct != null) {
    parts.push(`${Math.round(supplyPct)}% supply`);
    if (supplyPct < 50) {
      score += 3;
    } else if (supplyPct < 70) {
      score += 2;
    }
  }

  if (locState === "broken") {
    score += 3;
    parts.push(String(loc?.detail || "LOC broken"));
  } else if (locState === "threatened") {
    score += 2;
    parts.push(String(loc?.detail || "LOC threatened"));
  }

  if (!parts.length) {
    parts.push("No exposed local sustainment warning");
  }

  return {
    id: String(unit?.id || ""),
    name: unitName(unit),
    score,
    detail: parts.join(" • "),
  };
}

export function summarizeLocalSustainment(snapshot) {
  const units = localSustainmentUnits(snapshot);
  if (!units.length) {
    return {
      available: false,
      status: "Unavailable",
      note: "Local sustainment is unavailable outside the current Henderson/Lunga perimeter slice.",
      resources: [
        { label: "Supply", value: "Not exposed" },
        { label: "Ammo", value: "Not exposed" },
        { label: "Fuel", value: "Not exposed" },
        { label: "Rations", value: "Not exposed" },
        { label: "Support", value: "Not exposed" },
      ],
      atRisk: [],
      concerns: ["No local sustainment warning is exposed on the current shell path."],
    };
  }

  const supplyPcts = units.map((unit) => unit?.inspector?.supply?.supply_pct);
  const supplyDays = units.map((unit) => unit?.inspector?.supply?.supply_days_current);
  const avgSupplyPct = average(supplyPcts);
  const avgSupplyDays = average(supplyDays);
  const lowSupplyPctUnits = units.filter((unit) => {
    const value = toNumber(unit?.inspector?.supply?.supply_pct);
    return value != null && value < 50;
  });
  const strainedSupplyPctUnits = units.filter((unit) => {
    const value = toNumber(unit?.inspector?.supply?.supply_pct);
    return value != null && value < 70;
  });
  const lowSupplyDayUnits = units.filter((unit) => {
    const value = toNumber(unit?.inspector?.supply?.supply_days_current);
    return value != null && value < 3;
  });
  const ammoUnits = units.filter((unit) => {
    const ammo = unit?.inspector?.supply?.ammo;
    return ammo && typeof ammo === "object" && Object.keys(ammo).length > 0;
  });
  const fuelUnits = units.filter((unit) => {
    const fuel = String(unit?.inspector?.supply?.fuel ?? "").trim();
    return !!fuel;
  });
  const rationUnits = units.filter((unit) => {
    const rations = String(unit?.inspector?.supply?.rations ?? "").trim();
    return !!rations;
  });
  const locWarnings = units.filter((unit) => {
    const state = String(unit?.inspector?.operational_state?.loc?.state ?? "").trim().toLowerCase();
    return state === "threatened" || state === "broken";
  });
  const supportUnits = units.filter(hasAnySupportLinks);

  let status = "Unavailable";
  if (lowSupplyPctUnits.length || locWarnings.some((unit) => String(unit?.inspector?.operational_state?.loc?.state ?? "").trim().toLowerCase() === "broken")) {
    status = "Critical";
  } else if (strainedSupplyPctUnits.length || lowSupplyDayUnits.length || locWarnings.length) {
    status = "Strained";
  } else if (avgSupplyPct != null || avgSupplyDays != null) {
    status = "Stable";
  }

  const concerns = [];
  if (lowSupplyPctUnits.length) {
    concerns.push(`${lowSupplyPctUnits.length} local formations fall below 50% supply.`);
  }
  if (lowSupplyDayUnits.length) {
    concerns.push(`${lowSupplyDayUnits.length} local formations fall below 3.0 days current tempo.`);
  }
  if (locWarnings.length) {
    concerns.push(`${locWarnings.length} local formations report threatened or broken LOC status.`);
  }
  if (!concerns.length) {
    concerns.push("No local sustainment warning is exposed beyond current supply and LOC state.");
  }

  return {
    available: true,
    status,
    note: "Built from local Allied unit supply %, current-tempo sustainment days, LOC state, and exposed ammo/fuel/ration rows only.",
    resources: [
      {
        label: "Supply",
        value: avgSupplyDays != null
          ? `${avgSupplyDays.toFixed(1)} days average current tempo`
          : avgSupplyPct != null
            ? `${Math.round(avgSupplyPct)}% average supply`
            : "Not exposed",
      },
      {
        label: "Ammo",
        value: ammoUnits.length ? formatTrackedCount(ammoUnits.length, "formation", "Not exposed") : "Not exposed beyond artillery unit records.",
      },
      {
        label: "Fuel",
        value: fuelUnits.length ? formatTrackedCount(fuelUnits.length, "formation", "Not exposed") : "Not exposed",
      },
      {
        label: "Rations",
        value: rationUnits.length ? formatTrackedCount(rationUnits.length, "formation", "Not exposed") : "Not exposed",
      },
      {
        label: "Support",
        value: supportUnits.length
          ? formatTrackedCount(supportUnits.length, "formation", "Support posture not exposed")
          : locWarnings.length
            ? `${locWarnings.length} formation${locWarnings.length === 1 ? "" : "s"} with LOC warning`
            : "Support posture not exposed",
      },
    ],
    atRisk: units
      .map(localRiskEntry)
      .filter((entry) => entry.score > 0)
      .sort((left, right) => right.score - left.score || left.name.localeCompare(right.name))
      .slice(0, 3),
    concerns,
  };
}

export function summarizeLogisticsBranch(snapshot) {
  const units = Array.isArray(snapshot?.units) ? snapshot.units : [];
  const inspectorUnits = units.filter((unit) => unit?.inspector && typeof unit.inspector === "object");
  const logisticsUnits = inspectorUnits.filter((unit) => {
    const kind = unitKind(unit);
    return kind.includes("logistics") || kind.includes("supply") || kind.includes("transport");
  });

  const supplyPcts = inspectorUnits.map((unit) => unit?.inspector?.supply?.supply_pct);
  const supplyDays = inspectorUnits.map((unit) => unit?.inspector?.supply?.supply_days_current);
  const avgSupplyPct = average(supplyPcts);
  const avgSupplyDays = average(supplyDays);
  const lowSupplyUnits = inspectorUnits.filter((unit) => {
    const days = toNumber(unit?.inspector?.supply?.supply_days_current);
    return days != null && days < 3;
  });
  const locWarnings = inspectorUnits.filter((unit) => {
    const state = String(unit?.inspector?.operational_state?.loc?.state ?? "").trim().toLowerCase();
    return state === "threatened" || state === "broken";
  });
  const vehicleUnits = inspectorUnits.filter((unit) => unit?.inspector?.toe?.vehicles);
  const movementUnits = inspectorUnits.filter((unit) => unit?.inspector?.movement?.remaining != null || unit?.inspector?.movement?.km_remaining != null);
  const fuelUnits = inspectorUnits.filter((unit) => unit?.inspector?.supply?.fuel);
  const rationUnits = inspectorUnits.filter((unit) => unit?.inspector?.supply?.rations);
  const shortfallUnits = inspectorUnits.filter((unit) => unit?.inspector?.toe?.missing_summary);
  const attachmentUnits = inspectorUnits.filter(hasAnySupportLinks);

  const bottlenecks = [];
  if (lowSupplyUnits.length) {
    bottlenecks.push(`${lowSupplyUnits.length} formations below 3.0 days current tempo.`);
  }
  if (locWarnings.length) {
    bottlenecks.push(`${locWarnings.length} formations report threatened or broken LOC status.`);
  }
  if (shortfallUnits.length) {
    bottlenecks.push(`${shortfallUnits.length} formations report TO&E shortfall summaries.`);
  }
  if (!bottlenecks.length) {
    bottlenecks.push("No major sustainment warnings are exposed in the current shell path.");
  }

  return {
    overview: {
      formationsTracked: inspectorUnits.length,
      logisticsFormations: logisticsUnits.length,
      supplyAveragePct: avgSupplyPct,
      supplyAverageDays: avgSupplyDays,
      supportHeadline: avgSupplyDays != null
        ? `${avgSupplyDays.toFixed(1)} days average current tempo across formations with exposed sustainment records.`
        : "Current-tempo sustainment detail is limited on the current shell path.",
      staffLoad: snapshot?.staff?.load ?? null,
      staffSummary: snapshot?.staff?.summary ?? "Staff summary unavailable",
    },
    transport: {
      vehicleFormationCount: vehicleUnits.length,
      movementTrackedCount: movementUnits.length,
      logisticsFormationCount: logisticsUnits.length,
      detail: vehicleUnits.length
        ? `${vehicleUnits.length} formations expose vehicle tables; route-capacity and truck-column throughput remain unexposed.`
        : "Vehicle and movement support detail is not exposed beyond a few unit records.",
    },
    reserves: {
      fuelTrackedCount: fuelUnits.length,
      rationsTrackedCount: rationUnits.length,
      reserveStockStatus: "Reserve stock and depot capacity are not exposed on the current shell path.",
    },
    replacements: {
      status: "Replacement flow not exposed",
      detail: "Replacement pools, return-to-duty flow, and reinforcement schedules are not exposed on the current shell path.",
    },
    support: {
      attachmentTrackedCount: attachmentUnits.length,
      detail: attachmentUnits.length
        ? `${attachmentUnits.length} formations expose attachment or support relationships.`
        : "Attachment and support posture is not exposed beyond isolated unit records.",
    },
    warnings: bottlenecks,
    tables: {
      lowSupply: lowSupplyUnits.slice(0, 6).map((unit) => ({
        name: unitName(unit),
        value: `${unit.inspector.supply.supply_days_current.toFixed(1)} days`,
      })),
      locWarnings: locWarnings.slice(0, 6).map((unit) => ({
        name: unitName(unit),
        value: unit?.inspector?.operational_state?.loc?.detail || "LOC warning",
      })),
      shortfalls: shortfallUnits.slice(0, 6).map((unit) => ({
        name: unitName(unit),
        value: unit.inspector.toe.missing_summary,
      })),
    },
  };
}
