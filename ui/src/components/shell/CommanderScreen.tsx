type CommanderScreenData = {
  portraitLabel: string;
  portraitMonogram: string;
  insigniaCode: string;
  rank: string;
  name: string;
  service: string;
  assignment: string;
  formation: string;
  superiorHq: string;
  operationalRole: string;
  commandContext: string;
  profileScope: string;
  traits: string[];
  cautions: string[];
  notes: string;
};

type CommanderScreenProps = {
  commander: CommanderScreenData;
  onBack: () => void;
};

export default function CommanderScreen({ commander, onBack }: CommanderScreenProps) {
  return (
    <section className="shell-commander" aria-label="Commander screen">
      <div className="shell-commander__header">
        <button type="button" className="shell-button shell-button--secondary" onClick={onBack}>
          Back to Inspector
        </button>
        <div>
          <div className="shell-eyebrow">Commander Screen</div>
          <h3 className="shell-panel__title shell-panel__title--subscreen">Command Personality and Context</h3>
        </div>
      </div>

      <div className="shell-commander__hero">
        <div className="shell-commander__portrait" aria-label={commander.portraitLabel}>
          <span>{commander.portraitMonogram}</span>
        </div>
        <div className="shell-commander__identity">
          <div className="shell-commander__insignia" aria-label="Formation insignia">
            {commander.insigniaCode}
          </div>
          <div className="shell-commander__rank">{commander.rank}</div>
          <div className="shell-commander__name">{commander.name}</div>
          <div className="shell-commander__service">{commander.service}</div>
          <div className="shell-commander__assignment">{commander.assignment}</div>
        </div>
      </div>

      <div className="shell-commander__grid">
        <div className="shell-commander__panel">
          <span>Current Command</span>
          <strong>{commander.formation}</strong>
          <p>{commander.commandContext}</p>
        </div>
        <div className="shell-commander__panel">
          <span>Superior HQ</span>
          <strong>{commander.superiorHq}</strong>
          <p>Command relationship shown from the active shell read model.</p>
        </div>
        <div className="shell-commander__panel">
          <span>Current Role</span>
          <strong>{commander.operationalRole}</strong>
          <p>Built from the current posture and tracked order lifecycle only.</p>
        </div>
      </div>

      <div className="shell-commander__panel">
        <span>Profile Scope</span>
        <p>{commander.profileScope}</p>
      </div>

      <div className="shell-commander__block">
        <span>Descriptive Traits</span>
        <div className="shell-commander__tags">
          {commander.traits.map((item) => (
            <strong key={item}>{item}</strong>
          ))}
        </div>
      </div>

      <div className="shell-commander__block">
        <span>Cautions and Tendencies</span>
        <div className="shell-commander__tags">
          {commander.cautions.map((item) => (
            <strong key={item}>{item}</strong>
          ))}
        </div>
      </div>

      <div className="shell-commander__panel">
        <span>Notes</span>
        <p>{commander.notes}</p>
      </div>
    </section>
  );
}
