// Compatibility export only.
// The live UI entry is `ui/src/main.jsx`, which mounts `App.tsx`.
// Keeping this shim removes App.jsx/App.tsx split-brain if a stale import path survives.
export { default } from "./App.tsx";
