import React from "react";

type Props = {
  send?: (obj:any)=>void;
  files: string[];
  onRefresh: () => void;
  onLoad: (name:string) => void;
  onSave: (name:string) => void;
};

export default function ScenarioPanel({ send, files, onRefresh, onLoad, onSave }: Props) {
  const [name, setName] = React.useState("export");

  return (
    <div className="border rounded-xl p-3 bg-slate-900">
      <div className="text-sm font-semibold mb-2">Scenario Editor</div>

      <div className="flex gap-2 items-center mb-2">
        <button className="px-2 py-1 border rounded" onClick={onRefresh}>List</button>
        <select className="px-2 py-1 bg-slate-800 border rounded grow"
                onChange={(e)=> setName(e.target.value)} value={name}>
          {[name, ...files.filter(f => f !== name)].map(f => <option key={f} value={f}>{f}</option>)}
        </select>
      </div>

      <div className="flex gap-2 mb-2">
        <input className="px-2 py-1 bg-slate-800 border rounded grow"
               value={name} onChange={e=>setName(e.target.value)} placeholder="scenario name (without .json)" />
      </div>

      <div className="flex gap-2">
        <button className="px-2 py-1 border rounded" onClick={() => onLoad(name)}>Load</button>
        <button className="px-2 py-1 border rounded" onClick={() => onSave(name)}>Save</button>
      </div>

      <div className="mt-3 text-xs opacity-70">
        Folder: <code>…\\MWE\\scenarios\\</code><br/>
        Tip: duplicate <code>template.json</code> and edit units/objectives.
      </div>
    </div>
  );
}
