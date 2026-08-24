# Adapter cho `daily_stock_analysis` — Phân tích & Kế hoạch

Repo: https://github.com/ZhuLinsen/daily_stock_analysis
Mục tiêu: viết một adapter (data provider Python) để repo này dùng API của OpenStock, hỗ trợ thị trường VN.

## 1. Repo đó cần gì từ một data provider?

Repo là hệ thống phân tích cổ phiếu bằng LLM (Python/FastAPI). Mọi nguồn dữ liệu được trừu tượng hóa trong `data_provider/`:

- `base.py` → `class BaseFetcher(ABC)` — cho dữ liệu giá/thị trường.
- `fundamental_adapter.py` — cho dữ liệu cơ bản + dòng tiền.
- `realtime_types.py` — định nghĩa `UnifiedRealtimeQuote`, `ChipDistribution`.

Để có VN support, ta viết `OpenStockFetcher(BaseFetcher)` + `OpenStockFundamentalAdapter` gọi REST API của ta.

### Hợp đồng (contract) bắt buộc — `BaseFetcher`
| Method | Mục đích | Bắt buộc |
|---|---|---|
| `_fetch_raw_data(code, start, end) -> DataFrame` | OHLCV thô | ✅ |
| `_normalize_data(df, code) -> DataFrame` | chuẩn hóa cột `[date, open, high, low, close, volume, amount, pct_chg]` | ✅ (nội bộ) |
| `get_daily_data(...)` | lịch sử OHLCV (base gọi 2 hàm trên) | ✅ |
| `get_realtime_quote(code) -> UnifiedRealtimeQuote` | giá realtime + định giá | ✅ |
| `get_stock_name(code) -> str` | tên công ty | ✅ |

### Optional (tăng chất lượng phân tích) — `BaseFetcher`
`get_main_indices`, `get_market_stats`, `get_sector_rankings`, `get_concept_rankings`, `get_hot_stocks`, `get_limit_up_pool`, `get_chip_distribution`, `get_belong_board`.

### `OpenStockFundamentalAdapter`
| Method | Trả về |
|---|---|
| `get_fundamental_bundle(code)` | growth (revenue_yoy, net_profit_yoy, roe, gross_margin), `financial_report`, `dividend`, `forecast_summary`, `institution_holding_change`, `top10_holder_change` |
| `get_capital_flow(code, top_n)` | dòng tiền (với VN = khối ngoại mua/bán ròng) |
| `get_dragon_tiger_flag(code, lookback)` | bảng "long hổ" — đặc thù TQ, **N/A cho VN** (stub rỗng) |

`UnifiedRealtimeQuote` cần: `price, change_pct, change_amount, volume, amount, volume_ratio, turnover_rate, amplitude, open/high/low/pre_close, pe_ratio, pb_ratio, total_mv, circ_mv, change_60d, high_52w, low_52w`.

## 2. Bảng đối chiếu với API hiện tại của OpenStock

Trạng thái: ✅ đủ · 🟡 thiếu một phần (cần bổ sung field/endpoint) · ❌ chưa có · ⬛ không áp dụng cho VN

| Contract | Endpoint hiện có | Trạng thái | Ghi chú |
|---|---|---|---|
| OHLCV lịch sử | `GET /stocks/:symbol/candles` (`/daily`) | 🟡 | Thiếu `amount` (giá trị GD) và `pct_chg`. `pct_chg` suy ra được; `amount` nên thêm vào candle. |
| `get_realtime_quote` | `GET /stock/quote` | 🟡 | Có price/change/%change/volume/OHLC/prevClose. **Thiếu**: pe, pb, market cap, 52w high/low, turnover_rate, volume_ratio, amount. Phần lớn đã có trong DB nhưng không nằm trong quote. |
| `get_stock_name` | `GET /search?q=` | ✅ | Trả symbol+name. |
| `get_fundamental_bundle` (pe/pb/roe/eps/marketCap) | `GET /fundamentals/:symbol/overview` | ✅ | Service đã trả pe, pb, roe, epsTTM, bvps, marketCap, dividendYield. |
| → growth: revenue_yoy, net_profit_yoy, gross_margin | `GET /stocks/:symbol/financials` | 🟡 | Có BCTC theo kỳ; YoY/biên gộp cần tính (thêm field tổng hợp). |
| → `financial_report` (revenue, net_profit, OCF, roe) | `GET /stocks/:symbol/financials` | ✅ | Có sẵn. |
| → `dividend` (cash events + TTM) | — | 🟡→❌ | DB có `dividend_amount`, `corporate_actions(DIVIDEND...)`, `dividendPerShare`. **Chưa có endpoint** expose. Cần `GET /stocks/:symbol/dividends`. |
| → `institution_holding_change`, `top10_holder_change` | — | 🟡→❌ | DB có `ownership_snapshots`, `major_shareholders`. Có trong `dashboard/stocks/:symbol` nhưng **không có endpoint riêng**. Cần `GET /stocks/:symbol/ownership`. |
| → `forecast_summary`, `quick_report_summary` | — | ❌ | Khái niệm earnings guidance — VN ít chuẩn hóa. Để trống/None (fail-open). |
| `get_capital_flow` (khối ngoại) | — | 🟡→❌ | DB/VCI có `foreignBuyVol/foreignSellVol`; lưu trong realtimeCollector + ownership. **Chưa expose**. Cần `GET /stocks/:symbol/capital-flow` (net khối ngoại theo ngày). Đây là tín hiệu rất quan trọng cho VN. |
| `get_dragon_tiger_flag` | — | ⬛ | Đặc thù TQ. Adapter trả `{}`. |
| `get_main_indices` | `GET /dashboard/market/overview` | 🟡 | Có index data (VNINDEX...) nhưng cần endpoint indices gọn `GET /indices`. |
| `get_market_stats` | `GET /dashboard/market/overview` | ✅ | Advancers/decliners/breadth. |
| `get_sector_rankings` | `GET /sectors`, `/sectors/:sector/valuation` | 🟡 | Có sector + valuation; thiếu top tăng/giảm theo ngành. |
| `get_concept_rankings` | `GET /sectors` | 🟡 | Map "concept board" (TQ) → ngành VN; chấp nhận gần đúng. |
| `get_hot_stocks` | `GET /dashboard/market/leaders` | ✅ | Top movers. |
| `get_limit_up_pool` | `GET /dashboard/market/leaders` / screener | 🟡 | VN có giá trần/sàn (ceiling). Cần lọc % thay đổi ≈ biên độ trần. Suy ra được, hoặc thêm filter. |
| `get_chip_distribution` | — | ⬛/❌ | Khái niệm TQ (phân bố chip theo giá vốn). Khó dựng đúng. Adapter trả `None`. |
| `get_belong_board` | `GET /fundamentals/:symbol/overview` | ✅ | Overview có sector/industry. |
| (Bonus) News + sentiment cho LLM | `GET /news/market`, `/stocks/:symbol/news`, `/news-sentiment` | ✅ | Repo tự lo news, nhưng ta có thể cấp luôn → tăng chất lượng. |
| (Bonus) Technical indicators / signals | `GET /technical/:symbol/indicators`, `/signals/...` | ✅ | Repo tự tính, nhưng ta có sẵn — có thể dùng kiểm chứng. |

### Kết luận đối chiếu
- **Hợp đồng lõi (giá + quote + tên + cơ bản): ĐÁP ỨNG ĐƯỢC** với chỉnh sửa nhỏ. Adapter có thể chạy ngay ở mức cơ bản.
- Phần lớn "gap" thực ra là **dữ liệu đã có trong DB nhưng chưa expose qua REST** (dividends, ownership, foreign flow). Công việc chính là *thêm endpoint*, không phải thu thập dữ liệu mới.
- Một số method là **đặc thù Trung Quốc** (dragon-tiger, chip distribution) → adapter stub, không cần làm.

## 3. Kế hoạch bổ sung OpenStock (theo ưu tiên)

### Phase 0 — Adapter MVP (không đổi backend)
Viết `OpenStockFetcher` + `OpenStockFundamentalAdapter` chỉ dùng endpoint sẵn có:
- `_fetch_raw_data` → `/stocks/:symbol/candles?from&to` (tính `pct_chg`, `amount=close*volume` tạm).
- `get_realtime_quote` → ghép `/stock/quote` + `/fundamentals/:symbol/overview` (lấy pe/pb/marketCap/roe).
- `get_stock_name` → `/search`.
- `get_fundamental_bundle` → `/fundamentals/:symbol/overview` + `/stocks/:symbol/financials`.
- Các method TQ → stub.
- Thêm `name`, `priority`, đăng ký vào registry `data_provider/__init__.py`; cấu hình base URL + symbol routing (VN: HOSE/HNX/UPCOM 3 ký tự).
→ **Cho ra adapter chạy được, đủ để LLM phân tích cổ phiếu VN.**

### Phase 1 — Bổ sung endpoint từ dữ liệu đã có (high value, low cost)
> **Nền tảng dùng chung với realtime signals**: phần lớn các mục dưới đây được chuẩn bị trong
> [realtime_signals.md §10](realtime_signals.md) (persist `value`/foreign/ceiling-floor mà worker
> đã fetch sẵn nhưng đang vứt đi). Làm realtime signals V1 là gần như xong dữ liệu cho Phase 1 này.

1. `GET /stocks/:symbol/dividends` — từ `corporate_actions` + `dividendPerShare/Yield`. → lấp `dividend`.
2. `GET /stocks/:symbol/ownership` — từ `ownership_snapshots` + `major_shareholders`. → lấp `institution_holding_change`, `top10_holder_change`.
3. `GET /stocks/:symbol/capital-flow?days=N` — net khối ngoại theo ngày từ `stock_prices.foreign_net_value` (persist ở realtime §10.1). → lấp `get_capital_flow` (rất quan trọng cho VN).
4. Mở rộng `/stock/quote`: thêm `pe, pb, marketCap, high52w, low52w, turnoverRatio, volumeRatio, foreignNet, change60d` (realtime §10.3). → quote một-lần-gọi đầy đủ cho `UnifiedRealtimeQuote`.
5. Thêm `amount` (giá trị GD thực) vào candle output thay vì ước lượng (`stock_prices.amount`, realtime §10.1).
6. `GET /dashboard/market/ceiling-floor` — cổ phiếu trần/sàn từ tín hiệu CEILING/FLOOR (realtime §10.2). → lấp `get_limit_up_pool`.

### Phase 2 — Endpoint thị trường (medium value)
7. `GET /indices` — VNINDEX/VN30/HNX-INDEX/UPCOM realtime + % → `get_main_indices`.
8. Mở rộng `/sectors`: thêm top gainers/losers mỗi ngành → `get_sector_rankings`.
   (Ceiling/floor pool → đã chuyển lên Phase 1 item 6.)

### Phase 3 — Nâng cao (optional)
9. 52-week range + `change_60d` precompute (worker) nếu chưa có để quote nhanh.
10. Quyết định bỏ hẳn `chip_distribution`/`dragon_tiger` (đặc thù TQ) — document là không hỗ trợ.

## 4. Việc cần xác nhận trước khi code
- Adapter đặt ở repo nào: fork `daily_stock_analysis` hay 1 thư mục `adapters/` trong OpenStock? (đề xuất: fork repo đó, vì adapter là Python theo contract của họ).
- Quy ước mã CK: họ dùng `600519`; VN dùng `FPT/VNM`. Adapter cần nhận diện symbol VN và route sang base URL OpenStock.
- Có cần auth không khi adapter gọi (hầu hết endpoint của ta là public, chỉ watchlist cần session) → adapter chỉ dùng public endpoint nên OK.
