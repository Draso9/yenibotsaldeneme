export const IZFIN_DESIGN_FOUNDATION = {
  theme: "command-center",
  density: "compact",
  responsive: true,
  tokens: ["iz-bg", "iz-surface", "iz-accent", "iz-positive", "iz-negative", "iz-warning"],
  breakpoints: { tablet: 1100, compact: 860, mobile: 600 },
  navigation: ["Piyasa Merkezi", "Akıllı Tarama", "Projeksiyon", "Performans", "Strateji Lab", "Hesap"],
  sections: ["shell", "overview", "workspace", "market-center", "stock-detail", "account"],
} as const;
