import type { UiLanguage } from '../i18n/uiText';

const DATE_LOCALES: Record<UiLanguage, string> = {
  zh: 'zh-CN',
  en: 'en-US',
  vi: 'vi-VN',
};

const resolveDateLocale = (language: UiLanguage = 'vi'): string => DATE_LOCALES[language] ?? 'vi-VN';

export const formatDateTime = (value?: string | null, language: UiLanguage = 'vi'): string => {
  if (!value) return '—';
  const date = new Date(value);
  if (Number.isNaN(date.getTime())) return value;

  return new Intl.DateTimeFormat(resolveDateLocale(language), {
    year: 'numeric',
    month: '2-digit',
    day: '2-digit',
    hour: '2-digit',
    minute: '2-digit',
  }).format(date);
};

export const formatDate = (value?: string, language: UiLanguage = 'vi'): string => {
  if (!value) return '—';
  const date = new Date(value);
  if (Number.isNaN(date.getTime())) return value;

  return new Intl.DateTimeFormat(resolveDateLocale(language), {
    year: 'numeric',
    month: '2-digit',
    day: '2-digit',
  }).format(date);
};

export const toDateInputValue = (date: Date): string => {
  const year = date.getFullYear();
  const month = `${date.getMonth() + 1}`.padStart(2, '0');
  const day = `${date.getDate()}`.padStart(2, '0');
  return `${year}-${month}-${day}`;
};

/**
 * Returns the date N days ago as YYYY-MM-DD in Asia/Shanghai timezone.
 * Consistent with getTodayInShanghai() so both ends of the date range
 * are expressed in the same timezone as the backend.
 */
export const getRecentStartDate = (days: number): string => {
  const date = new Date();
  date.setDate(date.getDate() - days);
  return new Intl.DateTimeFormat('en-CA', { timeZone: 'Asia/Shanghai' }).format(date);
};

/**
 * Returns today's date as YYYY-MM-DD in Asia/Shanghai timezone.
 * Use this instead of browser-local date to stay consistent with the backend,
 * which stores and filters timestamps in server local time (Asia/Shanghai).
 */
export const getTodayInShanghai = (): string =>
  new Intl.DateTimeFormat('en-CA', { timeZone: 'Asia/Shanghai' }).format(new Date());

const REPORT_TYPE_LABELS: Record<string, Record<UiLanguage, string>> = {
  simple: { zh: '普通', en: 'Basic', vi: 'Thường' },
  detailed: { zh: '标准', en: 'Standard', vi: 'Chuẩn' },
  full: { zh: '完整', en: 'Full', vi: 'Đầy đủ' },
  brief: { zh: '简版', en: 'Brief', vi: 'Rút gọn' },
  market_review: { zh: '大盘', en: 'Market', vi: 'Toàn thị trường' },
};

export const formatReportType = (value?: string, language: UiLanguage = 'vi'): string => {
  if (!value) return '—';
  const labels = REPORT_TYPE_LABELS[value];
  if (labels) return labels[language];
  return value;
};
