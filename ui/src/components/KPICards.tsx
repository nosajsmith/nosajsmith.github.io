import React from "react";

export default function KPICards({ kpis, clock }: { kpis?: any; clock?: any }) {
  const Item = ({ label, value }: { label: string; value: any }) => (
    <div className="border rounded-lg p-3 shadow-sm">
      <div className="text-xs opacity-70">{label}</div>
      <div className="text-2xl font-semibold">{value ?? "—"}</div>
    </div>
  );

  return (
    <div className="grid grid-cols-2 md:grid-cols-4 gap-3">
      <Item label="Turn" value={clock?.turn_number} />
      <Item label="Supply %" value={kpis?.supply_pct} />
      <Item label="Readiness %" value={kpis?.readiness_pct} />
      <Item label="Morale %" value={kpis?.morale_pct} />
    </div>
  );
}
