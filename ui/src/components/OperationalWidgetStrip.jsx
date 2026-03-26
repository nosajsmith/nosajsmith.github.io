import React from "react";

export default function OperationalWidgetStrip({ widgets = [] }) {
  return (
    <section className="ops-strip">
      {widgets.map((widget) => (
        <article
          className={`ops-widget ${widget.tone ? `ops-widget--${widget.tone}` : ""}`}
          key={widget.id}
        >
          <div className="ops-widget__topline">
            <div className="ops-widget__label">{widget.label}</div>
            {widget.tag ? <div className="ops-widget__tag">{widget.tag}</div> : null}
          </div>
          <div className="ops-widget__value">{widget.value}</div>
          <div className="ops-widget__detail">{widget.detail}</div>
          {widget.footer ? <div className="ops-widget__footer">{widget.footer}</div> : null}
        </article>
      ))}
    </section>
  );
}
