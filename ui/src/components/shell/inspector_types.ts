export type InspectorSelectionKind = "unit" | "objective" | "airfield" | "port";

export type InspectorSelection = {
  kind: InspectorSelectionKind;
  id: string;
};
