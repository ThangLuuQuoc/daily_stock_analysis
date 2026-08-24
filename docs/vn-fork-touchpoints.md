# VN fork — Touchpoints vào code upstream

Tài liệu **canonical** liệt kê MỌI chỗ fork VN sửa file của upstream
(`ZhuLinsen/daily_stock_analysis`). Mục đích: lần catch-up sau đi trong 1 giờ thay vì
1 tuần.

**Quy tắc bắt buộc:** mỗi lần buộc phải sửa một file của upstream → thêm 1 dòng vào đây,
kèm **lý do** và **cách re-apply**. Nếu không ghi, coi như chưa xong việc.

Base hiện tại: branch `vendor` = upstream `ecf87ea0` (2026-06-24).
Upstream HEAD lúc lập tài liệu: `v3.31.0` (2026-08-23).

## Cách dùng nhanh

```bash
# Fork da sua gi cua upstream?
git diff --stat vendor -- $(git diff --name-only --diff-filter=M vendor)

# Xem 1 file da lech the nao
git diff vendor -- src/analyzer.py

# Phuc hoi nguyen trang 1 file cua upstream
git checkout vendor -- src/market_phase_prompt.py

# Do be mat fork (CI guard)
bash scripts/check-fork-surface.sh
```

---

## 1. Bảng touchpoint

Cột **Loại**:
`HOOK` = chỉ 1–3 dòng gọi sang code của ta (tốt) ·
`BRANCH` = thêm nhánh `vi`/`vn` kề nhánh đã có (chấp nhận được) ·
`REWRITE` = viết lại logic upstream (đắt, cần bỏ) ·
`OVERWRITE` = ghi đè literal của upstream (rất tệ, phải bỏ)

### 1.1 Data provider / routing thị trường VN

| File | Vị trí | Loại | Lý do | Re-apply |
|---|---|---|---|---|
| `data_provider/base.py` | `_is_vn_market()` (~193) | HOOK | nhận diện mã VN, gate sau `openstock_enabled` | giữ; nguồn sự thật vẫn là regex (xem §Phase 2b bên dưới — không build symbol-universe vì OpenStock chưa có endpoint liệt kê mã) |
| `data_provider/base.py` | `_market_tag()` (~255) | HOOK | trả `"vn"` | 1 dòng, dễ re-apply |
| `data_provider/base.py` | `_DAILY_MARKET_FETCHER_SUPPORT` (~630) | HOOK | `"OpenStockFetcher": {"vn"}` | 1 dòng |
| `data_provider/base.py` | `get_fundamental_context()` (~3013) | HOOK ✅ | route `market == "vn"` → `build_vn_fundamental_context` | 3 dòng, đặt TRƯỚC nhánh `us/hk/jp/kr` |
| `data_provider/base.py` | `get_capital_flow_context()` (~3312) | HOOK ✅ | route `"vn"` → `build_vn_capital_flow_block` (Agent tool gọi trực tiếp entry này) | 3 dòng, đặt TRƯỚC guard `!= "cn"` |
| `data_provider/base.py` | `_init_default_fetchers()` | HOOK ✅ **(Phase 2a xong)** | **Đã revert về vendor nguyên bản** + 1 khối 6 dòng thêm OpenStockFetcher, cùng style với khối Tushare có sẵn. Trước đây REWRITE toàn bộ hàm bằng tolerant-import — **đã kiểm chứng bằng git worktree của `vendor`: giả định "thiếu efinance/akshare thì crash" là SAI**, mọi fetcher class lazy-import thư viện bên thứ 3 bên trong method chứ không phải module/class level, nên hard-import của vendor chạy tốt dù thiếu hết 9 lib | 6 dòng, đặt sau `optional_fetchers: List[...] = []` |
| `data_provider/base.py` | daily routing (~1278), quote routing (~1710) | HOOK ✅ **(Phase 2b xong)** | Đã gộp `is_vn/is_us/is_hk/is_jp/is_kr` về `market = _market_tag(stock_code)` rồi suy ra từng boolean từ `market == "..."` — chứng minh tương đương vì `_market_tag` dùng đúng các hàm `_is_us_market`/`_is_hk_market`/... theo đúng thứ tự ưu tiên. Bỏ luôn 1 import không còn dùng (`is_us_stock_code`, `_is_us_code`) | đã ở dạng tối giản, không cần re-apply thêm |
| `data_provider/__init__.py` | toàn file | HOOK ✅ **(Phase 2a xong)** | **Đã revert về vendor nguyên bản** + 3 dòng import OpenStock (`OpenStockFetcher`, `OpenStockFundamentalAdapter`, `openstock_symbols`) + mở rộng `__all__`. Trước đây rewrite toàn bộ bằng `_optional_import()` loader — không cần thiết (lý do như trên) | 3 dòng import + entries trong `__all__` |
| `data_provider/realtime_types.py` | 1 dòng | ? | cần rà lại xem còn cần không | — |

### 1.1b Basic-fundamental VN (Phase 1 — đã xong)

File mới `data_provider/vn_fundamental_context.py` giữ toàn bộ logic; `base.py` chỉ có
2 hook × 3 dòng ở trên. Trước Phase 1, `OpenStockFundamentalAdapter` là **dead code**:
mã VN rơi vào nhánh A-share nên gọi AkShare với `"FPT"`, và `capital_flow` bị guard
`_market_tag != "cn"` chặn → tăng trưởng doanh thu/LNST, biên gộp, dòng tiền HĐKD và
**dòng tiền khối ngoại** không tới được LLM.

Test khoá lại: `tests/test_vn_fundamental_context.py` (8 test) assert trên **context
pack pipeline thật dùng**, không phải trên adapter — tháo hook là test đỏ.

### 1.2 Config

| File | Vị trí | Loại | Lý do |
|---|---|---|---|
| `src/config.py` | `openstock_base_url` / `openstock_enabled` | HOOK | config adapter |
| `src/config.py` | `DEFAULT_VN_NEWS_DOMAINS`, `parse_vn_news_domains()`, `vn_news_*` | HOOK | chế độ tin tức VN |
| `src/config.py` | `_parse_market_review_region` thêm `'vn'` | BRANCH | market review VN |

### 1.3 Tin tức VN — **mẫu chuẩn, nhân rộng cách này**

| File | Loại | Ghi chú |
|---|---|---|
| `src/search_service.py` | HOOK | 3 private method mới (`_vn_scope`, `_is_vn_domain`, `_restrict_response_to_vn`), tất cả gate sau `if self.vn_news_enabled`. Sửa +197 dòng vào file upstream đổi +490 mà **chỉ 3 hunk xung đột** |

### 1.4 Market review VN

| File | Loại | Ghi chú |
|---|---|---|
| `src/core/market_profile.py` | BRANCH | `VN_PROFILE` + route `'vn'` |
| `src/core/market_strategy.py` | BRANCH | `VN_BLUEPRINT` + route `'vn'` |
| `src/core/market_review.py` | BRANCH | market tuple `('vn','vn_title','VN')` |
| `api/v1/schemas/analysis.py` | BRANCH | region parser nhận `vn`; `report_language` Literal thêm `"vi"` |

### 1.5 API

| File | Loại | Lý do | Re-apply |
|---|---|---|---|
| `api/v1/endpoints/vn_search.py` (mới) | HOOK ✅ **(Phase 2c xong)** | endpoint `/search` gọi OpenStock — đã tách khỏi `stocks.py` sang file riêng của fork | file độc lập, không đụng `stocks.py` nữa |
| `api/v1/router.py` | HOOK ✅ **(Phase 2c — file mới bị chạm)** | thêm import `vn_search` + `include_router(vn_search.router, prefix="/stocks", ...)` — mount CHUNG prefix `/stocks` với `stocks.router` để giữ nguyên URL `/api/v1/stocks/search` (frontend `apps/dsa-web/src/api/stocks.ts` không cần đổi). Test khoá lại: `tests/test_vn_search_endpoint.py::test_duong_dan_van_la_stocks_search` | 5 dòng (1 import + 1 khối `include_router`) |
| `api/v1/endpoints/stocks.py` | — ✅ **(Phase 2c xong)** | endpoint `/search` đã dọn sạch khỏi file này, quay lại gần như nguyên bản upstream | không còn gì để re-apply cho mục này |
| `api/v1/endpoints/stocks.py` | OVERWRITE | message lỗi TQ → English | gộp vào lớp localize thay vì sửa literal (Phase 3) |
| `api/middlewares/error_handler.py` | OVERWRITE | như trên | như trên |
| `api/v1/endpoints/analysis.py` | OVERWRITE | như trên | như trên |

### 1.6 i18n — ⚠️ khu vực nợ kỹ thuật nặng nhất

| File | Loại | Trạng thái |
|---|---|---|
| `src/report_language.py` | BRANCH + OVERWRITE | `SUPPORTED=("zh","en","vi")` đối đầu `("zh","en","ko")` của upstream; thêm `"vi"` vào dict `key→{lang}` → **13 hunk xung đột**. Phase 3b: chuyển sang overlay `src/report_language_vi.py` |
| `src/analyzer.py` | BRANCH + **OVERWRITE** | **15 hunk xung đột**. Nhánh chỉ thị output `vi` = giữ; phần dịch scaffold tại chỗ = bỏ |
| `src/market_analyzer.py` | **OVERWRITE** | +138/−138 = thay 1:1 literal. **13 hunk.** Phase 3a: `git checkout vendor --` |
| `src/market_phase_prompt.py` | **OVERWRITE** | `_PHASE_LABELS_ZH` chứa tiếng Việt, `_format_zh()` emit tiếng Việt. Phase 3a + 3c |
| `src/market_phase_summary.py` | **OVERWRITE** | như trên |
| `src/stock_analyzer.py` | **OVERWRITE** | +62/−62 |
| `src/market_context.py` | **OVERWRITE** | +15/−15 |
| `src/analysis_context_pack_prompt.py` | **OVERWRITE** | +41/−40 |
| `src/daily_market_context_guardrail.py` | OVERWRITE | 2 hunk |
| `src/schemas/decision_action.py` | BRANCH | `_ACTION_LABELS["vi"]` — ổn |
| `src/core/pipeline.py` | OVERWRITE | 11 chuỗi `_emit_progress` |
| `src/services/stock_service.py`, `src/notification.py` | HOOK | bỏ fallback `股票{code}` |

> **Rủi ro không báo lỗi**: mọi dòng `OVERWRITE` nghĩa là upstream thêm label mới sẽ về
> dưới dạng tiếng Trung và đi thẳng vào report tiếng Việt. Test `vi` coverage ở Phase 3b
> là thứ duy nhất bắt được việc này.

### 1.7 Frontend (`apps/dsa-web/src`)

| Nhóm file | Loại | Ghi chú |
|---|---|---|
| `i18n/uiText.ts` | BRANCH | +696 dòng `vi`, type-safe — **tốt, giữ** |
| `locales/featureText.ts`, `locales/settingsHelp.ts` | BRANCH | tốt |
| `utils/reportLanguage.ts`, `types/analysis.ts` | BRANCH | thêm `vi` vào `ReportLanguage`; khi merge `ko` → `'zh'|'en'|'ko'|'vi'` |
| `utils/uiLanguage.ts`, `contexts/UiLanguageContext.tsx`, `components/i18n/UiLanguageToggle.tsx` | BRANCH | default `vi`, toggle EN↔VI (quyết định sản phẩm) |
| `pages/{HomePage,ChatPage,PortfolioPage,AlertsPage,BacktestPage}.tsx` | OVERWRITE | dịch literal tại chỗ; `ChatPage` **11 hunk**, `HomePage` 2 |
| `components/alerts/*`, `components/report/*`, `components/StockAutocomplete/*` | OVERWRITE | dịch literal |
| `utils/{decisionAction,portfolioFormat,format,validation,marketPhase}.ts` | OVERWRITE | dịch literal + date locale tham số hoá (phần locale là **tốt**) |
| `api/stocks.ts`, `hooks/useAutocomplete.ts` | HOOK | gọi `/search` của OpenStock |

### 1.8 Khác

| File | Loại | Ghi chú |
|---|---|---|
| `docs/*.md`, `docs/CHANGELOG.md` | BRANCH | thêm mục VN vào tài liệu upstream |
| `templates/report_{markdown,brief,wechat}.j2` | OVERWRITE | dịch literal |
| `docker/docker-compose.yml`, `.github/workflows/00-daily-analysis.yml` | HOOK | cấu hình deployment |
| `CLAUDE.md` | — | **KHÔNG phải fork sửa.** Upstream để đây là symlink → `AGENTS.md`; snapshot dựng từ tarball làm nó thành file thường nên trước đó bị đếm sai là `−291 dòng`. Đã phục hồi ở commit `chore(fork): phuc hoi symlink...` |
| `tests/*` (18 file) | — | **đang đỏ**: assert tiếng Trung nhưng source emit tiếng Việt |

---

## 2. Điểm upstream sẽ đụng ta trong tương lai

Upstream đang siết chuẩn hoá mã chứng khoán. `is_us_stock_code()` của họ = **1–5 chữ in
hoa** → mã VN 3 chữ là tập con. Mỗi module dưới đây là một chỗ ta sẽ phải hook thêm:

| Module upstream | Từ release | Việc cần làm khi merge |
|---|---|---|
| `src/services/market_symbol_utils.py` | 3.24.0 | thêm spec/suffix VN nếu dùng `FPT.VN` |
| `src/services/name_to_code_resolver.py` | 3.31.0 | VN name → code qua OpenStock `/search` |
| `src/services/stock_list_parser.py` (`canonical_id`) | 3.31.0 | định nghĩa `canonical_id` cho mã VN |
| target-resolution contract | 3.30.0 | chèn nhận diện VN trước US |
| `src/services/screening/*` | 3.29.0 | universe + chỉ tiêu VN cho screener |

---

## 3. Ngân sách bề mặt fork

| Chỉ số | Trước Phase 2 | Sau Phase 2a+2b+2c | Mục tiêu sau Phase 3 |
|---|---|---|---|
| File upstream bị sửa | 66 | **67**¹ | ≤ 30 |
| File xung đột khi merge v3.31.0 | 28 | _(đo lại trước khi merge thật)_ | ≤ 10 |
| Hunk xung đột | 98 | _(đo lại trước khi merge thật)_ | ≤ 25 |

¹ Tăng 1 vì Phase 2c thêm `api/v1/router.py` vào danh sách file bị sửa (5 dòng, HOOK
thuần) để tách `/search` ra khỏi `stocks.py`. Đổi lại: `data_provider/base.py` và
`data_provider/__init__.py` giảm từ REWRITE (6+ hunk, hàng chục dòng logic viết lại)
xuống còn thuần HOOK/BRANCH (mỗi hunk vài dòng) — chất lượng diff tốt hơn nhiều dù số
đếm file không giảm. Đo bằng `--merge-test` sẽ phản ánh đúng việc này hơn đếm file.

`scripts/check-fork-surface.sh` fail khi vượt trần đặt trong file đó.

### Việc đã KHÔNG làm trong Phase 2b — và lý do

Plan gốc đề xuất "openstock_symbols.py thành single source of truth, dữ liệu lấy từ
OpenStock universe, cache TTL". **Không triển khai** vì OpenStock hiện chỉ có
`GET /search?q=` (cần query, không có endpoint liệt kê toàn bộ mã) — xác nhận lại
trong `plan/daily_stock_analysis_adapter.md` và `plan/openstock_adapter_gaps.md`,
không thấy endpoint nào phù hợp. Build một cơ chế cache dựa trên network call tới
endpoint không tồn tại là suy đoán, không kiểm chứng được.

Tương tự, các false-negative đã biết (ETF `FUEVFVND`/`E1VFVN30`, hợp đồng phái sinh
`VN30F2409`) **không sửa bằng regex đoán mò** — không có cách xác minh danh sách mã ETF
VN hiện hành từ môi trường này, và một regex sai tạo cảm giác an toàn giả còn tệ hơn
giữ nguyên hạn chế đã biết. Việc đã làm thay vào đó: **gộp toàn bộ điểm gọi
`_is_vn_market`/`is_us`/... về một hàm `_market_tag()` duy nhất** — khi có endpoint
universe thật (cần thêm vào `openstock_adapter_gaps.md` mục C như một backend gap),
chỉ cần sửa `_is_vn_market()` một chỗ, mọi call site tự động ăn theo.

Test khoá lại giới hạn đã biết: `tests/test_vn_fundamental_context.py::test_flag_off_thi_ma_3_chu_bi_coi_la_my___han_che_da_biet`.
