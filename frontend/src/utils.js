export const LANGUAGES = [
  { code: 'en', name: 'English', speech: 'en-IN' },
  { code: 'hi', name: 'हिन्दी', speech: 'hi-IN' },
  { code: 'kn', name: 'ಕನ್ನಡ', speech: 'kn-IN' },
  { code: 'te', name: 'తెలుగు', speech: 'te-IN' },
  { code: 'ta', name: 'தமிழ்', speech: 'ta-IN' },
  { code: 'mr', name: 'मराठी', speech: 'mr-IN' },
  { code: 'bn', name: 'বাংলা', speech: 'bn-IN' },
  { code: 'gu', name: 'ગુજરાતી', speech: 'gu-IN' },
];

export const CATEGORY_COLORS = {
  safe: '#2e9e6a',
  semi_critical: '#e5b53a',
  critical: '#e8833a',
  over_exploited: '#d64545',
  no_data: '#9aa3b2',
};

export const CATEGORY_LABELS = {
  safe: 'Safe',
  semi_critical: 'Semi-critical',
  critical: 'Critical',
  over_exploited: 'Over-exploited',
  no_data: 'No data',
};

// Official CGWB thresholds for the stage of groundwater extraction (%).
export function categoryFor(stage) {
  if (stage === null || stage === undefined || Number.isNaN(stage)) return 'no_data';
  if (stage <= 70) return 'safe';
  if (stage <= 90) return 'semi_critical';
  if (stage <= 100) return 'critical';
  return 'over_exploited';
}

// Light -> dark blue scale for rainfall (0 - 3000 mm).
export function rainfallColor(mm) {
  if (mm === null || mm === undefined) return CATEGORY_COLORS.no_data;
  const t = Math.max(0, Math.min(mm / 3000, 1));
  const r = Math.round(219 - 170 * t);
  const g = Math.round(234 - 130 * t);
  const b = Math.round(254 - 60 * t);
  return `rgb(${r}, ${g}, ${b})`;
}

export function formatNumber(value, digits = 1) {
  if (value === null || value === undefined) return 'n/a';
  return Number(value).toLocaleString('en-IN', { maximumFractionDigits: digits });
}

export function speechLang(code) {
  const found = LANGUAGES.find((l) => l.code === code);
  return found ? found.speech : 'en-IN';
}
