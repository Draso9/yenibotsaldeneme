"use client";

const primaryProfiles = ["Kendi Listem", "BIST 30", "BIST 100", "ABD Büyük Teknoloji"] as const;

type ScanQuickControlsProps = {
  activeProfile: string;
  launchDisabled?: boolean;
  onChooseProfile: (profile: string) => void;
  onFocusListManager: () => void;
  onLaunchScan: () => void;
};

function profileDescription(profile: (typeof primaryProfiles)[number]): string {
  if (profile === "Kendi Listem") return "Kaydettiğin hisseler";
  if (profile === "BIST 30") return "BIST'in en büyük 30 hissesi";
  if (profile === "BIST 100") return "Geniş BIST 100 evreni";
  return "ABD büyük teknoloji hisseleri";
}

export function ScanQuickControls({
  activeProfile,
  launchDisabled = false,
  onChooseProfile,
  onFocusListManager,
  onLaunchScan,
}: Readonly<ScanQuickControlsProps>) {
  return (
    <section className="scan-command-deck" aria-label="Akıllı Tarama hızlı kontrol">
      <div className="scan-command-copy">
        <p className="eyebrow">TARAMA EVRENİ</p>
        <h1>Ne taramak istiyorsun?</h1>
        <p>Hazır BIST ve ABD teknoloji evrenlerinden birini seç veya kişisel listenle devam et. Seçimin aşağıdaki çalışma alanına anında uygulanır.</p>
      </div>
      <div className="scan-universe-presets" aria-label="Hızlı tarama evrenleri">
        {primaryProfiles.map((profile) => (
          <button
            className={`scan-preset-button${activeProfile === profile ? " active" : ""}`}
            key={profile}
            type="button"
            onClick={() => onChooseProfile(profile)}
          >
            <strong>{profile}</strong>
            <span>{profileDescription(profile)}</span>
          </button>
        ))}
      </div>
      <div className="scan-command-actions">
        <button className="scan-list-manager" type="button" onClick={onFocusListManager}>＋ Hisse / şirket ekle</button>
        <button className="scan-primary-action" type="button" disabled={launchDisabled} onClick={onLaunchScan}>Taramayı Başlat →</button>
      </div>
    </section>
  );
}
