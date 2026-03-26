type BranchPlaceholderProps = {
  branch: "Air" | "Naval" | "Logistics" | "Intelligence" | "Dashboard" | "Reinforcements";
  onReturnHome: () => void;
};

const BRANCH_COPY: Record<BranchPlaceholderProps["branch"], string> = {
  Air: "Air branch layout is reserved, but branch-specific air data is not exposed on the current shell path.",
  Naval: "Naval branch layout is reserved, but branch-specific naval data is not exposed on the current shell path.",
  Logistics: "Logistics branch layout is reserved, but logistics detail is not exposed here yet.",
  Intelligence: "Intelligence branch layout is reserved, but dedicated intel branch data is not exposed on the current shell path.",
  Dashboard: "Dashboard is a reserved top-level analysis screen and is not implemented on this shell path yet.",
  Reinforcements: "Reinforcements board layout is reserved, but scheduled force-change data is not exposed on the current shell path.",
};

export default function BranchPlaceholder({ branch, onReturnHome }: BranchPlaceholderProps) {
  return (
    <section className="shell-state">
      <div className="shell-state__card">
        <div className="shell-eyebrow">Branch Placeholder</div>
        <h2 className="shell-state__title">{branch}</h2>
        <p className="shell-state__message">{BRANCH_COPY[branch]}</p>
        <div className="shell-state__action">
          <button type="button" className="shell-button" onClick={onReturnHome}>
            Return To Theatre
          </button>
        </div>
      </div>
    </section>
  );
}
