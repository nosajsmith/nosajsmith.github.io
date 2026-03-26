import mockGreaseBoard from "../../data/mockGreaseBoard.js";

function normalizeString(value) {
  return typeof value === "string" ? value.trim() : "";
}

function normalizeList(value) {
  if (!Array.isArray(value)) {
    return [];
  }
  return value
    .map((entry) => normalizeString(entry))
    .filter(Boolean);
}

function normalizeGreaseBoardPayload(raw) {
  if (!raw || typeof raw !== "object") {
    return null;
  }

  const turn = normalizeString(raw.turn);
  const objective = normalizeString(raw.objective);
  const frontStatus = normalizeString(raw.front_status);
  const supplyStatus = normalizeString(raw.supply_status);
  const mainEffort = normalizeString(raw.main_effort);

  if (!turn || !objective || !frontStatus || !supplyStatus || !mainEffort) {
    return null;
  }

  const staffNotes = normalizeString(raw.staff_notes);

  return {
    turn,
    objective,
    front_status: frontStatus,
    supply_status: supplyStatus,
    main_effort: mainEffort,
    orders: normalizeList(raw.orders),
    alerts: normalizeList(raw.alerts),
    staff_notes: staffNotes || undefined,
  };
}

function looksLikeInchon(snapshot) {
  const scenarioId = normalizeString(snapshot?.scenario?.id).toLowerCase();
  const scenarioName = normalizeString(snapshot?.scenario?.name).toLowerCase();
  return scenarioId.includes("inchon") || scenarioName.includes("inchon");
}

export function summarizeGreaseBoard(snapshot) {
  const authoritativePayload = normalizeGreaseBoardPayload(snapshot?.grease_board);
  if (authoritativePayload) {
    return {
      available: true,
      data: authoritativePayload,
      source: "snapshot",
      note: null,
    };
  }

  if (looksLikeInchon(snapshot)) {
    return {
      available: true,
      data: mockGreaseBoard,
      source: "mock",
      note: "Demo grease-board brief until bridge payloads are exposed on the shell path.",
    };
  }

  return {
    available: false,
    data: null,
    source: "unavailable",
    note: "Grease Board is staged for the Inchon vertical slice or future bridge-fed command briefs.",
  };
}
