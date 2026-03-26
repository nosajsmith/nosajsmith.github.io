type CommunicationMessage = {
  id: string;
  title: string;
  kind: string;
  showKind: boolean;
  summary: string;
  body: string;
  severity: string;
  timeLabel: string;
  senderLabel: string | null;
  insigniaCode: string | null;
  isDemo: boolean;
};

type CommunicationsCenterProps = {
  open: boolean;
  messages: CommunicationMessage[];
  demoExample: CommunicationMessage | null;
  selectedMessageId: string | null;
  onClose: () => void;
  onSelectMessage: (messageId: string) => void;
  onCloseMessage: () => void;
};

function severityLabel(severity: string): string {
  return severity === "warning" ? "Warning" : "Info";
}

export default function CommunicationsCenter({
  open,
  messages,
  demoExample,
  selectedMessageId,
  onClose,
  onSelectMessage,
  onCloseMessage,
}: CommunicationsCenterProps) {
  if (!open) {
    return null;
  }

  const selectedMessage = messages.find((message) => message.id === selectedMessageId) ?? (demoExample?.id === selectedMessageId ? demoExample : null);

  return (
    <div className="shell-commcenter" role="dialog" aria-modal="true" aria-label="Communications Center">
      <div className="shell-commcenter__scrim" onClick={onClose} />

      <section className="shell-commcenter__panel">
        <div className="shell-commcenter__head">
          <div>
            <div className="shell-eyebrow">Communications Center</div>
            <h2 className="shell-panel__title">Operational Message Log</h2>
          </div>
          <button type="button" className="shell-button shell-button--secondary" onClick={onClose}>
            Close
          </button>
        </div>

        <div className="shell-commcenter__body">
          {demoExample ? (
            <button
              type="button"
              className={"shell-commcenter__message shell-commcenter__message--demo" + (demoExample.id === selectedMessageId ? " is-selected" : "")}
              onClick={() => onSelectMessage(demoExample.id)}
            >
              <div className="shell-commcenter__message-head">
                <div className="shell-commcenter__message-identity">
                  <span className="shell-commcenter__insignia" aria-hidden="true">
                    {demoExample.insigniaCode}
                  </span>
                  <div className="shell-commcenter__message-copy">
                    {demoExample.senderLabel ? <div className="shell-commcenter__message-sender">{demoExample.senderLabel}</div> : null}
                    <div className="shell-commcenter__message-title">{demoExample.title}</div>
                    <div className="shell-commcenter__message-meta">
                      {demoExample.showKind ? <div className="shell-commcenter__message-kind">{demoExample.kind}</div> : null}
                      <div className="shell-commcenter__message-time">{demoExample.timeLabel}</div>
                    </div>
                  </div>
                </div>
                <div className="shell-commcenter__demo-tag">Demo</div>
              </div>
              <div className="shell-commcenter__message-summary">{demoExample.summary}</div>
            </button>
          ) : null}

          {messages.length ? (
            messages.map((message) => (
              <button
                type="button"
                key={message.id}
                className={"shell-commcenter__message" + (message.id === selectedMessageId ? " is-selected" : "")}
                onClick={() => onSelectMessage(message.id)}
              >
                <div className="shell-commcenter__message-head">
                  <div className="shell-commcenter__message-copy">
                    {message.senderLabel ? <div className="shell-commcenter__message-sender">{message.senderLabel}</div> : null}
                    <div className="shell-commcenter__message-title">{message.title}</div>
                    <div className="shell-commcenter__message-meta">
                      {message.showKind ? <div className="shell-commcenter__message-kind">{message.kind}</div> : null}
                      <div className="shell-commcenter__message-time">{message.timeLabel}</div>
                    </div>
                  </div>
                  <div className={"shell-report__severity is-" + message.severity}>{severityLabel(message.severity)}</div>
                </div>
                <div className="shell-commcenter__message-summary">{message.summary}</div>
              </button>
            ))
          ) : (
            <div className="shell-empty">No communications are available in the current snapshot.</div>
          )}
        </div>
      </section>

      {selectedMessage ? (
        <div className="shell-messageview" role="dialog" aria-modal="true" aria-label="Communication detail">
          <div className="shell-messageview__card">
            <div className="shell-messageview__head">
              <div className="shell-messageview__identity">
                {selectedMessage.insigniaCode ? (
                  <span className="shell-messageview__insignia" aria-hidden="true">
                    {selectedMessage.insigniaCode}
                  </span>
                ) : null}
                <div className="shell-messageview__identity-copy">
                  <div className="shell-eyebrow">Message Detail</div>
                  <h3 className="shell-panel__title">{selectedMessage.title}</h3>
                  {selectedMessage.senderLabel ? <div className="shell-messageview__sender">{selectedMessage.senderLabel}</div> : null}
                </div>
              </div>
              <button type="button" className="shell-button shell-button--secondary" onClick={onCloseMessage}>
                Close
              </button>
            </div>

            <div className="shell-messageview__meta">
              {selectedMessage.isDemo ? <span>Frontend demo example</span> : null}
              {selectedMessage.showKind ? <span>{selectedMessage.kind}</span> : null}
              <span>{selectedMessage.timeLabel}</span>
            </div>

            <div className="shell-messageview__body">{selectedMessage.body}</div>
          </div>
        </div>
      ) : null}
    </div>
  );
}
