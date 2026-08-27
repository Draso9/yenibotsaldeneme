"use client";

import { useState } from "react";

const primaryProfiles = ["Kendi Listem", "BIST 30", "BIST 100"] as const;

function selectProfile(profile: string, attempt = 0) {
  const select = document.querySelector<HTMLSelectElement>(".scan-profile-label select");
  const optionReady = select && Array.from(select.options).some((option) => option.value === profile);
  if (!select || !optionReady) {
    if (attempt < 20) window.setTimeout(() => selectProfile(profile, attempt + 1), 150);
    return;
  }
  const setter = Object.getOwnPropertyDescriptor(HTMLSelectElement.prototype, "value")?.set;
  setter?.call(select, profile);
  select.dispatchEvent(new Event("change", { bubbles: true }));
  document.getElementById("scan-control")?.scrollIntoView({ behavior: "smooth", block: "start" });
}

export function ScanQuickControls() {
  const [activeProfile, setActiveProfile] = useState<string>("Kendi Listem");

  function chooseProfile(profile: string) {
    setActiveProfile(profile);
    selectProfile(profile);
  }

  function focusListManager() {
    document.getElementById("scan-control")?.scrollIntoView({ behavior: "smooth", block: "start" });
    window.setTimeout(() => document.querySelector<HTMLInputElement>(".symbol-search-form input")?.focus(), 350);
  }

  function launchScan() {
    const button = document.querySelector<HTMLButtonElement>(".scan-launch");
    button?.scrollIntoView({ behavior: "smooth", block: "center" });
    if (button && !button.disabled) button.click();
  }

  return (
    <section className="scan-command-deck" aria-label="Akıllı Tarama hızlı kontrol">
      <div className="scan-command-copy">
        <p className="eyebrow">TARAMA EVRENİ</p>
        <h1>Ne taramak istiyorsun?</h1>
        <p>Hazır BIST evrenlerinden birini seç veya kişisel listenle devam et. Seçimin aşağıdaki çalışma alanına anında uygulanır.</p>
      </div>
      <div className="scan-universe-presets" aria-label="Hızlı tarama evrenleri">
        {primaryProfiles.map((profile) => (
          <button
            className={`scan-preset-button${activeProfile === profile ? " active" : ""}`}
            key={profile}
            type="button"
            onClick={() => chooseProfile(profile)}
          >
            <strong>{profile}</strong>
            <span>{profile === "Kendi Listem" ? "Kaydettiğin hisseler" : profile === "BIST 30" ? "BIST'in en büyük 30 hissesi" : "Geniş BIST 100 evreni"}</span>
          </button>
        ))}
      </div>
      <div className="scan-command-actions">
        <button className="scan-list-manager" type="button" onClick={focusListManager}>＋ Hisse / şirket ekle</button>
        <button className="scan-primary-action" type="button" onClick={launchScan}>Taramayı Başlat →</button>
      </div>
    </section>
  );
}
