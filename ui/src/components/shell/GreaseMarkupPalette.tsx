import { GREASE_MARKUP_STYLE_OPTIONS, GREASE_MARKUP_TOOL_OPTIONS } from "../../map/greaseMarkup.js";

type GreaseMarkupPaletteProps = {
  activeTool: string | null;
  activeStyle: string;
  selectedId: string | null;
  visible: boolean;
  onToggleVisibility: () => void;
  onSelectTool: (toolId: string | null) => void;
  onSelectStyle: (styleId: string) => void;
  onEraseSelected: () => void;
  onClearAll: () => void;
};

export default function GreaseMarkupPalette({
  activeTool,
  activeStyle,
  selectedId,
  visible,
  onToggleVisibility,
  onSelectTool,
  onSelectStyle,
  onEraseSelected,
  onClearAll,
}: GreaseMarkupPaletteProps) {
  return (
    <div className="shell-greasepalette" aria-label="Planning markup tools">
      <div className="shell-greasepalette__head">
        <div>
          <div className="shell-eyebrow">Planning Markup</div>
          <div className="shell-greasepalette__title">{activeTool ? "Tool armed" : "Map navigation"}</div>
        </div>
        <button
          type="button"
          className={"shell-button shell-button--secondary shell-greasepalette__visibility" + (visible ? " is-active" : "")}
          onClick={onToggleVisibility}
          aria-pressed={visible}
        >
          {visible ? "Visible" : "Hidden"}
        </button>
      </div>

      <div className="shell-greasepalette__toolbar" role="group" aria-label="Planning markup tools">
        {GREASE_MARKUP_TOOL_OPTIONS.map((tool) => {
          const active = tool.id === activeTool;
          return (
            <button
              key={tool.id}
              type="button"
              className={"shell-greasepalette__tool" + (active ? " is-active" : "")}
              onClick={() => onSelectTool(active ? null : tool.id)}
              aria-pressed={active}
              title={tool.label}
            >
              {tool.label}
            </button>
          );
        })}
      </div>

      <div className="shell-greasepalette__styles" role="group" aria-label="Planning markup colors">
        {GREASE_MARKUP_STYLE_OPTIONS.map((style) => (
          <button
            key={style.id}
            type="button"
            className={"shell-greasepalette__style is-" + style.id + (style.id === activeStyle ? " is-active" : "")}
            onClick={() => onSelectStyle(style.id)}
            aria-pressed={style.id === activeStyle}
          >
            <span className="shell-greasepalette__style-chip" aria-hidden="true" />
            <span>{style.label}</span>
          </button>
        ))}
      </div>

      <div className="shell-greasepalette__actions">
        <button
          type="button"
          className="shell-button shell-button--secondary"
          onClick={onEraseSelected}
          disabled={!selectedId}
        >
          Erase Selected
        </button>
        <button
          type="button"
          className="shell-button shell-button--secondary"
          onClick={onClearAll}
        >
          Clear All
        </button>
      </div>
    </div>
  );
}
