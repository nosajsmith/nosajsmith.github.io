import type { ReactNode } from "react";

type StateScreenProps = {
  title: string;
  message: string;
  action?: ReactNode;
};

export default function StateScreen({ title, message, action }: StateScreenProps) {
  return (
    <section className="shell-state">
      <div className="shell-state__card">
        <div className="shell-eyebrow">Command Post</div>
        <h2 className="shell-state__title">{title}</h2>
        <p className="shell-state__message">{message}</p>
        {action ? <div className="shell-state__action">{action}</div> : null}
      </div>
    </section>
  );
}
