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
| `data_provider/base.py` | `_is_vn_market()` (~193) | HOOK | nhận diện mã VN, gate sau `openstock_enabled` | giữ; nguồn sự thật giờ là **symbol universe** từ `GET /stocks` của OpenStock (cache 6h, fail-open về regex) — xem §1.1c |
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

### 1.1c Quote enrich + market methods + symbol universe (2026-08-24)

**Bối cảnh:** rà lại code OpenStock hiện tại (thay vì đọc gap-doc từ 2026-06-25) thì
phần lớn "gap" đã được OpenStock làm xong, chỉ adapter chưa dùng.

| Việc | Trạng thái |
|---|---|
| `get_realtime_quote` dùng `/stock/quote?enrich=true` | ✅ 1 call thay vì 2. `getEnrichedQuote()` bên OpenStock có docstring ghi rõ *"Used to build a complete UnifiedRealtimeQuote for the daily_stock_analysis adapter"* — viết cho chính adapter này. Map thêm `volume_ratio`, `turnover_rate`, `change_60d`, `high_52w`, `low_52w`. **3 field đầu render trực tiếp trong bảng prompt** (`src/analyzer.py` ~3432–3438) nên trước đây mọi báo cáo VN đều hiện `N/A`. Giữ fallback về `/fundamentals/:symbol/overview` nếu server chưa hỗ trợ `enrich` |
| `get_market_stats` | ✅ từ `breadth` của `/dashboard/market/overview`. `limit_up/down_count` dùng số mã chạm trần/sàn (VN không có khái niệm 涨停 như A-share) |
| `get_sector_rankings` | ✅ từ `sectorLeadership.all` |
| `get_hot_stocks` | ✅ từ `/dashboard/market/leaders?tab=movers` |
| `get_limit_up_pool` | ✅ từ `/dashboard/market/ceiling-floor` (nhánh `ceiling`) |
| `src/core/market_profile.py` `VN_PROFILE` | ⚠️ **BRANCH bắt buộc**: bật `has_market_stats=True`, `has_sector_rankings=True`. Nếu để `False` thì 2 method trên thành dead code — **đúng loại bug đã gặp ở Phase 1** |
| `openstock_symbols.py` symbol universe | ✅ `GET /stocks` làm nguồn sự thật, cache 6h + backoff 60s khi lỗi, fail-open về regex. **Đã kiểm chứng trên DB thật (3616 mã)** — xem ô dưới về phạm vi thật sự |
| ↳ phạm vi thật của universe | **Đóng được**: false-negative ETF (`E1VFVN30`, `E1VFVN31`, `FUEABVND`, `FUEBFVND`, `FUEDCMID`, `FUEFCV50`, `FUEVFVND`… đều có trong `stocks`), và false-positive với mã Mỹ không trùng (`IBM`, `KEY`, `GEV` → 0 dòng). **KHÔNG đóng được**: (a) **phái sinh** — `stocks` có **0 dòng** `VN30Fxxxx`, futures không được sync (regex cũ cũng không khớp nên không hồi quy, chỉ là giới hạn còn nguyên); (b) **mã trùng thật** — `AMD`, `SSI`, `VIC` **đều là mã HOSE thật**, nên không cách nào phân biệt bằng symbol đơn lẻ, phải dùng suffix tường minh (`FPT.VN` / `AMD.US`) nếu muốn phục vụ đồng thời VN và US. (c) **chỉ số** — `stocks` có 0 dòng `VNINDEX`/`VN30`, nên `is_vn_index_code()` **phải** được kiểm TRƯỚC universe; đảo thứ tự sẽ làm chỉ số không nhận được |
| `VN_INDEX_MAPPING` | ✅ bỏ `HNX30` (OpenStock **không** sync), thêm `VN100` (có sync). Trước đây adapter nhận `HNX30` là mã hợp lệ rồi query rỗng |

Test khoá lại: `tests/test_openstock_market_methods.py` (13 test).

**Sửa lại kết luận Phase 2b:** lúc đó tôi ghi "OpenStock không có endpoint liệt kê mã"
dựa trên plan doc mà **chưa đọc code OpenStock**. Thực tế: có route `/tv/symbols`
nhưng chỉ là **stub TradingView** (`return { /* map from stocks + company_overview */ }`),
còn bảng `stocks` thì đã đầy đủ. Việc thêm `GET /stocks` chỉ tốn ~35 dòng — rẻ hơn
nhiều so với giả định lúc đó.

### 1.1d Touchpoint bat buoc khi fork them ngon ngu / region

Ba cho nay **phai cap nhat cung luc** khi fork them `vi` hoac `vn`, neu khong se
vo lúc chay (khong phai canh bao):

| File | Vi sao bat buoc |
|---|---|
| `src/services/empty_news.py` `_DISCLOSURES` | Upstream guard `if set(_DISCLOSURES) != set(SUPPORTED_REPORT_LANGUAGES): raise RuntimeError` chay **luc import**. Quen -> 186 RuntimeError + 88 ImportError day chuyen. |
| `tests/test_notification_empty_news_disclosure.py` `EXPECTED` | Test upstream duyet `SUPPORTED_REPORT_LANGUAGES` roi tra `EXPECTED[language]` -> KeyError. |
| `tests/test_market_review.py` (test `both`) | Cung goc: `both` co them vn nen (a) assert list region thieu 'vn', (b) `side_effect` chi mock 5 MarketAnalyzer -> region thu 6 gay StopIteration -> `result=None` -> TypeError. |
| `tests/test_stock_index_loader.py` (`test_default_candidate_paths_prefer_remote_cache`) | Fork doi mac dinh chi muc sang `stocks.index.vn.json` nen assert ten file cua upstream do. Da ghim `STOCK_INDEX_MARKET=cn` trong test do — no kiem THU TU duong dan, khong phai ten file. Che do vn co test rieng. |
| `tests/test_config_env_compat.py` (2 assert) | Fork them `vn` vao `MARKET_REVIEW_REGION_ORDER` nen `both` mo rong thanh `cn,hk,us,jp,kr,vn`. Assert cua upstream ky vong khong co `vn`. Day la **doi hanh vi co chu y** cua fork, khong phai bug. |


> **Bay thu tu region**: fork dat `vn` **dau tien** trong
> `src/core/market_review.py::_MARKET_REVIEW_MARKETS` (VN-first, thu tu CHAY va
> thu tu HIEN trong bao cao) nhung `vn` **cuoi cung** trong
> `src/utils/market_review_region.py::MARKET_REVIEW_REGION_ORDER` (thu tu
> chuan hoa chuoi region). Hai thu tu nay KHAC NHAU co chu y. Khi mock
> `MarketAnalyzer` bang `side_effect=[...]` phai theo thu tu cua
> `_MARKET_REVIEW_MARKETS` (vn, cn, hk, us, jp, kr), khong phai theo
> `MARKET_REVIEW_REGION_ORDER`.

### 1.1e Frontend: `vi` la overlay tren `en`, khong phai bang day du

`apps/dsa-web/src/i18n/uiText.ts`:

```ts
const viOverrides: Partial<Record<UiTextKey, string>> = { ... }
const vi: Record<UiTextKey, string> = { ...en, ...viOverrides }
```

Ly do: `t()` tra thang `UI_TEXT[lang][key]`, thieu key -> UI hien chu `undefined`.
Moi lan merge upstream ho them hang chuc key; bat buoc `vi` du thi build vo ngay.
Phu len `en`: key da dich -> tieng Viet, chua dich -> tieng Anh (dung duoc).
`VI_TRANSLATION_COVERAGE` theo doi tien do (659/934 sau catch-up v3.31.0).

**QUAN TRONG**: chay `npm install` truoc khi tin ket qua `tsc`. Neu node_modules
co tsc cu hon `package.json` yeu cau thi `tsc -p` chi bao loi OPTION roi dung —
KHONG typecheck file nao, va moi loi that bi che. Da xay ra: tsc 5.0.4 vs yeu cau
5.9.3 che mat 17 loi.

### 1.1f Quy tac vang: KHONG BAO GIO xoa literal cua upstream

Do luong "so literal tieng Trung bi MAT HAN" (co trong dong `-`, khong co trong
bat ky dong `+` nao) la thuoc do no merge chinh xac nhat cua fork nay.

    git diff upstream/main -- <file>

`analyzer.py`: 166 literal mat -> 6 (deu la duong tinh gia cua regex).

Bon cach hop le de them tieng Viet, xep theo do uu tien:

| # | Cach | Vi du | Khi nao |
|---|---|---|---|
| 1 | Them khoa `vi` vao bang co san | `{"zh": "买入", "en": "Buy", "vi": "Mua"}` | Upstream da co bang theo ngon ngu |
| 2 | Them tham so `vi=` | `_localized_text(lang, en=..., zh=..., ko=..., vi=...)` | Upstream dung helper chon ngon ngu |
| 3 | Nhanh moi ben canh | `if lang == "vi": ... elif lang == "zh": ...` | Doan van dai, nhieu bien |
| 4 | Bang tra cuu ngoai tree | `_L("开盘价")` + `PROMPT_LABELS_VI` | Nhieu nhan nam trong f-string lon |

**PHAN DIEN HINH SAI** — da gap that trong fork nay:

```python
# SAI: dao dieu kien, nhanh `else` nuot ca zh/ko
return "Capital flow unsupported" if language == "en" else "Dich vu dong tien..."

# SAI: ghi de vo dieu kien, moi ngon ngu deu nhan tieng Viet
add("quote", "## 📈 Dữ liệu kỹ thuật")

# SAI: dich thang trong ham upstream, xoa han ban goc
def _phase_aware_quote_labels(context):
    return "Diễn biến hôm nay", "Giá đóng cửa"   # mat "今日行情", "收盘价"
```

Ca ba deu (a) lam `REPORT_LANGUAGE=zh|en|ko` nhan tieng Viet, (b) lam test cua
upstream do, (c) tao conflict moi lan upstream cham vao dong do.

### 1.1g `src/analyzer_prompts_vi.py` — ban tieng Viet cua prompt he thong

`LEGACY_DEFAULT_SYSTEM_PROMPT`, `SYSTEM_PROMPT`, `TEXT_SYSTEM_PROMPT` (~377 dong)
nam o day; `analyzer.py` giu nguyen ban tieng Trung cua upstream va chon qua
`GeminiAnalyzer._vn_system_prompt_templates(lang)`.

Khi upstream doi prompt: merge `analyzer.py` khong conflict, roi cap nhat ban
dich o day neu muon. Khong cap nhat cung khong vo — chi la prompt tieng Viet
cu hon ban tieng Trung mot chut.

Cung file nay giu `PROMPT_LABELS_VI` (bang tra nhan, khoa = literal tieng Trung)
va `price_unit()` (hau to " 元": bo cho `vi`, giu cho ngon ngu khac).

### 1.1h Cac file fork tu so huu (them ngon ngu / thi truong VN)

Toan bo du lieu tieng Viet nam trong nhung file nay. `git merge upstream/main`
KHONG BAO GIO dinh conflict o day vi upstream khong biet chung ton tai.

| File fork | Phu cho | Co che |
|---|---|---|
| `src/report_language_vi.py` | `src/report_language.py` | `register()` tiem vao dict cua upstream. Gom `VI_FLAT_BY_LANGUAGE` cho cac dict phang `{lang: text}` (thieu khoa = KeyError luc chay). |
| `src/analyzer_prompts_vi.py` | `src/analyzer.py` | 3 hang prompt he thong + `PROMPT_LABELS_VI` (khoa = literal tieng Trung) + `price_unit()`. |
| `src/market_context_vi.py` | `src/market_context.py` | Ban dich `vi` cho 6 thi truong upstream + thi truong `vn` moi (bien do ±7%, T+2, foreign room). |
| `src/market_phase_prompt_vi.py` | `src/market_phase_prompt.py` | `_EXTRA_FORMATTERS` registry. |
| `src/market_phase_summary_vi.py` | `src/market_phase_summary.py` | `_EXTRA_*_LABELS` registry. |
| `src/trend_text_vi.py` | `src/stock_analyzer.py` | Dich o BIEN prompt — KHONG dich tai cho vi `_infer_trend_direction()` **parse** `ma_alignment`. |
| `src/core/pipeline_progress_vi.py` | `src/core/pipeline.py` | Bang `PROGRESS_VI`, khoa = template tieng Trung CHUA noi suy. |
| `api/v1/messages_vi.py` | `api/v1/endpoints/*`, `api/middlewares/error_handler.py` | `msg()` doc ngon ngu tu Config; khoa = literal tieng Trung. |

Ba nguyen tac chung cho moi bang tra cuu tren:

1. **Khoa la literal tieng Trung cua upstream**, giu nguyen tai cho trong file
   upstream. Merge de hon, va doc code van thay duoc ban goc.
2. **Khoa chua dich -> tra ve nguyen van**, khong bao gio `KeyError`. Thay sai
   ngon ngu de phat hien hon nhieu so voi phan tich bi vo.
3. **Khoa la template CHUA noi suy** (`"{code}：..."`), khong phai chuoi da
   format. Tra cuu la so sanh chuoi chinh xac, khong phai khop tien to mong manh.

Moi bang deu co test quet nguoc: khoa nao khong con ton tai trong file upstream
thi do ngay (upstream doi thong bao -> phat hien lien, khong am tham thoi dich).

### 1.1i Chi muc autocomplete — MAC DINH la thi truong VN

`stocks.index.json` cua upstream co ~31.700 muc CN/HK/US/JP/KR va **khong co MOT
ma VN nao** — ke ca VNINDEX lan FPT/VIC. Hau qua truoc khi sua:

  * go "FPT" trong o tim kiem khong ra goi y nao;
  * lich su phan tich hien `FPT(FPT)`, `HPG`, `KSB` tran trui vi khong tra duoc
    ten day du (nhung ma CO ten la do LLM/OpenStock tra ve, khong phai tu chi muc).

Repo nay phuc vu thi truong VN nen **mac dinh la `vn`**:

| Bien | Mac dinh | Doi ve upstream |
|---|---|---|
| `STOCK_INDEX_MARKET` (Python) | `vn` -> `stocks.index.vn.json` | `cn` -> `stocks.index.json` |
| `VITE_STOCK_INDEX_MARKET` (frontend) | `vn` | `cn` |

**Hai bien phai dat GIONG NHAU.** Lech nhau thi frontend va backend tra ten khac
nhau cho cung mot ma.

File fork tu so huu:
  * `scripts/generate_vn_index.py` — sinh chi muc tu OpenStock `GET /stocks`
    (3.616 ma) + seed chi so.
  * `scripts/stock_index_seeds/vn_index_registry.csv` — 5 chi so VN (VNINDEX,
    VN30, VN100, HNXINDEX, UPCOMINDEX).
  * `src/data/stock_index_market.py` — cong tac chon thi truong.
  * `apps/dsa-web/public/stocks.index.vn.json` + `static/...` — dau ra (sinh lai
    duoc, khong sua tay).

Hook trong file upstream chi 2 cho, deu nho:
  * `src/data/stock_index_loader.py::get_stock_index_candidate_paths()` — doi ten
    file theo thi truong.
  * `apps/dsa-web/src/utils/stockIndexLoader.ts` — them `stockIndexFilename()`.

**VI SAO KHONG dung registry chi so moi cua upstream** (`generate_index_from_csv.py
--index-only`, them o commit 1b429076): no khoa cung cho A-share —

```python
if not _INDEX_NAMESPACE_RE.match(canonical):   # ^(sh|sz|csi)\d{6}$
    raise ValueError(...)
if market != "CN":
    raise ValueError(f"index market must be CN: {canonical!r}")
```

`VNINDEX` truot ca hai. Nhet ma VN vao do buoc phai sua validator cua upstream —
dung kieu ghi de ma muc 1.1f cam.

**BAY**: `run_index_only()` **xoa sach moi dong `assetType=index`** roi ghi lai tu
seed cua chinh no. Neu ai do them chi so VN thang vao `stocks.index.json`, lan
chay `--index-only` ke tiep se xoa mat ma khong bao gi. Do la ly do thu hai phai
dung file RIENG.

Sinh lai chi muc (can OpenStock dang chay o :3000):

```bash
python scripts/generate_vn_index.py          # ghi file
python scripts/generate_vn_index.py --test   # chi kiem tra
```

**Khoang trong da biet**: 1.896/3.616 ma trong OpenStock co `name == symbol`
(khong co ten that) nen bi loc khoi *name map*, tuy van dung duoc cho autocomplete.
Trong so do 218 ma co the va them tu bang `company_overview` — chua lam.

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
| `src/report_language.py` | HOOK ✅ **(Phase 3b xong)** | **13 hunk → 1 hunk.** Toàn bộ dữ liệu `vi` chuyển sang `src/report_language_vi.py` và tiêm lúc import. Còn 3 điểm chạm: `SUPPORTED_REPORT_LANGUAGES` (+`"vi"`), registry `_SENTIMENT_LABEL_BANDS`, gọi `_register_vi()`. Hunk còn lại nằm đúng ở dòng khai báo ngôn ngữ — merge bằng cách giữ cả hai: `("zh","en","ko","vi")`. Test: `tests/test_report_language_vi_coverage.py` (11) |
| `src/market_phase_prompt.py` | HOOK ✅ **(Phase 3a+3c xong)** | +29/−29 ghi đè → +18/−1 registry `_EXTRA_FORMATTERS`. `vi` ở `src/market_phase_prompt_vi.py`. **`zh` đã phục hồi** → `ko` của upstream không còn nhận tiếng Việt. `tests/test_market_phase_prompt.py` 8 lỗi → 11/11 xanh |
| `src/market_phase_summary.py` | HOOK ✅ **(Phase 3a+3c xong)** | +22/−22 ghi đè → +32/−3 registry 5 bảng nhãn. `vi` ở `src/market_phase_summary_vi.py` (thuần dữ liệu) |
| `src/analyzer.py` | BRANCH + **OVERWRITE** | **15 hunk xung đột**. Nhánh chỉ thị output `vi` = giữ; phần dịch scaffold tại chỗ = bỏ |
| `src/market_analyzer.py` | **OVERWRITE** | +138/−138 = thay 1:1 literal. **13 hunk.** Phase 3a: `git checkout vendor --` |
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
| File xung đột khi merge v3.31.0 | 28 | **28**² | ≤ 10 |
| Hunk xung đột | 98 | **100**² | ≤ 25 |

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

² Số đếm gần như không đổi (28 file / +2 hunk), NHƯNG chất lượng xung đột ở
`data_provider/base.py` tốt hơn hẳn nhờ Phase 2b — kiểm chứng bằng merge thật:
upstream v3.31.0 (chưa release lúc viết tài liệu này, thấy ở `upstream/main`)
đã tự thêm **thị trường Đài Loan** (`is_tw`/`_is_tw_market`/`market == "tw"`)
đúng vào NHỮNG DÒNG mà Phase 2b vừa dọn. Trước Phase 2b: phải tách `is_tw` thủ
công ra khỏi 2 chuỗi boolean lồng nhau độc lập ở 2 hàm khác nhau. Sau Phase 2b:
chỉ cần thêm `if _is_tw_market(code): return "tw"` một lần trong `_market_tag()`
và `is_tw = market == "tw"` ở 2 call site — không còn phải object với logic
`(not is_us) and (not is_hk) and ...` của upstream. Đây chính là lợi ích
"tập trung hoá" nói ở đầu tài liệu, giờ có bằng chứng thật từ merge thử.
