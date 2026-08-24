# OpenStock Adapter — Trạng thái & Theo dõi gap

Tài liệu kèm theo [daily_stock_analysis_adapter.md](daily_stock_analysis_adapter.md).
Ghi nhận **đã làm gì (Phase 0 MVP)**, **endpoint nào thực ra đã có** (plan gốc viết
trước khi realtime-signals V1 bổ sung), và **gap còn lại** cần làm sau.

> Nguyên tắc: **không sửa OpenStock** trong giai đoạn này. Adapter chỉ gọi endpoint
> public sẵn có. Mọi việc cần đụng backend OpenStock đều liệt kê ở mục "Gap" bên dưới
> để implement sau.

Cập nhật: 2026-06-25 · Đã kiểm thử trực tiếp với OpenStock chạy local
(`http://localhost:3000/api/v1`).

---

## 1. Đã hoàn thành (Phase 0 MVP)

| File | Nội dung |
|---|---|
| `data_provider/openstock_symbols.py` | Nhận diện mã VN (3 chữ in hoa / chỉ số / chứng quyền), map chỉ số VN. |
| `data_provider/openstock_fetcher.py` | `OpenStockFetcher(BaseFetcher)` — `_fetch_raw_data`, `_normalize_data`, `get_realtime_quote`, `get_stock_name`. |
| `data_provider/openstock_fundamental_adapter.py` | `OpenStockFundamentalAdapter` — `get_fundamental_bundle`, `get_capital_flow`, `get_dragon_tiger_flag` (stub). |
| `data_provider/__init__.py` | Export các symbol mới. |
| `src/config.py` | `openstock_base_url`, `openstock_enabled` (env: `OPENSTOCK_BASE_URL`, `OPENSTOCK_ENABLED`). |
| `scripts/test_openstock_adapter.py` | Smoke test trực tiếp với server local. |

**Kết quả test (FPT, VNM):** `get_stock_name`, `get_daily_data`, `get_realtime_quote`,
`get_fundamental_bundle`, `get_capital_flow` đều OK. Đủ để LLM phân tích cổ phiếu VN ở
mức cơ bản.

Chạy lại:
```bash
OPENSTOCK_ENABLED=true python scripts/test_openstock_adapter.py FPT
# môi trường numpy/OpenBLAS hạn chế RAM: thêm OPENBLAS_NUM_THREADS=1 OMP_NUM_THREADS=1
```

---

## 2. Endpoint plan gốc ghi "thiếu" nhưng THỰC RA ĐÃ CÓ

Plan `daily_stock_analysis_adapter.md` viết trước realtime-signals V1. Đã xác nhận live:

| Endpoint | Trạng thái thực tế |
|---|---|
| `GET /stocks/:symbol/capital-flow?days=N` | ✅ Đã có. Trả `[{time, close, amount, foreignNet}]`. (Plan Phase 1 item 3) |
| `GET /dashboard/market/ceiling-floor` | ✅ Đã có. (Plan Phase 1 item 6) |
| `GET /stocks/:symbol/daily?limit=N` | ✅ Đã có (ngoài `/candles?from&to`). |
| Candle có field `amount`, `foreignNet` | ✅ Field đã có trong response (dù phần lớn còn `null`, xem gap 5). |
| `GET /stock/quote` có `value`, `ceiling`, `floor`, `foreignBuyVol/SellVol`, `foreignNetValue` | ✅ Đã có (nhiều hơn plan mô tả). |
| `GET /fundamentals/:symbol/overview` | ✅ Rất đầy đủ: pe, pb, eps, bvps, roe, roa, profitMargin, marketCap, sharesOutstanding, dividendYield, foreignOwnedPct, foreignRoomLeftPct. |

---

## 3. Gap còn lại (cần làm sau)

### A. Cần seed dữ liệu / sửa backend OpenStock

| # | Gap | Ảnh hưởng adapter | Đề xuất |
|---|---|---|---|
| ~~1~~ | ~~`GET /stocks/:symbol/financials` trả `statements: []`~~ | — | **✅ ĐÃ ĐÓNG 2026-08-14** — xem mục 6 bên dưới. |
| 5 | Candle `amount` chỉ có ở vài phiên gần nhất; phần lớn `null`. | Lịch sử thành khoản đang **ước lượng** `close*volume*1000` (close đơn vị nghìn VND → ×1000 ra VND đầy đủ, đã khớp order-of-magnitude với amount thật). | Persist `amount` thật cho toàn bộ lịch sử (realtime §10.1). |
| 7 | `capital-flow` `foreignNet` thưa (nhiều ngày `null`; VNM trả toàn `null`). | `get_capital_flow` có thể ra `not_supported` với mã ít dữ liệu khối ngoại. | Persist foreign net đầy đủ hơn. |

### B. Endpoint chưa có (đã có dữ liệu trong DB — plan Phase 1)

| # | Endpoint đề xuất | Lấp method | Nguồn dữ liệu |
|---|---|---|---|
| 4 | `GET /stocks/:symbol/dividends` | `dividend` (cash events + TTM). Hiện adapter chỉ lấy được `dividendYield` từ overview. | `corporate_actions`, `dividendPerShare`. |
| 5b | `GET /stocks/:symbol/ownership` | `institution_holding_change`, `top10_holder_change`. Hiện chỉ có `foreignOwnedPct/RoomLeftPct` từ overview. | `ownership_snapshots`, `major_shareholders`. |
| — | Mở rộng `/stock/quote`: thêm `pe, pb, marketCap, high52w, low52w, turnoverRatio, volumeRatio, change60d` | Bỏ được lệnh gọi `/fundamentals/overview` phụ trong `get_realtime_quote`; lấp `volume_ratio`, `high_52w`, `low_52w`, `change_60d` (hiện = `None`). | DB đã có phần lớn; 52w/60d cần precompute. |

### C. Endpoint thị trường (plan Phase 2) — adapter CHƯA implement (optional)

Các method optional của `BaseFetcher` hiện để mặc định `None`. Endpoint OpenStock đã có,
chỉ cần viết thêm trong `OpenStockFetcher`:

| Method | Endpoint sẵn có | Ghi chú |
|---|---|---|
| `get_market_stats` | `GET /dashboard/market/overview` | breadth/advancers. |
| `get_hot_stocks` | `GET /dashboard/market/leaders` | top movers. |
| `get_limit_up_pool` | `GET /dashboard/market/ceiling-floor` | cổ phiếu trần/sàn. |
| `get_sector_rankings` | `GET /sectors`, `/sectors/:sector/valuation` | thiếu top gainers/losers mỗi ngành. |
| `get_main_indices` | (chưa có `/indices`) | Cần endpoint indices gọn, hoặc trích từ `/dashboard/market/overview`. |

### D. Không áp dụng cho VN (đặc thù Trung Quốc)

| Method | Xử lý |
|---|---|
| `get_dragon_tiger_flag` | Stub `not_supported` (đã làm). |
| `get_chip_distribution` | Để mặc định `None`. |
| `get_concept_rankings` | Map concept→ngành; chưa làm, optional. |

---

## 4. Tích hợp vào DataFetcherManager — ✅ ĐÃ XONG

> Mục này trước ghi "CHƯA làm". Kiểm tra lại `data_provider/base.py` ngày 2026-08-14
> thì việc wiring **đã hoàn thành** rồi:
>
> - `is_vn_stock_code` / `is_vn_index_code` được import và dùng (dòng ~208).
> - Map thị trường có `"OpenStockFetcher": {"vn"}` (dòng ~630).
> - `_init_default_fetchers()` đăng ký `OpenStockFetcher` khi `openstock_enabled`
>   (dòng ~1185), có log `[数据源初始化] 已启用 OpenStockFetcher（越南市场）`.
>
> Không còn giới hạn "chỉ dùng được khi gọi trực tiếp".

---

## 4b. Cập nhật 2026-08-24 — rà lại code OpenStock hiện tại

Rà trực tiếp `src/routes/` + `src/services/` + `src/db/schema.ts` của OpenStock (thay
vì dựa vào bảng gap viết 2026-06-25). Kết quả: **phần lớn gap đã đóng ở phía OpenStock,
adapter chưa dùng.** Đã sửa adapter (xem `docs/vn-fork-touchpoints.md` §1.1c).

### Đã đóng — không cần làm gì thêm bên OpenStock

| Gap cũ | Thực tế |
|---|---|
| Mở rộng `/stock/quote` (pe, pb, marketCap, high52w, low52w, turnoverRatio, volumeRatio, change60d) | ✅ **Đã có** qua `?enrich=true` → `getEnrichedQuote()`. Docstring ghi rõ viết cho adapter này |
| `GET /stocks/:symbol/ownership` (gap B 5b) | ✅ **Không cần endpoint mới** — `/dashboard/stocks/:symbol` đã trả `ownership.majorShareholders[]` + `insiderTransactions[]` + `foreignOwnedPct/RoomLeftPct/insiderHoldingsPct`. ⚠️ Nhưng xem "Chưa đáng làm" bên dưới |
| `get_market_stats` / `get_sector_rankings` (Phase 2 C) | ✅ `/dashboard/market/overview` đã có `breadth` + `sectorLeadership` |
| `get_hot_stocks` / `get_limit_up_pool` | ✅ `/dashboard/market/leaders`, `/dashboard/market/ceiling-floor` |
| `get_main_indices` — cần `/indices` gọn | ✅ **Không cần**: `syncIndexWorker` lưu VNINDEX/VN30/VN100/HNXINDEX/UPCOMINDEX vào chính `stock_prices`, nên candles/daily endpoint hiện có đã phục vụ được |

### Đã làm bên OpenStock trong đợt này

| # | Việc | File |
|---|---|---|
| 1 | `GET /stocks` — liệt kê toàn bộ symbol universe (`?active=true` để lọc), cache theo ngày giao dịch | `src/services/stockService.ts::listAllStocks`, `src/routes/stock.ts` |

Lý do: adapter cần biết "mã này có phải mã VN không" **trước khi** route request.
`/search?q=` không thay thế được (cần query + `LIMIT 15` cứng). `/tv/symbols` chỉ là
stub TradingView. Không có universe thì adapter phải đoán bằng regex `^[A-Z]{3}$` —
vừa nhận sai mã Mỹ 3 chữ, vừa bỏ sót ETF/phái sinh VN.

### Còn lại — cần làm bên OpenStock (theo thứ tự ưu tiên)

| # | Việc | Chi phí | Ghi chú |
|---|---|---|---|
| 1 | **Worker nạp `corporate_actions`** (cổ tức) | Cao | Bảng có schema đầy đủ (`DIVIDEND/SPLIT/RIGHTS/BONUS`, `exDate`, `amount`, `ratio`) nhưng `grep corporateActions src/workers/` = **0 hit** → bảng rỗng. Đây là gap **thu thập dữ liệu**, không phải gap endpoint. Cần worker fetch từ VCI/KBS trước, rồi mới thêm endpoint. Prompt của analyzer có bảng "财报与分红" đọc `dividend.ttm_cash_dividend_per_share` / `ttm_dividend_yield_pct` / `ttm_event_count` — hiện chỉ có `dividend_yield` từ overview |
| 2 | **Backfill `amount` + `foreign_net_value` lịch sử** | Phụ thuộc nguồn | `syncDailyWorker.snapshotRealtimeIntoDaily()` chỉ copy `quotes` → bar **cùng ngày**, nên bar lịch sử vẫn NULL. Adapter đang ước lượng `close*volume*1000`, và `get_capital_flow` có thể ra `not_supported` với mã ít dữ liệu khối ngoại. Không sửa retroactive được **trừ khi** VCI/KBS có API lịch sử cho 2 chỉ tiêu này — cần kiểm tra trước khi hứa |
| 3 | Top gainers/losers **theo từng ngành** | Thấp | `/sectors` chưa có. Nhưng `sectorLeadership.all` đã đủ cho prompt hiện tại → ưu tiên thấp |

### Chưa đáng làm — sẽ thành dead code

`institution` block (`institution_holding_change`, `top10_holder_change`) **không được
prompt nào đọc**. Kiểm tra: `src/analyzer.py` chỉ consume `earnings` (financial_report +
dividend) và `capital_flow`; `grep institution` trong `src/` = 0 hit ngoài
`data_provider/`. Nên dù `/dashboard/stocks/:symbol` đã có sẵn `majorShareholders`,
nối nó vào adapter bây giờ sẽ lặp lại đúng bug Phase 1 (viết code không ai gọi).

Thêm nữa, 2 field đó là **delta** (thay đổi tỉ lệ nắm giữ) còn OpenStock chỉ có
snapshot hiện tại — muốn tính delta phải đọc nhiều bản `ownership_snapshots` theo thời
gian. Làm khi nào prompt thực sự cần.

---

## 4c. Trạng thái dữ liệu thật (2026-08-24, sau khi chạy update-to-today.sh)

Đo trực tiếp trên DB (docker `stock-postgres`), không suy đoán.

| Bảng | Mới nhất | Ghi chú |
|---|---|---|
| `stock_prices` (cổ phiếu) | 2026-08-24 | 7 phiên nạp thêm: 08-14, 17, 18, 19, 20, 21, 24 (cuối tuần đúng là không có) |
| `valuation_timeseries` | 2026-08-24 | +6.252 dòng |
| `technical_indicators` | 2026-08-24 | +12.777 dòng |
| `signal_events` | 2026-08-24 | +1.591 dòng |
| `quotes` | 2026-08-24 10:38 | snapshot từ daily bar |
| `fundamental_snapshots` | 2026-06-30 | **đúng** — Q2/2026, quý sau chưa công bố. Không cần `FULL=1` cho tới mùa BCTC Q3 (~tháng 10) |
| `financial_statements` | — | 152.873 dòng, đã đầy |

### ⚠️ `VN100` — dữ liệu quá mỏng để phân tích

`syncIndexWorker.INDICES` khai báo `VN100`, nhưng nguồn gần như không trả dữ liệu:

| Chỉ số | Số dòng | Khoảng |
|---|---|---|
| VNINDEX / HNXINDEX / UPCOMINDEX | 1.558 | 2020-06-01 → 2026-08-24 |
| VN30 | 1.557 | 2020-06-01 → 2026-08-24 |
| **VN100** | **11** | **2026-05-29 → 2026-08-24** |

Trong đợt update này VN100 chỉ nạp được **1/7 phiên**, các chỉ số khác đủ 7.

**Hệ quả cho adapter:** `StockTrendAnalyzer` bail out khi `len(df) < 20`
(`src/stock_analyzer.py`), nên `VN100` được `VN_INDEX_MAPPING` nhận là mã hợp lệ
nhưng **không phân tích được** — cùng loại bẫy như `HNX30` trước đây (mã hợp lệ,
query rỗng), chỉ nhẹ hơn.

Quyết định: **giữ** `VN100` trong mapping (nó là chỉ số thật, đang được sync, dữ
liệu sẽ dày lên theo ngày) nhưng ghi lại ở đây để không ai coi nó tương đương
VNINDEX/VN30. Nếu cần dùng VN100 sớm thì phải backfill lịch sử từ nguồn khác —
đây là gap **thu thập dữ liệu** bên OpenStock, không phải gap adapter.

---

## 5. Lưu ý đơn vị (đã xử lý trong adapter)

- Giá `open/high/low/close`: **nghìn VND** (71 == 71.000 VND). Lịch sử & realtime cùng đơn vị.
- `amount` (thành khoản) / `value` / `marketCap` / `foreignNet`: **VND đầy đủ**.
- `pct_chg`: suy ra từ `close.pct_change()`.
- `turnover_rate`: tính `volume / sharesOutstanding * 100` (cần overview).
- `roe` từ overview là tỉ lệ (0.2682) → adapter quy đổi sang % (26.82).

---

## 6. Gap 1 đã đóng — BCTC (2026-08-14)

### Phía OpenStock

| File | Nội dung |
|---|---|
| `src/lib/vci.ts` | `fetchFinancialStatement(symbol, section)` — endpoint `/v1/company/{sym}/financial-statement?section=`. Ba section hợp lệ: `INCOME_STATEMENT`, `BALANCE_SHEET`, `CASH_FLOW`. |
| `src/lib/fsMapping.ts` | Map mã field VCI → khoản mục có tên, kèm ghi chép cách xác minh từng field. |
| `src/workers/syncFinancialStatementsWorker.ts` | Worker nạp cả 3 loại báo cáo, cả năm và quý. |
| `src/services/financialService.ts` | Expose khoản mục **phẳng** ở cấp statement (`revenue`, `netProfit`, `grossProfit`, `operatingCashFlow`…) thay vì buộc consumer đào vào `data.mapped`. |
| `scripts/update-to-today.sh` | Thêm worker vào nhánh `FULL=1`. |

### Vấn đề mã field và cách xử lý

VCI trả BCTC bằng mã nội bộ (`isa3`, `isb38`, `cfa18`…), mỗi nhóm ngành một bộ:
`isa*` doanh nghiệp · `isb*` ngân hàng · `iss*` chứng khoán · `isi*` bảo hiểm.
Endpoint `/v1/company/financial-statement-metadata` **có tồn tại nhưng trả `data: null`**
nên không lấy được bảng map tên chính thức.

Vì gán nhãn sai cho dòng BCTC còn tệ hơn không có dữ liệu (số này đi vào LLM sinh
khuyến nghị mua/bán), nguyên tắc đã áp dụng:

1. Lưu **nguyên payload thô** vào `data.raw` — không mất field nào, mở rộng sau
   không cần fetch lại (income 181 field, balance 331 field).
2. Chỉ map field xác minh được bằng **hai cách độc lập**, đặt vào `data.mapped`.
3. Balance sheet **chưa xác minh field nào** → `data.meta.hasMapped = false`,
   chỉ lưu thô. Không đoán.

### Bằng chứng xác minh (năm 2024)

Doanh nghiệp phi tài chính (FPT):

```
isa1 + isa2 = isa3                 → isa3 = doanh thu thuần
isa3 + isa4 = isa5                 → isa5 = lợi nhuận gộp
isa5 / isa3 = 37.71%               ↔ VCI grossMargin = 0.3770692599   KHỚP TUYỆT ĐỐI
isa20 / isa3 = 15.00%              ↔ VCI afterTaxProfitMargin = 0.1500016449  KHỚP TUYỆT ĐỐI
isa20 = 9,427 tỷ                   ↔ LNST công bố ~9,420 tỷ
isa22 = 7,857 tỷ                   ↔ LNST cổ đông mẹ công bố ~7,849 tỷ
cfa1  = 11,070 tỷ                  ↔ LNTT công bố ~11,071 tỷ
sum(cfa9..cfa17) = cfa18           → cfa18 = LCTT từ HĐKD
```

Ngân hàng (VCB):

```
isb25 + isb26 = isb27 = 55,406 tỷ  ↔ thu nhập lãi thuần công bố ~55,400 tỷ
isb38 + isb39 = isb40
isb40 + isb41 = isa16 = 42,236 tỷ  ↔ LNTT công bố ~42,200 tỷ
```

Kết luận: bank dùng `isb25..isb41` cho phần trên P&L nhưng **dùng chung
`isa16..isa23`** cho phần dưới; bank **không có** `isa3`/`isa5` (đều 0) nên
"doanh thu" thay bằng `isb38` (tổng thu nhập hoạt động) và `grossProfit` = `None`.

### Phía adapter

`openstock_fundamental_adapter.py`:

- `_compute_growth_from_financials()` — tính `revenue_yoy`, `net_profit_yoy`,
  `gross_margin` từ **chuỗi báo cáo năm** (không dùng quý để tránh méo do mùa vụ).
  Mẫu số âm hoặc 0 → trả `None` thay vì con số gây hiểu sai.
- `_fetch_financial_report()` — thêm `operating_cash_flow` lấy từ báo cáo LCTT.
- `_fetch_statements()` — helper dùng chung.

### Kết quả trước / sau

```
TRƯỚC (AAA)                          SAU (AAA)
  revenue_yoy:        null             revenue_yoy:        -16.07
  net_profit_yoy:     null             net_profit_yoy:       1.18
  gross_margin:       null             gross_margin:        13.92
  earnings:           {}               financial_report:
  errors: ["financials:empty"]           revenue:            2,457 tỷ
                                         net_profit_parent:    195 tỷ
                                         operating_cash_flow: -195 tỷ
                                       errors: []
```

Ngân hàng (CTG) — `gross_margin` giữ `null` đúng bản chất, YoY vẫn tính được:
`revenue_yoy +6.58` · `net_profit_yoy +36.52`.

### Còn tồn

- Balance sheet: 331 field thô đã lưu nhưng **chưa map** field nào. Cần xác minh
  trước khi dùng (tổng tài sản, vốn chủ, nợ…).
- Chứng khoán (`iss*`) và bảo hiểm (`isi*`): chưa xác minh, chỉ lưu thô.
- `financial_report.roe` vẫn `None` — có thể tính `LNST mẹ / vốn chủ bình quân`
  sau khi map được vốn chủ từ balance sheet.
