import { categoryFor, formatNumber, rainfallColor, speechLang } from './utils';

test('categoryFor follows CGWB thresholds', () => {
  expect(categoryFor(null)).toBe('no_data');
  expect(categoryFor(70)).toBe('safe');
  expect(categoryFor(70.1)).toBe('semi_critical');
  expect(categoryFor(90)).toBe('semi_critical');
  expect(categoryFor(100)).toBe('critical');
  expect(categoryFor(100.1)).toBe('over_exploited');
});

test('formatNumber handles missing values', () => {
  expect(formatNumber(null)).toBe('n/a');
  expect(formatNumber(1234.56, 0)).toBe('1,235');
});

test('rainfallColor returns a css colour', () => {
  expect(rainfallColor(0)).toMatch(/^rgb\(/);
  expect(rainfallColor(undefined)).toBe('#9aa3b2');
});

test('speechLang falls back to Indian English', () => {
  expect(speechLang('hi')).toBe('hi-IN');
  expect(speechLang('zz')).toBe('en-IN');
});
