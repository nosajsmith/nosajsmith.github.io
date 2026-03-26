import { humanizeToken } from "../../lib/view_snapshot.js";

function humanizeOrFallback(value, fallback) {
  const raw = String(value ?? "").trim();
  if (!raw) {
    return fallback;
  }
  return humanizeToken(raw);
}

function normalizeText(value) {
  return String(value ?? "").trim().toLowerCase();
}

function formatValue(value, fallback = "Unavailable") {
  if (value == null || value === "") {
    return fallback;
  }
  return value;
}

function formatPercent(value) {
  return value == null ? "Unavailable" : `${value}%`;
}

function numericValue(value) {
  if (typeof value === "number" && Number.isFinite(value)) {
    return value;
  }
  const match = String(value ?? "").match(/-?\d+(?:\.\d+)?/);
  return match ? Number.parseFloat(match[0]) : null;
}

function formatDays(value) {
  const numeric = numericValue(value);
  return numeric == null ? "Unavailable" : `${numeric.toFixed(1)} days`;
}

function formatSignedDelta(delta, precision = 0, suffix = "") {
  const absolute = Math.abs(delta);
  const rendered = precision > 0 ? absolute.toFixed(precision) : String(Math.round(absolute));
  return `${delta > 0 ? "+" : "-"}${rendered}${suffix}`;
}

function buildCountRow(label, pair, unavailableLabel = "Unavailable") {
  return {
    label,
    onHand: pair?.on_hand ?? null,
    authorized: pair?.authorized ?? null,
    status: pair ? null : unavailableLabel,
  };
}

function buildEquipmentRows(inspector) {
  return [
    buildCountRow("Men", inspector.toe.men),
    buildCountRow("Armor", inspector.toe.tanks),
    buildCountRow("Guns", inspector.toe.guns),
    buildCountRow("Vehicles", inspector.toe.vehicles),
    buildCountRow("Rifles", null, "Not exposed"),
    buildCountRow("MG", null, "Not exposed"),
    buildCountRow("Mortars", null, "Not exposed"),
    buildCountRow("AT", null, "Not exposed"),
  ];
}

function buildAmmoSummary(ammo) {
  const entries = Object.entries(ammo || {});
  if (!entries.length) {
    return "Unavailable";
  }
  return entries
    .sort((left, right) => left[0].localeCompare(right[0]))
    .map(([label, value]) => `${label} ${value}`)
    .join(", ");
}

function buildSupportRows(attachmentsSupport) {
  const attachments = attachmentsSupport.attachments;
  const support = attachmentsSupport.support;
  const detached = attachmentsSupport.detached;
  const detachmentState = attachmentsSupport.detachment_state && typeof attachmentsSupport.detachment_state === "object"
    ? attachmentsSupport.detachment_state
    : null;
  const rows = [];

  if (detachmentState && (detachmentState.detached_count != null || detachmentState.max_detachments != null)) {
    rows.push({
      label: "Detached Companies",
      value: detachmentState.max_detachments != null
        ? `${detachmentState.detached_count ?? 0} / ${detachmentState.max_detachments}`
        : formatValue(detachmentState.detached_count),
    });
  }
  if (detachmentState && detachmentState.remaining_organic_companies != null) {
    rows.push({
      label: "Organic Remaining",
      value: `${detachmentState.remaining_organic_companies} companies`,
    });
  }
  if (detachmentState && detachmentState.remaining_organic_strength_pct != null) {
    rows.push({
      label: "Organic Strength Eq.",
      value: `${detachmentState.remaining_organic_strength_pct}%`,
    });
  }
  if (detachmentState && detachmentState.parent_cohesion_marker) {
    rows.push({
      label: "Parent Status",
      value: detachmentState.parent_cohesion_marker,
    });
  }
  if (detachmentState && Array.isArray(detachmentState.attached_detachments) && detachmentState.attached_detachments.length) {
    rows.push({
      label: "Received Support Detachments",
      value: detachmentState.attached_detachments.map((item) => item.detachment_label || item.name || "Detachment").join(", "),
    });
  }

  rows.push(
    {
      label: "Attached Formations",
      value: Array.isArray(attachments) && attachments.length ? attachments.join(", ") : "Unavailable",
    },
    {
      label: "Supporting Units",
      value: Array.isArray(support) && support.length ? support.join(", ") : "Unavailable",
    },
    {
      label: "Detached Units",
      value: Array.isArray(detached) && detached.length ? detached.join(", ") : "Unavailable",
    },
  );

  return rows;
}

function buildIdentityRows(unit) {
  const typeLabel = unit?.unit_type ? humanizeOrFallback(unit.unit_type, "Unavailable") : humanizeOrFallback(unit?.kind, "Unavailable");
  return [
    { label: "Formation", value: formatValue(unit?.name, "Formation unavailable") },
    { label: "Formation Type", value: typeLabel },
    { label: "Service / Branch", value: humanizeOrFallback(unitVariant(unit), "Unavailable") },
    { label: "Alignment", value: humanizeOrFallback(unit?.side, "Unavailable") },
    { label: "Map Reference", value: formatValue(unit?.id, "Unavailable") },
  ];
}

function buildLocSection(operational) {
  if (!operational?.loc) {
    return {
      id: "loc-status",
      group: "Current Summary",
      title: "Access / LOC",
      variant: "placeholder",
      body: "LOC status is not exposed for this selection on the current shell path.",
      note: null,
    };
  }

  const rows = [
    { label: "Current State", value: formatValue(operational.loc.label, "Unavailable") },
    { label: "Why It Matters", value: formatValue(operational.loc.detail, "No LOC detail exposed") },
  ];

  if (operational.loc.broken_at) {
    rows.push({ label: "Broken At", value: operational.loc.broken_at });
  }

  return {
    id: "loc-status",
    group: "Current Summary",
    title: "Access / LOC",
    variant: "key-list",
    rows,
    note: null,
  };
}

function buildToeStatusRows(operational, toe, orders) {
  return [
    { label: "TO&E Fill", value: formatPercent(toe.toe_pct ?? operational.strength_pct) },
    { label: "Men On Hand", value: toe.men?.on_hand ?? "Unavailable" },
    { label: "Men Authorized", value: toe.men?.authorized ?? "Unavailable" },
    { label: "Formation State", value: humanizeOrFallback(operational.status, "Unavailable") },
    { label: "Current Posture", value: humanizeOrFallback(operational.posture, "Unavailable") },
    { label: "Current Task", value: humanizeOrFallback(orders.action, "Not exposed") },
    { label: "Task Status", value: humanizeOrFallback(orders.lifecycle_state, "Unavailable") },
    { label: "Map Position", value: formatValue(operational.location_status, "Not exposed") },
  ];
}

function buildReplacementQualityRows(replacementQuality) {
  if (!replacementQuality) {
    return [
      { label: "Experience", value: "Unavailable" },
      { label: "Veteran Core", value: "Unavailable" },
      { label: "New Replacements", value: "Unavailable" },
      { label: "Replacement Quality", value: "Unavailable" },
      { label: "Reconstitution", value: "Unavailable" },
      { label: "Combat Cohesion", value: "Unavailable" },
    ];
  }
  return [
    { label: "Experience", value: formatValue(replacementQuality.experience_band ?? replacementQuality.replacement_quality_band) },
    { label: "Veteran Core", value: formatPercent(replacementQuality.veteran_core_pct) },
    { label: "New Replacements", value: formatPercent(replacementQuality.newcomer_pct) },
    { label: "Replacement Quality", value: formatValue(replacementQuality.replacement_quality_band) },
    { label: "Reconstitution", value: formatValue(replacementQuality.reconstitution_state) },
    { label: "Combat Cohesion", value: formatValue(replacementQuality.combat_cohesion_state) },
  ];
}

function buildStateTransition(label, current, previous) {
  const currentValue = String(current ?? "").trim();
  const previousValue = String(previous ?? "").trim();
  if (!currentValue || !previousValue) {
    return null;
  }
  if (currentValue.toLowerCase() === previousValue.toLowerCase()) {
    return null;
  }
  return {
    label,
    value: `${humanizeOrFallback(previousValue, "Unavailable")} -> ${humanizeOrFallback(currentValue, "Unavailable")}`,
  };
}

function buildRelationshipValue(relationship) {
  if (!relationship) {
    return "Unavailable";
  }
  return relationship.name || relationship.id || "Unavailable";
}

function buildSubordinateValue(subordinates) {
  return Array.isArray(subordinates) && subordinates.length
    ? subordinates.map((item) => item.name || item.id || "Unknown").join(", ")
    : "None listed";
}

function buildCommanderService(unit) {
  const side = humanizeOrFallback(unit?.side, "Service");
  switch (unitVariant(unit)) {
    case "air":
      return `${side} Air Forces`;
    case "naval":
      return `${side} Naval Forces`;
    case "logistics":
      return `${side} Service and Support`;
    default:
      return `${side} Ground Forces`;
  }
}

function buildCommanderIdentity(name) {
  if (typeof name !== "string") {
    return { rank: "Rank unavailable", name: "Commander not exposed" };
  }
  const trimmed = name.trim();
  if (!trimmed) {
    return { rank: "Rank unavailable", name: "Commander not exposed" };
  }

  const tokens = trimmed.split(/\s+/);
  const rankTokens = [];
  let index = 0;
  while (index < tokens.length && /\.$/.test(tokens[index])) {
    rankTokens.push(tokens[index]);
    index += 1;
  }

  return {
    rank: rankTokens.length ? rankTokens.join(" ") : "Rank unavailable",
    name: tokens.slice(index).join(" ") || trimmed,
  };
}

function buildCommanderPortraitMonogram(name, insigniaCode) {
  if (typeof name === "string") {
    const letters = name
      .trim()
      .split(/\s+/)
      .filter(Boolean)
      .slice(-2)
      .map((part) => part[0]?.toUpperCase() ?? "")
      .join("");
    if (letters) {
      return letters;
    }
  }
  return insigniaCode;
}

function pushCommanderLine(list, value) {
  const line = String(value ?? "").trim();
  if (line && !list.includes(line)) {
    list.push(line);
  }
}

function buildCommanderOperationalRole(operational, orders) {
  const parts = [];

  if (operational?.posture) {
    parts.push(`${humanizeOrFallback(operational.posture, "Unavailable")} posture`);
  }
  if (orders?.action) {
    parts.push(`${humanizeOrFallback(orders.action, "Not exposed")} order`);
  }

  const lifecycle = orders?.lifecycle_state || orders?.status || operational?.status;
  if (lifecycle) {
    parts.push(`${humanizeOrFallback(lifecycle, "Unavailable")} state`);
  }

  return parts.join(" • ") || "Current operational role is not exposed on the shell path.";
}

function buildCommanderTraits(unit, operational, command) {
  const traits = [];
  const posture = normalizeText(operational?.posture);
  const readiness = typeof operational?.readiness === "number" ? operational.readiness : null;
  const fatigue = typeof operational?.fatigue === "number" ? operational.fatigue : null;

  if (command?.commander) {
    pushCommanderLine(traits, "Named commander record present on the current shell path.");
  } else {
    pushCommanderLine(traits, "Commander identity is not yet exposed; profile remains tied to visible formation state.");
  }

  switch (posture) {
    case "defend":
      pushCommanderLine(traits, "Holding the line from a defensive posture.");
      break;
    case "attack":
      pushCommanderLine(traits, "Directing an active attack from the current order state.");
      break;
    case "prepare":
      pushCommanderLine(traits, "Assembling the formation before commitment.");
      break;
    case "reserve":
      pushCommanderLine(traits, "Holding the formation in reserve for local response.");
      break;
    case "screen":
      pushCommanderLine(traits, "Screening the current approach rather than massing for assault.");
      break;
    case "rest":
    case "recover":
      pushCommanderLine(traits, "Keeping the formation in a recovery posture instead of pressing it forward.");
      break;
    default:
      break;
  }

  if (readiness != null && fatigue != null) {
    if (readiness >= 70 && fatigue <= 15) {
      pushCommanderLine(traits, "Formation presents as steady and responsive on current condition.");
    } else if (readiness >= 55 && fatigue <= 25) {
      pushCommanderLine(traits, "Formation remains serviceable, but not fresh.");
    } else if (readiness < 55) {
      pushCommanderLine(traits, "Formation is working from reduced readiness.");
    }
  }

  switch (unitVariant(unit)) {
    case "air":
      pushCommanderLine(traits, "Balancing readiness and sortie posture for air operations.");
      break;
    case "naval":
      pushCommanderLine(traits, "Managing mission posture and endurance at sea.");
      break;
    case "logistics":
      pushCommanderLine(traits, "Focused on sustainment continuity rather than direct combat.");
      break;
    default:
      break;
  }

  return traits.slice(0, 3);
}

function buildCommanderCautions(operational, supply) {
  const cautions = [];
  const locState = normalizeText(operational?.loc?.state);

  if (locState === "broken") {
    pushCommanderLine(cautions, "LOC is broken on the current shell path.");
  } else if (locState === "threatened") {
    pushCommanderLine(cautions, "LOC is threatened and could constrain command freedom.");
  }

  if (typeof operational?.fatigue === "number" && operational.fatigue > 25) {
    pushCommanderLine(cautions, "Formation fatigue is elevated.");
  }
  if (typeof operational?.readiness === "number" && operational.readiness < 55) {
    pushCommanderLine(cautions, "Current readiness leaves little margin for abrupt retasking.");
  }
  if (typeof supply?.supply_pct === "number" && supply.supply_pct < 60) {
    pushCommanderLine(cautions, "Supply margin is tight on the current shell path.");
  }
  if (typeof operational?.morale === "number" && operational.morale < 50) {
    pushCommanderLine(cautions, "Morale is below a steady operating standard.");
  }
  if (typeof operational?.cohesion === "number" && operational.cohesion < 50) {
    pushCommanderLine(cautions, "Cohesion is degraded across the formation.");
  }

  if (!cautions.length) {
    pushCommanderLine(cautions, "No commander-specific caution record is exposed; current cautions are limited to visible formation state.");
  }

  return cautions.slice(0, 3);
}

function buildCommanderScreen(unit, command, operational, orders, supply) {
  const side = String(unit?.side ?? "").trim().toUpperCase();
  const insigniaCode = side === "ALLIED" ? "US" : side === "AXIS" ? "IJ" : "HQ";
  const identity = buildCommanderIdentity(command?.commander);
  const commanderName = identity.name;
  const formationName = formatValue(unit?.name, "Formation unavailable");
  const superiorName = buildRelationshipValue(command?.superior);
  const nextSuperiorName = buildRelationshipValue(command?.next_superior);
  const assignment = unit?.name ? `Formation commander, ${unit.name}` : "Command assignment unavailable";
  const commandContext = command?.hq_unit_id
    ? `Headquarters record: ${command.hq_unit_id}`
    : nextSuperiorName !== "Unavailable"
      ? `Next superior: ${nextSuperiorName}`
      : "Command chain context unavailable";

  return {
    portraitLabel: command?.commander ? `Placeholder portrait for ${commanderName}` : "Commander portrait placeholder",
    portraitMonogram: buildCommanderPortraitMonogram(command?.commander, insigniaCode),
    insigniaCode,
    rank: identity.rank,
    name: commanderName,
    service: buildCommanderService(unit),
    assignment,
    formation: formationName,
    superiorHq: superiorName,
    operationalRole: buildCommanderOperationalRole(operational, orders),
    commandContext,
    profileScope: command?.commander
      ? "Named commander identity is authoritative here. Traits and cautions below remain approved demo UI presentation derived from current formation state until full commander records are exposed."
      : "Commander identity, biography, and enduring traits are not exposed. This dossier stays on approved demo UI presentation derived from current formation state only.",
    traits: buildCommanderTraits(unit, operational, command),
    cautions: buildCommanderCautions(operational, supply),
    notes: command?.commander
      ? "Biography, service history, and personal dossier notes are not exposed in the current read model."
      : "Portrait, biography, rank, and personal dossier notes remain unavailable until commander records are exposed to the shell.",
  };
}

function normalizeInspector(unit) {
  const raw = unit && typeof unit === "object" && unit.inspector && typeof unit.inspector === "object" ? unit.inspector : {};
  const operational = raw.operational_state && typeof raw.operational_state === "object" ? raw.operational_state : {};
  const toe = raw.toe && typeof raw.toe === "object" ? raw.toe : {};
  const supply = raw.supply && typeof raw.supply === "object" ? raw.supply : {};
  const movement = raw.movement && typeof raw.movement === "object" ? raw.movement : {};
  const orders = raw.orders && typeof raw.orders === "object" ? raw.orders : {};
  const command = raw.command && typeof raw.command === "object" ? raw.command : {};
  const attachmentsSupport = raw.attachments_support && typeof raw.attachments_support === "object" ? raw.attachments_support : {};
  const replacementQuality = raw.replacement_quality && typeof raw.replacement_quality === "object" ? raw.replacement_quality : {};
  const branchSpecific = raw.branch_specific && typeof raw.branch_specific === "object" ? raw.branch_specific : {};

  return {
    operational_state: {
      strength_pct: operational.strength_pct ?? unit?.strength ?? null,
      readiness: operational.readiness ?? unit?.readiness ?? null,
      readiness_band: operational.readiness_band ?? unit?.readiness_band ?? null,
      fatigue: operational.fatigue ?? null,
      fatigue_trend: operational.fatigue_trend ?? null,
      morale: operational.morale ?? unit?.morale ?? null,
      morale_band: operational.morale_band ?? unit?.morale_band ?? null,
      cohesion: operational.cohesion ?? null,
      posture: operational.posture ?? null,
      status: operational.status ?? unit?.status ?? null,
      location_status: operational.location_status ?? null,
      loc: operational.loc && typeof operational.loc === "object"
        ? {
            state: operational.loc.state ?? "unavailable",
            label: operational.loc.label ?? "LOC Unavailable",
            detail: operational.loc.detail ?? "LOC state unavailable",
            broken_at: operational.loc.broken_at ?? null,
          }
        : null,
    },
    toe: {
      toe_pct: toe.toe_pct ?? null,
      men: toe.men ?? null,
      tanks: toe.tanks ?? null,
      guns: toe.guns ?? null,
      vehicles: toe.vehicles ?? null,
      missing_summary: toe.missing_summary ?? null,
    },
    supply: {
      supply_pct: supply.supply_pct ?? null,
      supply_display: supply.supply_display ?? unit?.supply ?? null,
      supply_days_current: supply.supply_days_current ?? null,
      supply_days_defensive: supply.supply_days_defensive ?? null,
      supply_days_resting: supply.supply_days_resting ?? null,
      fuel: supply.fuel ?? null,
      ammo: supply.ammo ?? null,
      rations: supply.rations ?? null,
    },
    movement: {
      remaining: movement.remaining ?? null,
      km_remaining: movement.km_remaining ?? null,
    },
    orders: {
      action: orders.action ?? null,
      status: orders.status ?? null,
      lifecycle_state: orders.lifecycle_state ?? operational.status ?? unit?.status ?? null,
      delay_reason: orders.delay_reason ?? null,
      note: orders.note ?? null,
    },
    replacement_quality: {
      replacement_quality_band: replacementQuality.replacement_quality_band ?? null,
      experience_band: replacementQuality.experience_band ?? null,
      newcomer_pct: replacementQuality.newcomer_pct ?? null,
      veteran_core_pct: replacementQuality.veteran_core_pct ?? null,
      reconstitution_state: replacementQuality.reconstitution_state ?? null,
      combat_cohesion_state: replacementQuality.combat_cohesion_state ?? null,
    },
    command: {
      hq_unit_id: command.hq_unit_id ?? null,
      superior: command.superior ?? null,
      next_superior: command.next_superior ?? null,
      subordinates: Array.isArray(command.subordinates) ? command.subordinates : [],
      commander: command.commander ?? null,
    },
    attachments_support: {
      attachments: Array.isArray(attachmentsSupport.attachments) ? attachmentsSupport.attachments : null,
      support: Array.isArray(attachmentsSupport.support) ? attachmentsSupport.support : null,
      detached: Array.isArray(attachmentsSupport.detached) ? attachmentsSupport.detached : null,
      detachment_state: attachmentsSupport.detachment_state && typeof attachmentsSupport.detachment_state === "object"
        ? attachmentsSupport.detachment_state
        : null,
    },
    branch_specific: {
      artillery: branchSpecific.artillery && typeof branchSpecific.artillery === "object" ? branchSpecific.artillery : null,
    },
  };
}

function unitVariant(unit) {
  const rawKind = String(unit?.kind ?? "").trim().toLowerCase();
  const rawName = String(unit?.name ?? "").trim().toLowerCase();
  if (rawKind.includes("airmobile") || rawKind.includes("helicopter") || rawName.includes("helicopter") || rawName.includes("airmobile")) {
    return "airmobile";
  }
  if (rawKind.includes("air") || rawKind.includes("aviation")) {
    return "air";
  }
  if (rawKind.includes("naval") || rawKind.includes("navy") || rawKind.includes("fleet") || rawKind.includes("task force")) {
    return "naval";
  }
  if (rawKind.includes("logistics") || rawKind.includes("supply") || rawKind.includes("transport")) {
    return "logistics";
  }
  return "ground";
}

function buildGroundSections(inspector, operational, toe, supply, movement, artillery) {
  return [
    {
      id: "operational-state",
      group: "Readiness & Sustainment",
      title: "Readiness / Condition",
      variant: "metric-grid",
      metrics: [
        { label: "TO&E", value: formatPercent(toe.toe_pct ?? operational.strength_pct) },
        { label: "Readiness", value: formatValue(operational.readiness) },
        { label: "Fatigue", value: formatValue(operational.fatigue) },
        { label: "Morale", value: formatValue(operational.morale) },
        { label: "Cohesion", value: formatValue(operational.cohesion) },
        { label: "Status", value: humanizeOrFallback(operational.status, "Unavailable") },
      ],
    },
    {
      id: "equipment",
      group: "Readiness & Sustainment",
      title: "Strength / Equipment",
      variant: "count-table",
      rows: buildEquipmentRows(inspector),
      note: toe.missing_summary || "Weapon-category counts beyond the current equipment table are not exposed on this shell path.",
    },
    {
      id: "supply-state",
      group: "Readiness & Sustainment",
      title: "Sustainment / Mobility",
      variant: "key-list",
      rows: [
        { label: "Supply", value: formatValue(supply.supply_display) },
        { label: "Supply %", value: formatPercent(supply.supply_pct) },
        { label: "Ammo", value: buildAmmoSummary(supply.ammo) },
        { label: "Fuel", value: formatValue(supply.fuel) },
        { label: "Rations", value: formatValue(supply.rations) },
        { label: "Movement Remaining", value: formatValue(movement.remaining) },
        { label: "KM Remaining", value: formatValue(movement.km_remaining) },
        { label: "Current Tempo", value: formatDays(supply.supply_days_current) },
        { label: "Defensive Tempo", value: formatDays(supply.supply_days_defensive) },
        { label: "Resting Tempo", value: formatDays(supply.supply_days_resting) },
      ],
      note: artillery?.fire_policy ? `Fire policy: ${artillery.fire_policy}${artillery.endurance_days != null ? ` • Endurance ${artillery.endurance_days.toFixed(1)} days` : ""}` : null,
    },
  ];
}

function buildAirSections(operational, supply, movement) {
  return [
    {
      id: "air-state",
      group: "Readiness & Sustainment",
      title: "Air Readiness / Condition",
      variant: "metric-grid",
      metrics: [
        { label: "Readiness", value: formatValue(operational.readiness) },
        { label: "Fatigue", value: formatValue(operational.fatigue) },
        { label: "Morale", value: formatValue(operational.morale) },
        { label: "Posture", value: humanizeOrFallback(operational.posture, "Unavailable") },
        { label: "Serviceability", value: "Unavailable" },
        { label: "Sortie Posture", value: "Unavailable" },
      ],
    },
    {
      id: "aircraft-composition",
      group: "Readiness & Sustainment",
      title: "Aircraft / Lift Picture",
      variant: "key-list",
      rows: [
        { label: "Aircraft by Type", value: "Unavailable" },
        { label: "Ready Aircraft", value: "Unavailable" },
        { label: "Reserve Aircraft", value: "Unavailable" },
      ],
      note: "Airframe counts are not exposed on the current shell path.",
    },
    {
      id: "air-support",
      group: "Readiness & Sustainment",
      title: "Support / Mobility",
      variant: "key-list",
      rows: [
        { label: "Fuel", value: formatValue(supply.fuel) },
        { label: "Ammo", value: "Unavailable" },
        { label: "Movement Remaining", value: formatValue(movement.remaining) },
        { label: "KM Remaining", value: formatValue(movement.km_remaining) },
      ],
      note: "Serviceability, sortie generation, and branch-specific air support detail are not exposed on the current shell path.",
    },
  ];
}

function buildNavalSections(operational, supply, movement) {
  return [
    {
      id: "naval-state",
      group: "Readiness & Sustainment",
      title: "Task Force Readiness",
      variant: "metric-grid",
      metrics: [
        { label: "Readiness", value: formatValue(operational.readiness) },
        { label: "Fatigue", value: formatValue(operational.fatigue) },
        { label: "Morale", value: formatValue(operational.morale) },
        { label: "Posture", value: humanizeOrFallback(operational.posture, "Unavailable") },
        { label: "Fuel Endurance", value: formatValue(supply.fuel) },
        { label: "Mission", value: "Unavailable" },
      ],
    },
    {
      id: "task-force-composition",
      group: "Readiness & Sustainment",
      title: "Task Force Composition",
      variant: "key-list",
      rows: [
        { label: "Ships by Class", value: "Unavailable" },
        { label: "Screen", value: "Unavailable" },
        { label: "Heavy Units", value: "Unavailable" },
      ],
      note: "Ship-class and mission detail are not exposed on the current shell path.",
    },
    {
      id: "naval-endurance",
      group: "Readiness & Sustainment",
      title: "Endurance / Mobility",
      variant: "key-list",
      rows: [
        { label: "Supply", value: formatValue(supply.supply_display) },
        { label: "Fuel", value: formatValue(supply.fuel) },
        { label: "Movement Remaining", value: formatValue(movement.remaining) },
        { label: "KM Remaining", value: formatValue(movement.km_remaining) },
      ],
    },
  ];
}

function buildAirmobileSections(operational, toe, supply, movement) {
  return [
    {
      id: "airmobile-state",
      group: "Readiness & Sustainment",
      title: "Airmobile Readiness",
      variant: "metric-grid",
      metrics: [
        { label: "TO&E", value: formatPercent(toe.toe_pct ?? operational.strength_pct) },
        { label: "Readiness", value: formatValue(operational.readiness) },
        { label: "Fatigue", value: formatValue(operational.fatigue) },
        { label: "Morale", value: formatValue(operational.morale) },
        { label: "Lift Readiness", value: "Unavailable" },
        { label: "Posture", value: humanizeOrFallback(operational.posture, "Unavailable") },
      ],
    },
    {
      id: "airmobile-composition",
      group: "Readiness & Sustainment",
      title: "Lift / Support",
      variant: "key-list",
      rows: [
        { label: "Men", value: toe.men ? `${toe.men.on_hand ?? "?"} / ${toe.men.authorized ?? "?"}` : "Unavailable" },
        { label: "Aircraft", value: "Unavailable" },
        { label: "Support Readiness", value: "Unavailable" },
      ],
      note: "Aircraft and lift-package detail are not exposed on the current shell path.",
    },
    {
      id: "airmobile-sustainment",
      group: "Readiness & Sustainment",
      title: "Sustainment / Mobility",
      variant: "key-list",
      rows: [
        { label: "Supply", value: formatValue(supply.supply_display) },
        { label: "Fuel", value: formatValue(supply.fuel) },
        { label: "Movement Remaining", value: formatValue(movement.remaining) },
        { label: "KM Remaining", value: formatValue(movement.km_remaining) },
      ],
    },
  ];
}

function buildLogisticsSections(toe, supply, movement, operational) {
  return [
    {
      id: "logistics-state",
      group: "Readiness & Sustainment",
      title: "Logistics Readiness",
      variant: "metric-grid",
      metrics: [
        { label: "TO&E", value: formatPercent(toe.toe_pct ?? operational.strength_pct) },
        { label: "Readiness", value: formatValue(operational.readiness) },
        { label: "Fatigue", value: formatValue(operational.fatigue) },
        { label: "Supply Reserve", value: formatValue(supply.supply_display) },
        { label: "Fuel", value: formatValue(supply.fuel) },
        { label: "Posture", value: humanizeOrFallback(operational.posture, "Unavailable") },
      ],
    },
    {
      id: "transport-capacity",
      group: "Readiness & Sustainment",
      title: "Transport Capacity",
      variant: "count-table",
      rows: [
        buildCountRow("Men", toe.men),
        buildCountRow("Vehicles", toe.vehicles),
        buildCountRow("Throughput", null, "Not exposed"),
        buildCountRow("Truck Columns", null, "Not exposed"),
      ],
      note: toe.missing_summary || "Throughput and route-capacity detail are not exposed on the current shell path.",
    },
    {
      id: "logistics-movement",
      group: "Readiness & Sustainment",
      title: "Reserve / Mobility",
      variant: "key-list",
      rows: [
        { label: "Supply %", value: formatPercent(supply.supply_pct) },
        { label: "Current Tempo", value: formatDays(supply.supply_days_current) },
        { label: "Movement Remaining", value: formatValue(movement.remaining) },
        { label: "KM Remaining", value: formatValue(movement.km_remaining) },
      ],
    },
  ];
}

function buildVariantSections(unit, inspector, operational, toe, supply, movement, artillery) {
  switch (unitVariant(unit)) {
    case "air":
      return buildAirSections(operational, supply, movement);
    case "naval":
      return buildNavalSections(operational, supply, movement);
    case "airmobile":
      return buildAirmobileSections(operational, toe, supply, movement);
    case "logistics":
      return buildLogisticsSections(toe, supply, movement, operational);
    default:
      return buildGroundSections(inspector, operational, toe, supply, movement, artillery);
  }
}

function pushNumericDelta(rows, label, current, previous, options = {}) {
  const currentValue = numericValue(current);
  const previousValue = numericValue(previous);
  if (currentValue == null || previousValue == null) {
    return null;
  }

  const precision = typeof options.precision === "number" ? options.precision : 0;
  const threshold = typeof options.threshold === "number" ? options.threshold : (precision > 0 ? 0.05 : 0.5);
  const delta = currentValue - previousValue;
  if (Math.abs(delta) < threshold) {
    return null;
  }

  rows.push({
    label,
    value: formatSignedDelta(delta, precision, options.suffix ?? ""),
  });
  return delta;
}

function buildRecoveryAssessment(deltas, currentReplacementQuality, previousReplacementQuality) {
  if (deltas.men != null && deltas.men > 0 && ((deltas.veteranCore ?? 0) < 0 || (deltas.newcomers ?? 0) > 0)) {
    return "Strength is recovering, but veteran cadre is thinning and newcomer share is rising.";
  }
  if (deltas.men != null && deltas.men < 0) {
    return "Recent losses remain visible relative to the previous snapshot.";
  }
  if ((deltas.readiness ?? 0) > 0 && (deltas.fatigue ?? 0) < 0) {
    return "Readiness is improving while fatigue eases relative to the previous snapshot.";
  }
  if ((deltas.readiness ?? 0) < 0 || (deltas.morale ?? 0) < 0 || (deltas.cohesion ?? 0) < 0 || (deltas.fatigue ?? 0) > 0) {
    return "Formation quality has slipped relative to the previous snapshot.";
  }
  if (String(currentReplacementQuality?.reconstitution_state ?? "").trim()
    && String(previousReplacementQuality?.reconstitution_state ?? "").trim()
    && String(currentReplacementQuality.reconstitution_state).trim().toLowerCase()
      !== String(previousReplacementQuality.reconstitution_state).trim().toLowerCase()) {
    return "Reconstitution state has shifted on the current shell path.";
  }
  return "Only currently exposed fields are compared here; no deep archival history is implied.";
}

function buildRecentChangeSection(inspector, previousUnit, previousSnapshotLabel) {
  const sourceLabel = previousSnapshotLabel ? `Compared with ${previousSnapshotLabel}.` : "Compared with the previous snapshot captured in this session.";
  if (!previousUnit) {
    return {
      id: "recent-change",
      group: "Recovery & Support",
      title: "Recent Change",
      variant: "placeholder",
      body: previousSnapshotLabel
        ? `This formation was not visible in ${previousSnapshotLabel}. Recent-change comparison is unavailable.`
        : "Previous snapshot unavailable. Recent-change view will populate after the next authoritative update captured in this session.",
      note: inspector.replacement_quality.reconstitution_state
        ? `Current reconstitution state: ${inspector.replacement_quality.reconstitution_state}.`
        : sourceLabel,
    };
  }

  const previousInspector = normalizeInspector(previousUnit);
  const rows = [];
  const deltas = {
    men: null,
    supply: null,
    readiness: null,
    fatigue: null,
    morale: null,
    cohesion: null,
    veteranCore: null,
    newcomers: null,
  };

  deltas.men = pushNumericDelta(rows, "Men", inspector.toe.men?.on_hand, previousInspector.toe.men?.on_hand);
  deltas.supply = pushNumericDelta(
    rows,
    "Supply",
    inspector.supply.supply_days_current ?? inspector.supply.supply_display,
    previousInspector.supply.supply_days_current ?? previousInspector.supply.supply_display,
    { precision: 1, threshold: 0.1, suffix: " days" },
  );
  if (deltas.supply == null) {
    pushNumericDelta(rows, "Supply %", inspector.supply.supply_pct, previousInspector.supply.supply_pct, { suffix: "%" });
  }
  deltas.readiness = pushNumericDelta(rows, "Readiness", inspector.operational_state.readiness, previousInspector.operational_state.readiness);
  deltas.fatigue = pushNumericDelta(rows, "Fatigue", inspector.operational_state.fatigue, previousInspector.operational_state.fatigue);
  deltas.morale = pushNumericDelta(rows, "Morale", inspector.operational_state.morale, previousInspector.operational_state.morale);
  deltas.cohesion = pushNumericDelta(rows, "Cohesion", inspector.operational_state.cohesion, previousInspector.operational_state.cohesion);
  deltas.veteranCore = pushNumericDelta(
    rows,
    "Veteran Core",
    inspector.replacement_quality.veteran_core_pct,
    previousInspector.replacement_quality.veteran_core_pct,
    { suffix: "%" },
  );
  deltas.newcomers = pushNumericDelta(
    rows,
    "New Replacements",
    inspector.replacement_quality.newcomer_pct,
    previousInspector.replacement_quality.newcomer_pct,
    { suffix: "%" },
  );

  const experienceTransition = buildStateTransition(
    "Experience",
    inspector.replacement_quality.experience_band,
    previousInspector.replacement_quality.experience_band,
  );
  if (experienceTransition) {
    rows.push(experienceTransition);
  }

  const replacementQualityTransition = buildStateTransition(
    "Replacement Quality",
    inspector.replacement_quality.replacement_quality_band,
    previousInspector.replacement_quality.replacement_quality_band,
  );
  if (replacementQualityTransition) {
    rows.push(replacementQualityTransition);
  }

  const reconstitutionTransition = buildStateTransition(
    "Reconstitution",
    inspector.replacement_quality.reconstitution_state,
    previousInspector.replacement_quality.reconstitution_state,
  );
  if (reconstitutionTransition) {
    rows.push(reconstitutionTransition);
  }

  if (!rows.length) {
    return {
      id: "recent-change",
      group: "Recovery & Support",
      title: "Recent Change",
      variant: "placeholder",
      body: "No material change from the previous snapshot across currently exposed recovery fields.",
      note: sourceLabel,
    };
  }

  return {
    id: "recent-change",
    group: "Recovery & Support",
    title: "Recent Change",
    variant: "key-list",
    rows,
    note: `${sourceLabel} ${buildRecoveryAssessment(deltas, inspector.replacement_quality, previousInspector.replacement_quality)}`,
  };
}

function buildUnitSummary(operational, supply, orders, command) {
  const commandValue = buildRelationshipValue(command.superior) !== "Unavailable"
    ? buildRelationshipValue(command.superior)
    : formatValue(command.hq_unit_id, "HQ link unavailable");
  const supplyValue = supply.supply_days_current != null
    ? `${supply.supply_days_current.toFixed(1)} days current tempo`
    : supply.supply_display != null
      ? formatValue(supply.supply_display)
      : supply.supply_pct != null
        ? formatPercent(supply.supply_pct)
        : "Supply not exposed";
  const taskingValue = orders.action
    ? humanizeOrFallback(orders.action, "Not exposed")
    : humanizeOrFallback(operational.posture, "Not exposed");

  return {
    title: "Current Summary",
    rows: [
      { label: "Readiness", value: operational.readiness != null ? String(operational.readiness) : "Unavailable" },
      { label: "Supply", value: supplyValue },
      { label: "Command", value: commandValue },
      { label: "Tasking", value: taskingValue },
    ],
    note: orders.note || orders.delay_reason
      ? formatValue(orders.note || orders.delay_reason, "No current tasking note exposed")
      : "Summary is limited to currently exposed readiness, sustainment, command, and tasking rows.",
  };
}

export function summarizeUnitInspector(unit, options = {}) {
  if (!unit) {
    return {
      selected: false,
      header: {
        eyebrow: "Inspector",
        title: "No selection",
        subtitle: "Select a visible unit or map object to review current state.",
        loc: null,
      },
      summary: null,
      sections: [],
    };
  }

  const inspector = normalizeInspector(unit);
  const operational = inspector.operational_state;
  const toe = inspector.toe;
  const supply = inspector.supply;
  const movement = inspector.movement;
  const orders = inspector.orders;
  const replacementQuality = inspector.replacement_quality;
  const command = inspector.command;
  const attachmentsSupport = inspector.attachments_support;
  const artillery = inspector.branch_specific.artillery;
  const commanderScreen = buildCommanderScreen(unit, command, operational, orders, supply);
  const variantSections = buildVariantSections(unit, inspector, operational, toe, supply, movement, artillery);
  const previousUnit = options?.previousUnit ?? null;
  const previousSnapshotLabel = typeof options?.previousSnapshotLabel === "string" && options.previousSnapshotLabel.trim()
    ? options.previousSnapshotLabel.trim()
    : null;
  const recentChangeSection = buildRecentChangeSection(inspector, previousUnit, previousSnapshotLabel);

  return {
    selected: true,
    header: {
      eyebrow: "Inspector",
      title: unit.name || "Unnamed Unit",
      subtitle: `${humanizeOrFallback(unit.side, "Unknown Side")} ${humanizeOrFallback(unit.kind, "Formation")}`,
      loc: operational.loc ?? null,
    },
    summary: buildUnitSummary(operational, supply, orders, command),
    commanderScreen,
    sections: [
      {
        id: "identity",
        group: "Current Summary",
        title: "Formation Summary",
        variant: "key-list",
        rows: buildIdentityRows(unit),
      },
      {
        id: "commander-screen",
        group: "Current Summary",
        title: "Command Lead",
        variant: "commander-link",
        commander: commanderScreen,
        body: "Open the commander screen for the selected formation.",
      },
      buildLocSection(operational),
      {
        id: "toe-current-status",
        group: "Current Summary",
        title: "Readiness / Tasking",
        variant: "key-list",
        rows: buildToeStatusRows(operational, toe, orders),
        note: orders.note || orders.delay_reason
          ? formatValue(orders.note || orders.delay_reason, "No current command note exposed")
          : "Current status uses only exposed order, posture, and TO&E fields.",
      },
      ...variantSections,
      {
        id: "command-chain",
        group: "Command & Control",
        title: "Command / Control",
        variant: "key-list",
        rows: [
          { label: "Superior HQ", value: buildRelationshipValue(command.superior) },
          { label: "Next Higher HQ", value: buildRelationshipValue(command.next_superior) },
          { label: "HQ Reference", value: formatValue(command.hq_unit_id) },
          { label: "Subordinates Visible", value: buildSubordinateValue(command.subordinates) },
          { label: "Named Commander", value: formatValue(command.commander) },
          { label: "Formation State", value: humanizeOrFallback(operational.status, "Unavailable") },
          { label: "Map Position", value: formatValue(operational.location_status) },
          { label: "Readiness Band", value: humanizeOrFallback(operational.readiness_band, "Unavailable") },
          { label: "Morale Band", value: humanizeOrFallback(operational.morale_band, "Unavailable") },
          { label: "Fatigue Trend", value: humanizeOrFallback(operational.fatigue_trend, "Unavailable") },
        ],
      },
      {
        id: "attachments-support",
        group: "Recovery & Support",
        title: "Support / Attachments",
        variant: "key-list",
        rows: buildSupportRows(attachmentsSupport),
        note: "Support attachments remain unavailable unless exposed on the authoritative shell path.",
      },
      recentChangeSection,
      {
        id: "replacement-quality",
        group: "Recovery & Support",
        title: "Experience / Reconstitution",
        variant: "key-list",
        rows: buildReplacementQualityRows(replacementQuality),
        note: replacementQuality.experience_band || replacementQuality.replacement_quality_band
          ? "Formation quality reflects surviving veteran cadre, newcomer share, and currently exposed cohesion/readiness state."
          : "Experience and reconstitution remain unavailable until authoritative personnel-quality data is exposed for the unit.",
      },
    ],
  };
}
