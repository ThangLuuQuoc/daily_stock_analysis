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
