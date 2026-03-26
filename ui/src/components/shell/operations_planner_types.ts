export type OperationTypeId = "offensive" | "defense" | "withdrawal" | "amphibious" | "air" | "naval" | "logistics";
export type GroundRoleId = "none" | "main_effort" | "support" | "flank" | "screen" | "reserve";
export type AirRoleId = "none" | "air_superiority" | "cas" | "interdiction" | "recon";
export type NavalRoleId = "none" | "shore_support" | "task_force_support";
export type TempoId = "immediate" | "standard" | "night_movement" | "slow_concealed";

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
