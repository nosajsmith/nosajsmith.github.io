export type OperationTypeId = "offensive" | "defense" | "withdrawal" | "amphibious" | "air" | "naval" | "logistics";
export type GroundRoleId = "none" | "main_effort" | "support" | "flank" | "screen" | "reserve";
export type AirRoleId = "none" | "air_superiority" | "cas" | "interdiction" | "recon";
export type NavalRoleId = "none" | "shore_support" | "task_force_support";
export type TempoId = "immediate" | "standard" | "night_movement" | "slow_concealed";
export type PlannerCommandIntent = "operation" | "move" | "attack";

export type OperationPlannerState = {
  scenarioId: string | null;
  greaseEnabled: boolean;
  plannerOpen: boolean;
  selectingObjective: boolean;
  operationType: OperationTypeId;
  objectiveId: string | null;
  name: string;
  unitRoles: Record<string, GroundRoleId>;
  airRole: AirRoleId;
  navalRole: NavalRoleId;
  tempo: TempoId;
  approved: boolean;
  commandIntent: PlannerCommandIntent;
  commandSource: "planner" | "map_shortcut";
  seedUnitId: string | null;
  targetHex: { q: number; r: number } | null;
  targetLabel: string | null;
  enemyTargetId: string | null;
};

export type TrackedDemoOperationParticipant = {
  unitId: string;
  name: string;
  roleId: GroundRoleId;
};

export type TrackedDemoOperation = {
  id: string;
  scenarioId: string | null;
  name: string;
  type: OperationTypeId;
  objectiveId: string;
  objectiveName: string;
  leadHq: string | null;
  participants: TrackedDemoOperationParticipant[];
  airRole: AirRoleId;
  navalRole: NavalRoleId;
  tempo: TempoId;
  estimatedPrepHours: number | null;
  approvedAtTurn: number | null;
  approvedAtHours: number | null;
  commandIntent: PlannerCommandIntent;
  source: "planner" | "map_shortcut";
  seedUnitId: string | null;
  targetHex: { q: number; r: number } | null;
  targetLabel: string | null;
  enemyTargetId: string | null;
};

export type FastCommandPreview = {
  available: boolean;
  unitId: string;
  unitName: string;
  commandIntent: PlannerCommandIntent;
  mode: "immediate" | "planner_review";
  legal: boolean;
  targetHex: { q: number; r: number };
  targetLabel: string;
  objectiveId: string | null;
  objectiveName: string | null;
  enemyTargetId: string | null;
  enemyTargetName: string | null;
  route: Array<{ x: number; y: number }>;
  distance: number;
  note: string;
  title: string;
  statusLabel: string;
  previewTone: "move" | "attack" | "review";
};

export type OperationPlannerActions = {
  onToggleGreaseOverlay: () => void;
  onOpenPlanner: () => void;
  onClosePlanner: () => void;
  onBeginObjectiveSelection: () => void;
  onSetOperationType: (operationType: OperationTypeId) => void;
  onSelectObjectiveArea: (objectiveId: string) => void;
  onSetOperationName: (name: string) => void;
  onSetGroundRole: (unitId: string, role: GroundRoleId) => void;
  onSetAirRole: (role: AirRoleId) => void;
  onSetNavalRole: (role: NavalRoleId) => void;
  onSetTempo: (tempo: TempoId) => void;
  onApproveOperation: () => void;
};
