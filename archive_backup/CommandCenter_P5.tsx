import React, { useEffect, useMemo, useState } from "react";
import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Input } from "@/components/ui/input";
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from "@/components/ui/select";
import { Progress } from "@/components/ui/progress";
import { Tabs, TabsList, TabsTrigger, TabsContent } from "@/components/ui/tabs";
import { CloudRain, Gauge, Activity, Bell, Map, Sword, Filter } from "lucide-react";

type Category = "logistics"|"rest"|"combat"|"engineering"|"air"|"navy";
type Rec = { id:string; title:string; detail:string; category:Category; urgency:"low"|"medium"|"high" };

function KPI({label, value, icon}:{label:string; value:number; icon:React.ReactNode}){
  return (<Card className="rounded-2xl shadow-sm">
    <CardHeader className="pb-2 flex flex-row items-center justify-between">
      <CardTitle className="text-sm font-medium text-muted-foreground flex items-center gap-2">{icon}{label}</CardTitle>
      <span className="text-xl font-semibold">{value}%</span>
    </CardHeader>
    <CardContent><Progress value={value} className="h-2"/></CardContent>
  </Card>);
}

export default function CommandCenterP5(){
  const [ws, setWs] = useState<WebSocket|null>(null);
  const [engine, setEngine] = useState<any|null>(null);
  const [alerts, setAlerts] = useState<any[]>([]);
  const [aiOrders, setAiOrders] = useState<any[]>([]);
  const [stance, setStance] = useState<"aggressive"|"balanced"|"cautious">("balanced");
  const [daysPerTurn, setDPT] = useState<1|2|3>(2);
  const [search, setSearch] = useState("");
  const [filter, setFilter] = useState<Category|"all">("all");

  // Demo initial recs
  const recs:Rec[] = [
    { id:"r1", title:"Rotate 24th ID 2/19 RCT", detail:"Fatigue high; schedule stand-down.", category:"rest", urgency:"high" },
    { id:"r2", title:"Bridge repair at Naktong", detail:"Engineer battalion ETA 2 days.", category:"engineering", urgency:"medium" },
    { id:"r3", title:"Optimize trucks: fuel/ammo/cargo", detail:"Shift 10% trucks to ammo.", category:"logistics", urgency:"high" },
  ];

  const filtered = useMemo(()=>recs.filter(r=>(filter==="all"||r.category===filter)&& (r.title+ r.detail).toLowerCase().includes(search.toLowerCase())),[recs,filter,search]);

  useEffect(()=>{
    const s = new WebSocket("ws://localhost:8765");
    s.onmessage = (ev)=>{
      const msg = JSON.parse(ev.data);
      if(msg.type==="snapshot"){
        setEngine(msg.data.engine);
      }
      if(msg.type==="kpi_updated" || msg.type==="phase_changed" || msg.type==="turn_advanced"){
        // request-less update: rely on incremental data carried in event
        if(msg.data.kpis) setEngine((e:any)=>({...e, kpis: msg.data.kpis }));
        if(msg.data.phase) setEngine((e:any)=>({...e, clock:{...e.clock, phase: msg.data.phase}}));
        if(typeof msg.data.turn !== "undefined") setEngine((e:any)=>({...e, clock:{...e.clock, turn_number: msg.data.turn}}));
      }
      if(msg.type==="alert_pushed"){
        setAlerts(a=>[...a, msg.data.alert]);
      }
      if(msg.type==="stance_updated"){
        setStance(msg.data.stance);
      }
      if(msg.type==="days_per_turn"){
        setDPT(msg.data.days);
      }
      if(msg.type==="ai_orders"){
        setAiOrders(msg.data.orders);
      }
    };
    setWs(s);
    return ()=> s.close();
  },[]);

  const send = (cmd:string, payload:any={}) => ws?.send(JSON.stringify({cmd,payload}));

  return (
    <div className="w-full h-full p-4 grid grid-cols-12 gap-4">
      <div className="col-span-12 flex items-center justify-between">
        <div className="flex items-center gap-3">
          <div className="text-2xl font-semibold">MWE Command Center – Phase 5</div>
          {engine && <Badge variant="outline">Turn {engine.clock.turn_number}</Badge>}
          <Badge variant="secondary">{daysPerTurn}-day turns</Badge>
          <Badge variant="outline" className="capitalize">HQ: {stance}</Badge>
        </div>
        <div className="flex items-center gap-2">
          <Select value={stance} onValueChange={(v:any)=>{ setStance(v); send("set_stance",{stance:v}); }}>
            <SelectTrigger className="w-36"><SelectValue placeholder="Stance"/></SelectTrigger>
            <SelectContent>
              <SelectItem value="aggressive">Aggressive</SelectItem>
              <SelectItem value="balanced">Balanced</SelectItem>
              <SelectItem value="cautious">Cautious</SelectItem>
            </SelectContent>
          </Select>
          <Select value={String(daysPerTurn)} onValueChange={(v:any)=>{ const d=Number(v) as 1|2|3; setDPT(d); send("set_days_per_turn",{days:d}); }}>
            <SelectTrigger className="w-28"><SelectValue placeholder="Days/Turn"/></SelectTrigger>
            <SelectContent>
              <SelectItem value="1">1 day</SelectItem>
              <SelectItem value="2">2 days</SelectItem>
              <SelectItem value="3">3 days</SelectItem>
            </SelectContent>
          </Select>
          <Button onClick={()=>send("run")}>Run</Button>
          <Button variant="ghost" onClick={()=>send("pause")}>Pause</Button>
          <Button onClick={()=>send("next_turn")}>Next Turn</Button>
          <Button variant="secondary" onClick={()=>send("plan_orders")}>Plan Orders</Button>
        </div>
      </div>

      {/* KPI Cards */}
      <div className="col-span-12 grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-4 gap-4">
        <KPI label="Supply" value={engine?.kpis?.supply_pct ?? 0} icon={<Gauge className="h-4 w-4"/>} />
        <KPI label="Readiness" value={engine?.kpis?.readiness_pct ?? 0} icon={<Activity className="h-4 w-4"/>} />
        <KPI label="Morale" value={engine?.kpis?.morale_pct ?? 0} icon={<Bell className="h-4 w-4"/>} />
        <KPI label="Weather Impact" value={engine?.kpis?.weather_impact_pct ?? 0} icon={<CloudRain className="h-4 w-4"/>} />
      </div>

      {/* Alerts + Weather */}
      <div className="col-span-12 lg:col-span-8 grid grid-rows-[auto_auto_1fr] gap-4 min-h-[70vh]">
        <Card className="rounded-2xl">
          <CardHeader className="pb-2"><CardTitle className="text-base">Alerts</CardTitle></CardHeader>
          <CardContent>
            <div className="flex flex-col gap-2">
              {alerts.map((a,i)=>(
                <div key={i} className="flex items-center justify-between p-2 rounded-xl border">
                  <div className="flex items-center gap-2">
                    <Badge variant={a.severity==="crit"?"destructive":a.severity==="warn"?"secondary":"outline"} className="uppercase">{a.severity}</Badge>
                    <span>{a.text}</span>
                  </div>
                </div>
              ))}
              {alerts.length===0 && <div className="text-sm text-muted-foreground">No alerts yet.</div>}
            </div>
          </CardContent>
        </Card>

        <Card className="rounded-2xl">
          <CardHeader className="pb-2"><CardTitle className="text-base">Weather & Ground</CardTitle></CardHeader>
          <CardContent>
            <div className="grid grid-cols-2 md:grid-cols-4 gap-3">
              <Stat label="Temp" value={`${engine?.weather?.temp_c ?? 0}°C`} />
              <Stat label="Wind" value={`${engine?.weather?.wind_kph ?? 0} kph`} />
              <Stat label="Precip" value={`${engine?.weather?.precip_mm ?? 0} mm`} />
              <Stat label="Ground" value={engine?.weather?.ground ?? "-"} />
            </div>
            <Tabs defaultValue="forecast" className="mt-4">
              <TabsList>
                <TabsTrigger value="forecast">Forecast vs Actual</TabsTrigger>
                <TabsTrigger value="orders">AI Orders</TabsTrigger>
              </TabsList>
              <TabsContent value="forecast"><p className="text-sm text-muted-foreground">Hook to Weather System 1.0 deviations.</p></TabsContent>
              <TabsContent value="orders"><p className="text-sm">{aiOrders.length} orders planned. Use Map view to visualize arrows.</p></TabsContent>
            </Tabs>
          </CardContent>
        </Card>

        <Card className="rounded-2xl flex-1">
          <CardHeader className="pb-2 flex items-center justify-between">
            <CardTitle className="text-base flex items-center gap-2"><Map className="h-5 w-5"/> Operational Map</CardTitle>
            <div className="flex items-center gap-2">
              <Button variant="outline" onClick={()=>window.open("/map","_blank")}>Open Map</Button>
            </div>
          </CardHeader>
          <CardContent>
            <div className="h-64 rounded-xl border border-dashed grid place-items-center text-muted-foreground">
              <div className="flex flex-col items-center gap-2">
                <Map className="h-6 w-6" />
                <span>Map canvas placeholder — use MapCanvas.tsx for overlay arrows & unit rendering.</span>
              </div>
            </div>
          </CardContent>
        </Card>
      </div>

      {/* Right Rail: Staff Recommendations */}
      <div className="col-span-12 lg:col-span-4">
        <Card className="rounded-2xl h-full flex flex-col">
          <CardHeader className="pb-2"><CardTitle className="text-base flex items-center gap-2"><Sword className="h-5 w-5"/> Staff Recommendations</CardTitle></CardHeader>
          <CardContent className="flex-1 flex flex-col gap-3">
            <div className="flex items-center gap-2">
              <Input placeholder="Search..." value={search} onChange={e=>setSearch(e.target.value)} />
              <Select value={filter} onValueChange={(v:any)=>setFilter(v)}>
                <SelectTrigger className="w-40"><SelectValue placeholder="Filter"/></SelectTrigger>
                <SelectContent>
                  <SelectItem value="all"><div className="flex items-center gap-2"><Filter className="h-4 w-4"/> All</div></SelectItem>
                  <SelectItem value="logistics">Logistics</SelectItem>
                  <SelectItem value="rest">Rest</SelectItem>
                  <SelectItem value="combat">Combat</SelectItem>
                  <SelectItem value="engineering">Engineering</SelectItem>
                  <SelectItem value="air">Air</SelectItem>
                  <SelectItem value="navy">Navy</SelectItem>
                </SelectContent>
              </Select>
            </div>
            <div className="flex-1 overflow-auto rounded-xl border p-2 space-y-2">
              {filtered.map(r=>(
                <div key={r.id} className="p-3 rounded-xl border">
                  <div className="flex items-center justify-between">
                    <div className="font-medium">{r.title}</div>
                    <Badge variant={r.urgency==="high"?"destructive": r.urgency==="medium"?"secondary":"outline"} className="capitalize">
                      {r.urgency==="high"?"⚠️ High": r.urgency==="medium"?"• Medium":"Low"}
                    </Badge>
                  </div>
                  <div className="text-sm text-muted-foreground mt-1">{r.detail}</div>
                  <div className="mt-2 flex items-center gap-2 text-xs">
                    <Badge variant="outline" className="capitalize">{r.category}</Badge>
                  </div>
                  <div className="mt-2 flex gap-2">
                    <Button size="sm" variant="secondary">Accept</Button>
                    <Button size="sm" variant="ghost">Snooze</Button>
                  </div>
                </div>
              ))}
              {filtered.length===0 && <div className="text-sm text-muted-foreground p-4 text-center">No recommendations match your filters.</div>}
            </div>
          </CardContent>
        </Card>
      </div>
    </div>
  );
}

function Stat({label, value}:{label:string; value:string}){
  return <div className="p-3 rounded-xl border flex items-center justify-between"><div className="text-sm text-muted-foreground">{label}</div><div className="font-semibold">{value}</div></div>;
}

function KPI({label, value, icon}:{label:string; value:number; icon:React.ReactNode}){
  return (<Card className="rounded-2xl shadow-sm">
    <CardHeader className="pb-2 flex flex-row items-center justify-between">
      <CardTitle className="text-sm font-medium text-muted-foreground flex items-center gap-2">{icon}{label}</CardTitle>
      <span className="text-xl font-semibold">{value}%</span>
    </CardHeader>
    <CardContent><Progress value={value} className="h-2"/></CardContent>
  </Card>);
}
