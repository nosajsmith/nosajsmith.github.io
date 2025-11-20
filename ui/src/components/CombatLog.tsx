import React from "react";

type Combat = { attacker:string; defender:string; location:[number,number]; odds:number; result:string; atk_losses:number; def_losses:number };

export default function CombatLog({ combats }: { combats: Combat[] }) {
  if (!combats?.length) return <div className="text-sm opacity-70">No combats yet.</div>;
  return (
    <div className="space-y-2">
      {combats.map((c, i) => (
        <div key={i} className="border rounded-lg p-3 text-sm">
          <div className="font-semibold">{c.attacker} vs {c.defender} @ ({c.location[0]}, {c.location[1]})</div>
          <div>Odds: {c.odds} • Result: {c.result}</div>
          <div>Losses — Atk: {c.atk_losses} | Def: {c.def_losses}</div>
        </div>
      ))}
    </div>
  );
}
