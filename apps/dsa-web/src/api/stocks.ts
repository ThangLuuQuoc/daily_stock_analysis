import apiClient from './index';

export type ExtractItem = {
  code?: string | null;
  name?: string | null;
  confidence: string;
};

export type ExtractFromImageResponse = {
  codes: string[];
  items?: ExtractItem[];
  rawText?: string;
};

export const stocksApi = {
  async extractFromImage(file: File): Promise<ExtractFromImageResponse> {
    const formData = new FormData();
    formData.append('file', file);

    const headers: { [key: string]: string | undefined } = { 'Content-Type': undefined };
    const response = await apiClient.post(
      '/api/v1/stocks/extract-from-image',
      formData,
      {
        headers,
        timeout: 60000, // Vision API can be slow; 60s
      },
    );

    const data = response.data as { codes?: string[]; items?: ExtractItem[]; raw_text?: string };
    return {
      codes: data.codes ?? [],
      items: data.items,
      rawText: data.raw_text,
    };
  },

  async parseImport(file?: File, text?: string): Promise<ExtractFromImageResponse> {
    if (file) {
      const formData = new FormData();
      formData.append('file', file);
      const headers: { [key: string]: string | undefined } = { 'Content-Type': undefined };
      const response = await apiClient.post('/api/v1/stocks/parse-import', formData, { headers });
      const data = response.data as { codes?: string[]; items?: ExtractItem[] };
      return { codes: data.codes ?? [], items: data.items };
    }
    if (text) {
      const response = await apiClient.post('/api/v1/stocks/parse-import', { text });
      const data = response.data as { codes?: string[]; items?: ExtractItem[] };
      return { codes: data.codes ?? [], items: data.items };
    }
    throw new Error('请提供文件或粘贴文本');
  },
};

import type { StockSuggestion } from '../types/stockIndex';

/**
 * Live stock search via backend (OpenStock for the Vietnamese market).
 * Returns suggestions shaped for the autocomplete dropdown.
 */
export async function searchStocksRemote(q: string): Promise<StockSuggestion[]> {
  const query = q.trim();
  if (!query) return [];
  const response = await apiClient.get('/api/v1/stocks/search', { params: { q: query } });
  const data = response.data as { result?: Array<Record<string, unknown>> };
  const rows = Array.isArray(data.result) ? data.result : [];
  return rows.map((row) => ({
    canonicalCode: String(row.canonicalCode ?? ''),
    displayCode: String(row.displayCode ?? row.canonicalCode ?? ''),
    nameZh: String(row.nameZh ?? ''),
    market: (row.market as StockSuggestion['market']) ?? 'CN',
    matchType: (row.matchType as StockSuggestion['matchType']) ?? 'contains',
    matchField: (row.matchField as StockSuggestion['matchField']) ?? 'name',
    score: typeof row.score === 'number' ? row.score : 0,
  }));
}
