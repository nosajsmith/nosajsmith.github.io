/** @type {import("../types/greaseBoard").GreaseBoardPayload} */
const mockGreaseBoard = Object.freeze({
  turn: "TURN 5 — 15 SEP 1950",
  objective: "SEOUL",
  front_status: "CONTESTED",
  supply_status: "STRAINED WEST AXIS",
  main_effort: "SEOUL AXIS",
  orders: [
    "1st Marines advancing toward Seoul",
    "7th Infantry securing beachhead",
    "Naval support active on western flank",
  ],
  alerts: [
    "Supply strain west of Inchon",
    "Fatigue increasing on main axis",
  ],
  staff_notes: "Road network vulnerable west of Inchon. Recommend securing supply route.",
});

export default mockGreaseBoard;
