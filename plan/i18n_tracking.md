# i18n — Đánh giá tổng thể & Tracking đa ngôn ngữ

Ngày: 2026-06-25 · Phạm vi: `apps/dsa-web` (frontend) + `src/`, `api/` (backend).
Bối cảnh: deployment thị trường VN; UI đã hỗ trợ `zh`/`en`/`vi`, nhưng **đổi sang English nhiều chỗ vẫn ra tiếng Trung**. Tài liệu này đánh giá kiến trúc và liệt kê các điểm cần xử lý.

---

## 1. Kết luận nhanh

- **Lớp UI-text (frontend) được thiết kế TỐT, dễ thêm ngôn ngữ.** `src/i18n/uiText.ts`: `UI_TEXT: Record<UiLanguage, Record<UiTextKey, string>>`, `UiTextKey = keyof typeof zh`, mỗi ngôn ngữ là `Record<UiTextKey, string>` → **TypeScript ép đủ key**, thêm ngôn ngữ là thao tác type-safe.
- **Vấn đề "vẫn tiếng Trung khi đổi English" KHÔNG nằm ở lớp này**, mà ở **mọi chỗ đi vòng qua nó**:
  1. **Hệ "report language" song song** (`reportLanguage.ts`) chỉ hỗ trợ `zh`/`en`, **mặc định `zh`**, và **nhãn báo cáo bám theo ngôn ngữ của báo cáo đã lưu — không theo UI** → nguyên nhân chính.
  2. **Backend chưa có `vi`** và rò rỉ nhiều chuỗi tiếng Trung user-facing (`股票{code}`, lỗi API, thông báo/email).
  3. **~85 chuỗi tiếng Trung hardcode** ở frontend (không qua `t()`), tập trung ở alerts/portfolio/autocomplete.
  4. Vài chỗ **mặc định về `zh`** + ternary `=== 'zh'` không scale cho 3 ngôn ngữ + date locale khoá `zh-CN` + `stocks.index.json` chỉ có CN.

Quy mô: FE ~85–90 chuỗi/~15 file; BE ~80–90 chuỗi user-facing/~20 file. **Không nơi nào hỗ trợ `vi` cho nội dung báo cáo.**

---

## 2. Kiến trúc i18n hiện tại

| Lớp | Cơ chế | Đánh giá |
|---|---|---|
| **UI text (FE)** | `uiText.ts` `UI_TEXT[lang][key]` + `t()` qua `UiLanguageContext` | ✅ Tốt, type-safe, 3 ngôn ngữ |
| **Report language (FE)** | `reportLanguage.ts` `REPORT_TEXT` (chỉ zh/en) + `getReportText()` | ⚠️ Hệ song song, default zh, không type-link với `UiLanguage` |
| **Report language (BE)** | `src/report_language.py` `SUPPORTED=("zh","en")` + nhãn/label maps | ⚠️ Chỉ zh/en, default zh, chưa có vi |
| **Nội dung báo cáo (LLM)** | Prompt scaffold tiếng Trung + khối "output language" en/zh (`analyzer.py:3718/3730`) | ⚠️ Body en được, nhưng khung prompt vẫn Trung; chưa có vi |

---

## 3. Nguyên nhân gốc "đổi English vẫn tiếng Trung" (ưu tiên)

- **R1 (CHÍNH) — Nhãn báo cáo theo ngôn ngữ báo cáo đã lưu, không theo UI.**
  `HomePage.tsx:233` `reportLanguage = normalizeReportLanguage(selectedReport?.meta.reportLanguage)`; truyền xuống `ReportSummary/ReportOverview/MarketReviewReportView` → `getReportText(reportLanguage)`. Báo cáo tạo bằng tiếng Trung → nhãn (核心洞察, 操作建议, 策略点位...) **mãi tiếng Trung dù UI = English**. (Body LLM cũng cố định theo lúc tạo.)
- **R2 — Mặc định `zh`.** `reportLanguage.ts:3` `normalizeReportLanguage` trả `zh` trừ khi đúng `'en'` (nên `undefined`/`null`/`vi` → zh). BE: `config.py:900` `report_language="zh"`, `normalize_report_language(default="zh")`, ~8 chỗ `getattr(config,"report_language","zh")`.
- **R3 — Chuỗi tiếng Trung hardcode (FE)** không qua `t()` (mục 4).
- **R4 — Backend rò rỉ tiếng Trung user-facing** (mục 5): tên CK fallback `股票{code}`, lỗi API, body thông báo/email.

> Đã xử lý trước đó: `_emit_progress(...)` trong `src/core/pipeline.py` (11 chuỗi) đã dịch sang VN; `submitAnalysis` đã gửi `report_language` theo UI (`HomePage.tsx:419,462`).

---

## 4. Tracking — Frontend (`apps/dsa-web/src`)

### A. Chuỗi tiếng Trung hardcode (không qua `t()`) — ~85 chỗ
- `components/StockAutocomplete/StockAutocomplete.tsx:41,100` — default `placeholder = '输入股票代码或名称'`.
- `components/alerts/AlertRuleForm.tsx:35–104` — **~37 nhãn** (loại cảnh báo, scope, mức độ, hướng, thị trường, đèn).
- `components/alerts/AlertTriggerHistory.tsx:9–12,52–58,66–73` — map trạng thái, tiêu đề/empty, header bảng.
- `components/alerts/AlertsPage.tsx` (`pages/AlertsPage.tsx`):49–58,79–96,102,209,265–330 — nhãn inline, `document.title='告警中心 - DSA'`, toast, card.
- `components/StockAutocomplete/SuggestionsList.tsx:80–109` — badge thị trường (A股/港股...) & match (精确/前缀...).
- `pages/PortfolioPage.tsx:60–62,1069–1404` — placeholder/label form danh mục, `FALLBACK_BROKERS` (华泰/中信/招商).
- `pages/ChatPage.tsx:~1397` — placeholder ví dụ chat (有 "分析 600519 / 茅台...").
- `components/report/MarketReviewReportView.tsx:69–72,84–93,107,117` — set tiêu đề, regex icon mục, fallback "复盘正文/复盘概览".
- **Util trả tiếng Trung (không có tham số ngôn ngữ):**
  - `utils/decisionAction.ts:16–25` — `DEFAULT_DECISION_ACTION_LABELS` (买入/持有/卖出...).
  - `utils/portfolioFormat.ts:57–77` — giá/side/cash/corporate-action/broker labels.
  - `utils/format.ts:55–60` — `formatReportType` (普通/标准/完整...).
  - `utils/validation.ts:36,43` — '请输入股票代码' / '股票代码格式不正确'.
  - `utils/marketPhase.ts:10–55` — `*_PHASE_LABELS['zh']`/TEXT prefix.

### B. Mặc định về `zh`
- `utils/reportLanguage.ts:3,107` — `normalizeReportLanguage`/`getReportText` → zh trừ khi 'en'.
- `utils/uiLanguage.ts:67,88` — browser fallback & SSR initial = 'zh'.
- `contexts/UiLanguageContext.tsx:12–15` — `fallbackContext` = 'zh'.
- Default prop `= 'zh'` ở: `ReportStrategy:40`, `ReportNews:31`, `ReportDiagnostics:138`, `ReportDetails:20`, `AnalysisContextSummary:195`, `MarketReviewReportView:265`, `ReportMarkdownPanel:23`, `ReportMarkdownDrawer:90`, `ReportMarkdown:24`.

### C. Tách Report-language vs UI-language (R1)
- `pages/HomePage.tsx:233,234,921,1061` — nhãn report theo `meta.reportLanguage`/`payload.language`, không theo UI.
- `ReportSummary.tsx:42–43`, `ReportOverview.tsx:91–92`, `MarketReviewReportView.tsx:269` — dùng `getReportText(reportLanguage)`.
- `ReportOverview.tsx` — **trộn**: vài nút dùng `t()` (theo UI), header dùng `getReportText` (theo report) → nửa đổi nửa không.

### D. Kiến trúc — điểm yếu
- **Hệ report-language chỉ zh/en**, không type-link `UiLanguage`, không có `vi` (UI vi → nhãn báo cáo en).
- **~14 ternary `language === 'zh' ? ... : ...`** ở `alerts/AlertRuleForm.tsx` (456,490,509,520,541,574,596,628,670,712,741,751,+124,382) — không scale 3 ngôn ngữ.
- **Date locale khoá `zh-CN`**: `utils/format.ts:6,20` `Intl.DateTimeFormat('zh-CN',...)` không nhận tham số ngôn ngữ.
- **`public/stocks.index.json`** chỉ có market `CN` + tên Trung (autocomplete tĩnh đã được thay bằng OpenStock live search, nhưng file vẫn là fallback CN).

---

## 5. Tracking — Backend (`src/`, `api/`)

### E. Tên cổ phiếu fallback `股票{code}` (gây "股票HPG") — CAO
- `src/services/stock_service.py:175` — `"stock_name": f"股票{stock_code}"` (placeholder quote → UI).
- `src/core/pipeline.py:440` — `stock_name = f'股票{code}'` fallback cuối.
- `src/analyzer.py:1560,3053,3313–3314` — `f'股票{code}'` / `STOCK_NAME_MAP.get(code, f'股票{code}')`.
- Đã có sẵn `report_language.py:798 get_localized_stock_name()` + `_GENERIC_STOCK_NAME_BY_LANGUAGE` (zh:"待确认股票", en:"Unnamed Stock", **chưa có vi**) nhưng các chỗ trên **không** dùng.

### F. Lỗi/thông báo API có CJK trong response — CAO
- `api/middlewares/error_handler.py:64,108,125` — 500/422 messages tiếng Trung.
- `api/v1/endpoints/analysis.py:177,294,297,305,441` — validate/lỗi phân tích.
- `api/v1/endpoints/stocks.py:158,165,389,503` — mã rỗng/không hợp lệ/không tìm thấy/"当前自选 N 只".
- `src/services/backtest_service.py:456,477,565`, `src/services/analysis_service.py:134,138` — surfaced qua API.
- (Thấp) `description=`/`summary=`/example tiếng Trung khắp `api/v1/...` → hiện trong Swagger docs.

### G. Thông báo / Email / Body báo cáo — CAO
- `src/notification.py generate_daily_report()` — **toàn bộ body per-stock hardcode tiếng Trung** (~:831–981: 核心看点/走势分析/风险提示...). (Bản `generate_dashboard_report()` đã có nhánh en — OK.)
- Title push luôn tiếng Trung: `notification_sender/{ntfy:83,gotify:79,pushplus:73,pushover:83,serverchan3:69}` `"📈 股票分析报告"`; `custom_webhook:115,286,309,328,368`; `feishu_sender.py:124`; `slack_sender.py:220`.
- Email `notification_sender/email_sender.py:62,114,166,238,245,247–248` — subject/body/sender name tiếng Trung.
- `templates/report_markdown.j2:~181,184` — fallback template (path cũ).
- `config.py:840,1738` — `email_sender_name='daily_stock_analysis股票分析助手'`.

### H. Progress của luồng phân tích còn sót ở `analyzer.py` (KHÔNG nằm trong pipeline.py) — TRUNG BÌNH
- `src/analyzer.py:3042,3170,3218` — 3 `_emit_progress(...)` tiếng Trung (LLM 请求前等待 / 已接收请求 / 返回完成解析 JSON). **Cùng loại bug đã sửa ở pipeline.py.**

### I. Chưa hỗ trợ `vi` cho báo cáo — CAO (nếu muốn báo cáo tiếng Việt)
- `src/report_language.py:9` `SUPPORTED_REPORT_LANGUAGES=("zh","en")`; mọi dict nhãn/sentiment/generic-name chỉ zh/en. `vi` → fallback zh.

---

## 6. Lộ trình thêm tiếng Việt cho NỘI DUNG báo cáo (LLM)

Hiện UI=vi → báo cáo ra **tiếng Anh** (`uiToReportLanguage` map vi→en). Muốn báo cáo hẳn tiếng Việt cần:
1. `src/report_language.py`: thêm `"vi"` vào `SUPPORTED_REPORT_LANGUAGES` + entry `vi` cho mọi dict (`_REPORT_LABELS`, sentiment, `_GENERIC_STOCK_NAME_BY_LANGUAGE`, placeholder/unknown/no-data...).
2. Prompt "output language": thêm nhánh `vi` tại `src/analyzer.py:3718–3737` và `src/market_analyzer.py:1249–1377` (+ strategy blocks `:217–312`).
3. Frontend: `reportLanguage.ts` thêm `REPORT_TEXT.vi` + cho `UiLanguage` 'vi' đi thẳng (bỏ map vi→en trong `uiToReportLanguage`); type-link `ReportLanguage` với `UiLanguage`.
4. (Tùy) Dịch khung prompt scaffold (`analyzer.py:3346–3716`) — không bắt buộc để có body vi, nhưng cải thiện chất lượng.

---

## 7. Ưu tiên đề xuất

| Mức | Hạng mục | Ghi chú |
|---|---|---|
| **P0** | R1: nhãn report theo UI (hoặc tối thiểu đồng bộ), E: tên CK fallback, F: lỗi API, H: 3 progress còn sót | Ảnh hưởng trực tiếp trải nghiệm "đổi English" |
| **P1** | A: hardcode FE (alerts/portfolio/autocomplete/suggestions), G: thông báo/email | Nhiều chuỗi, gom theo file |
| **P2** | D: ternary `=== 'zh'`, date locale `zh-CN`, B: default-to-zh dọn dẹp | Kiến trúc/đồng nhất |
| **P3** | I + Mục 6: hỗ trợ `vi` cho nội dung báo cáo (FE+BE) | Khi cần báo cáo tiếng Việt thật |

### Khuyến nghị thiết kế
- **Hợp nhất** hệ report-language với `UiLanguage` (type-link `ReportLanguage`), để label báo cáo bám UI; tách rõ "nhãn chrome" (theo UI) vs "body LLM" (theo ngôn ngữ tạo).
- Thay `language === 'zh' ? a : b` bằng tra `Record<UiLanguage,...>` (đã có sẵn ở `featureText.ts`).
- Tham số hoá date locale theo `UiLanguage` thay vì khoá `zh-CN`.
- Backend: định tuyến mọi chuỗi user-facing qua `get_report_labels(lang)` / localizer thay vì hardcode.

---

## 8. Đã xong (tham chiếu)
- `src/core/pipeline.py` (11) + `src/analyzer.py:3042,3170,3218` (3) — `_emit_progress` đã dịch VN.
- `HomePage.tsx` — analyze/reanalyze gửi `report_language` theo UI.
- UI text (`uiText.ts` 673 keys × 3) + `featureText.ts` (28 map) — đã có `vi`.
- Search cổ phiếu — OpenStock live.

### Cập nhật 2026-06-25 (đợt P0/P1)
- **Switcher chỉ còn EN ↔ VI, bỏ ZH, mặc định VI**: `UiLanguageToggle.tsx` (cycle en/vi), `uiLanguage.ts` (browser/SSR default vi, bỏ qua `zh` đã lưu), `UiLanguageContext.tsx` (fallback vi). Dict `zh` vẫn giữ làm nguồn `UiTextKey` nhưng không chọn được.
- **P0 — R1**: nhãn báo cáo bám UI (`HomePage.tsx:233` → `uiToReportLanguage(uiLanguage)`). Thân LLM giữ ngôn ngữ lúc tạo.
- **P0 — E**: bỏ fallback `股票{code}` → dùng mã (`stock_service.py:175`, `pipeline.py:440`, `analyzer.py:1560,3053,3313-3314`).
- **P0 — F**: lỗi API → English (`error_handler.py`, `endpoints/analysis.py`, `endpoints/stocks.py`).
- **P1 — Search UI**: `SuggestionsList.tsx` badge market/match theo UI (+ fix CRASH khi market='VN'); `StockAutocomplete.tsx` placeholder dùng `t('home.placeholder')`.
- **P1 — Alerts**: `AlertRuleForm/AlertTriggerHistory/AlertRuleList/AlertsPage` — bỏ ~14 ternary `=== 'zh'`, dùng `featureText[language]` (đã có vi), dịch literal qua map cục bộ.
- **P1 — Portfolio/Chat/utils**: `PortfolioPage.tsx`, `ChatPage.tsx`, `utils/{portfolioFormat,format,validation,decisionAction}.ts` — dịch vi/en; `format.ts` date locale theo `language` (bỏ `zh-CN` cứng).
- Frontend `tsc -b --noEmit` PASS.

### Cập nhật 2026-06-26 (VN-first: báo cáo phân tích ra tiếng Việt)
Đã chuyển ngôn ngữ nền của luồng phân tích cổ phiếu sang tiếng Việt (thay vì chỉ dựa directive):
- `src/report_language.py`: `SUPPORTED += "vi"`, labels vi, **canonical maps thêm key tiếng Việt** (parse output LLM tiếng Việt → hành động/xu hướng), `get_sentiment_label` nhánh vi.
- `src/analyzer.py`: nhánh chỉ thị output `vi` (mạnh, cấm tiếng Trung) + một phần scaffold đã dịch; `_set_structural_hold_wording` thêm vi (an toàn `.get`).
- `src/stock_analyzer.py` + `src/analysis_context_pack_prompt.py`: **chuỗi context model hay "nhại" (ma_status/trend/volume/RSI/MACD...) đã sang tiếng Việt** — đây là đòn bẩy chính.
- `src/schemas/decision_action.py`: `_ACTION_LABELS` thêm vi. `api/v1/schemas/analysis.py`: `report_language` Literal thêm `"vi"`. `.env`: `REPORT_LANGUAGE=vi`.
- Frontend `reportLanguage.ts`/`types/analysis.ts` + các `Record<ReportLanguage>`: thêm vi (tsc xanh).
- **Kết quả test (VNM, FPT, gpt-4o-mini): báo cáo 100% tiếng Việt, 0 ký tự Trung trong summary/strategy/raw_result.**
- **Model**: `gpt-4o-mini` (rẻ + JSON ổn định + tiếng Việt). `gpt-4.1-nano` rẻ hơn nhưng yếu JSON có cấu trúc (từng rỗng/sai schema) → không khuyến nghị cho luồng phân tích.

### Cập nhật 2026-06-26 (VN Market Review — fix gốc)
Market review trước đây chạy region=CN (A-share) → LLM nhắc 上证/深证/创业板. Đã dựng **market review cho Việt Nam**:
- `data_provider/openstock_fetcher.py`: implement `get_main_indices('vn')` → VN-Index từ OpenStock `/dashboard/market/overview`.
- `src/core/market_profile.py`: thêm `VN_PROFILE` (mood_index=VNINDEX, news_queries VN, hint VN) + `get_profile('vn')`.
- `src/core/market_strategy.py`: thêm `VN_BLUEPRINT` (tiếng Việt, khung VN-Index/khối ngoại) + route vn. (CN/HK blueprint cũng đã dịch sang tiếng Việt.)
- `src/core/market_review.py`: thêm market `('vn','vn_title','VN')` + `vn_title` (en/vi/zh) + nhánh vi cho titles/stock_name/operation_advice ("Xem phân tích")/label/message.
- `src/core/market_profile.py` + `market_strategy.py`: `prompt_index_hint`/checkpoints bỏ tên chỉ số CN.
- `api/v1/schemas/analysis.py`: `MARKET_REVIEW_REGION`/region parser nhận `vn`; `api/v1/endpoints/analysis.py`: message submit → tiếng Việt.
- `.env`: `MARKET_REVIEW_REGION=vn`.
- **Verify (gpt-4o-mini): market review report 100% tiếng Việt, 0 ký tự Trung; không còn 上证/深证/创业板.**

### Còn lại (chưa làm)
- `src/market_analyzer.py` còn ~ vài trăm CJK (comment/log/nhánh zh-fallback/unit helper) — không hướng-LLM cho region vn nên output đã sạch; dọn nốt khi rảnh.
- Market review hiện chỉ lấy 1 chỉ số (VN-Index) + chưa có breadth/sector cho VN (profile `has_market_stats/has_sector_rankings=False`). Mở rộng sau (OpenStock có dữ liệu breadth/sector).
- `src/analyzer.py` còn ~4k CJK nhưng phần lớn là comment/log/key-parse (KHÔNG hướng-LLM) → output phân tích đã tiếng Việt.
- **BE thông báo/email (G)**: `notification.py generate_daily_report()` + `notification_sender/*` + `email_sender.py` vẫn tiếng Trung (P1).
- **BE lỗi phụ**: `backtest_service.py`, `analysis_service.py` vài chuỗi (P2).
- **P3 — Báo cáo tiếng Việt thật**: `report_language.py` mới có zh/en; cần thêm `vi` (labels + prompt `analyzer.py:3718`, `market_analyzer.py:1249`). Hiện UI=vi → báo cáo ra **English**.
- **Tests**: ~275 test component assert text tiếng Trung + 2 test `portfolioFormat` → **stale** do default đổi sang vi. Cần cập nhật test (set language hoặc assert vi/en) — chưa làm, không chặn app chạy.
- Call-site nhỏ chưa truyền `language` (an toàn vì default vi): `AlertsPage.tsx:353`, `BacktestPage.tsx:643`, `chatFollowUp.ts:34`, `chatStockCode.ts:102`.
