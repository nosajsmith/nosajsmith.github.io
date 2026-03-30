export interface GreaseBoardPayload {
  turn: string;
  objective: string;
  front_status: string;
  supply_status: string;
  main_effort: string;
  orders: string[];
  alerts: string[];
  staff_notes?: string;
}

export interface GreaseBoardSummary {
  available: boolean;
  data: GreaseBoardPayload | null;
  source: "snapshot" | "derived" | "mock" | "unavailable";
  note: string | null;
}
