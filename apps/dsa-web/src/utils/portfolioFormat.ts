import type { UiLanguage } from '../i18n/uiText';
import type {
  PortfolioCashDirection,
  PortfolioCorporateActionType,
  PortfolioFxRefreshResponse,
  PortfolioImportCommitResponse,
  PortfolioImportParseResponse,
  PortfolioPositionItem,
  PortfolioSide,
} from '../types/portfolio';
import { toDateInputValue } from './format';

export type FxRefreshFeedback = {
  tone: 'neutral' | 'success' | 'warning';
  text: string;
};

export type PortfolioAlertVariant = 'info' | 'success' | 'warning' | 'danger';

export function getTodayIso(): string {
  return toDateInputValue(new Date());
}

export function formatMoney(value: number | undefined | null, currency = 'CNY'): string {
  if (value == null || Number.isNaN(value)) return '--';
  return `${currency} ${Number(value).toLocaleString('zh-CN', {
    minimumFractionDigits: 2,
    maximumFractionDigits: 2,
  })}`;
}

export function formatPct(value: number | undefined | null): string {
  if (value == null || Number.isNaN(value)) return '--';
  return `${value.toFixed(2)}%`;
}

export function formatSignedPct(value: number | undefined | null): string {
  if (value == null || Number.isNaN(value)) return '--';
  const sign = value > 0 ? '+' : '';
  return `${sign}${value.toFixed(2)}%`;
}

export function hasPositionPrice(row: PortfolioPositionItem): boolean {
  return row.priceAvailable !== false && row.priceSource !== 'missing';
}

export function formatPositionPrice(row: PortfolioPositionItem): string {
  if (!hasPositionPrice(row)) return '--';
  return row.lastPrice.toFixed(4);
}

export function formatPositionMoney(value: number, row: PortfolioPositionItem): string {
  if (!hasPositionPrice(row)) return '--';
  return formatMoney(value, row.valuationCurrency);
}

const POSITION_PRICE_MISSING: Record<UiLanguage, string> = { zh: '缺价', en: 'No price', vi: 'Thiếu giá' };
const POSITION_PRICE_REALTIME: Record<UiLanguage, string> = { zh: '实时价', en: 'Real-time', vi: 'Giá realtime' };
const POSITION_PRICE_CLOSE: Record<UiLanguage, string> = { zh: '收盘价', en: 'Close price', vi: 'Giá đóng cửa' };
const POSITION_PRICE_UNKNOWN: Record<UiLanguage, string> = { zh: '未知来源', en: 'Unknown source', vi: 'Nguồn không xác định' };

export function getPositionPriceLabel(row: PortfolioPositionItem, language: UiLanguage = 'vi'): string {
  if (!hasPositionPrice(row)) return POSITION_PRICE_MISSING[language];
  if (row.priceSource === 'realtime_quote') {
    return row.priceProvider ? `${POSITION_PRICE_REALTIME[language]} · ${row.priceProvider}` : POSITION_PRICE_REALTIME[language];
  }
  if (row.priceSource === 'history_close') {
    return row.priceStale && row.priceDate ? `${POSITION_PRICE_CLOSE[language]} · ${row.priceDate}` : POSITION_PRICE_CLOSE[language];
  }
  return row.priceSource || POSITION_PRICE_UNKNOWN[language];
}

const SIDE_BUY: Record<UiLanguage, string> = { zh: '买入', en: 'Buy', vi: 'Mua' };
const SIDE_SELL: Record<UiLanguage, string> = { zh: '卖出', en: 'Sell', vi: 'Bán' };

export function formatSideLabel(value: PortfolioSide, language: UiLanguage = 'vi'): string {
  return value === 'buy' ? SIDE_BUY[language] : SIDE_SELL[language];
}

const CASH_IN: Record<UiLanguage, string> = { zh: '流入', en: 'Inflow', vi: 'Nạp tiền' };
const CASH_OUT: Record<UiLanguage, string> = { zh: '流出', en: 'Outflow', vi: 'Rút tiền' };

export function formatCashDirectionLabel(value: PortfolioCashDirection, language: UiLanguage = 'vi'): string {
  return value === 'in' ? CASH_IN[language] : CASH_OUT[language];
}

const CORP_DIVIDEND: Record<UiLanguage, string> = { zh: '现金分红', en: 'Cash dividend', vi: 'Cổ tức tiền mặt' };
const CORP_SPLIT: Record<UiLanguage, string> = { zh: '拆并股调整', en: 'Split adjustment', vi: 'Điều chỉnh tách/gộp cổ phiếu' };

export function formatCorporateActionLabel(value: PortfolioCorporateActionType, language: UiLanguage = 'vi'): string {
  return value === 'cash_dividend' ? CORP_DIVIDEND[language] : CORP_SPLIT[language];
}

const BROKER_DISPLAY_NAMES: Record<string, Record<UiLanguage, string>> = {
  huatai: { zh: '华泰', en: 'Huatai', vi: 'Huatai' },
  citic: { zh: '中信', en: 'CITIC', vi: 'CITIC' },
  cmb: { zh: '招商', en: 'CMB', vi: 'CMB' },
};

export function formatBrokerLabel(value: string, displayName?: string, language: UiLanguage = 'vi'): string {
  if (displayName && displayName.trim()) return `${value}（${displayName.trim()}）`;
  const known = BROKER_DISPLAY_NAMES[value];
  if (known) return `${value}（${known[language]}）`;
  return value;
}

export function buildFxRefreshFeedback(data: PortfolioFxRefreshResponse): FxRefreshFeedback {
  if (data.refreshEnabled === false) {
    return {
      tone: 'neutral',
      text: '汇率在线刷新已被禁用。',
    };
  }

  if (data.pairCount === 0) {
    return {
      tone: 'neutral',
      text: '当前范围无可刷新的汇率对。',
    };
  }

  if (data.updatedCount > 0 && data.staleCount === 0 && data.errorCount === 0) {
    return {
      tone: 'success',
      text: `汇率已刷新，共更新 ${data.updatedCount} 对。`,
    };
  }

  const summary = `更新 ${data.updatedCount} 对，仍过期 ${data.staleCount} 对，失败 ${data.errorCount} 对。`;
  if (data.staleCount > 0) {
    return {
      tone: 'warning',
      text: `已尝试刷新，但仍有部分货币对使用 stale/fallback 汇率。${summary}`,
    };
  }

  return {
    tone: 'warning',
    text: `在线刷新未完全成功。${summary}`,
  };
}

export function getFxRefreshFeedbackVariant(tone: FxRefreshFeedback['tone']): PortfolioAlertVariant {
  if (tone === 'success') return 'success';
  if (tone === 'warning') return 'warning';
  return 'info';
}

export function getCsvParseVariant(result: PortfolioImportParseResponse): PortfolioAlertVariant {
  return result.errorCount > 0 || result.skippedCount > 0 ? 'warning' : 'info';
}

export function getCsvCommitVariant(result: PortfolioImportCommitResponse, isDryRun: boolean): PortfolioAlertVariant {
  if (isDryRun) return 'info';
  return result.failedCount > 0 || result.duplicateCount > 0 ? 'warning' : 'success';
}
