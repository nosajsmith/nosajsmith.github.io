import React from "react";

export default function OverlayToggles({ overlays = [], onToggle }) {
  return (
    <div className="overlay-toggle-bar">
      {overlays.map((overlay) => (
        <button
          className={`overlay-toggle ${overlay.active ? "active" : ""} ${overlay.implemented ? "implemented" : "placeholder"}`}
          key={overlay.key}
          onClick={() => onToggle(overlay.key)}
          type="button"
        >
          <span>{overlay.label}</span>
          <small>{overlay.implemented ? "live" : "shell"}</small>
        </button>
      ))}
    </div>
  );
}
