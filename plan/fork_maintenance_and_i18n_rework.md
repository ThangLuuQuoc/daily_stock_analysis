# Fork `daily_stock_analysis` — Review upstream delta, adapter OpenStock & i18n VI

Ngày: 2026-08-24
Upstream: https://github.com/ZhuLinsen/daily_stock_analysis
Base snapshot của bản local: commit **`ecf87ea0`** (2026-06-24, giữa v3.23.0 và v3.24.0)
Upstream HEAD lúc review: **v3.31.0** (`9ab79b82`, 2026-08-23)

> Cách xác định base (repo local không có git): so `git hash-object` của các file không
> sửa với blob sha của upstream qua GitHub API. `main.py` local = `f691f6a1…` = upstream
> tại `35943d7f` (2026-06-22); tập file "A" (added) chỉ còn đúng các file của ta khi lấy
> base = `ecf87ea0`. Toàn bộ số liệu dưới đây đo bằng 3-way merge thật (`git merge`)
> giữa base / local / upstream main.

---

## 0. Tóm tắt kết luận

| Hạng mục | Kết luận |
|---|---|
| Adapter OpenStock (file mới) | ✅ **Tốt** — đúng contract, feature-flag, 0 xung đột merge |
| Wiring adapter vào pipeline | ❌ **Có bug chặn tính năng** — `OpenStockFundamentalAdapter` là dead code |
| Bề mặt sửa file upstream | ⚠️ **Quá rộng** — 65 file bị sửa → 28 file xung đột / ~101 hunk khi merge lên v3.31.0 |
| i18n tiếng Việt (lớp UI text) | ✅ **Tốt** — `uiText.ts` type-safe, `featureText.ts`, labels `vi` |
| i18n tiếng Việt (lớp prompt/context) | ❌ **Sai kiến trúc** — ghi đè tại chỗ slot `zh`, làm hỏng test và rò tiếng Trung về sau |
| Quản lý fork | ❌ **Không có git** → không merge được, không revert được, không biết đã sửa gì |

Ưu tiên: **P0 = git + vendor branch** → **P1 = fix dead code fundamental** →
**P2 = thu hẹp bề mặt sửa** → **P3 = làm lại i18n theo pattern `ko` của upstream** →
**P4 = catch up v3.31.0**.

---

## 1. Upstream có gì mới hơn bản của ta

Khoảng cách: **2 tháng, 8 release (v3.24.0 → v3.31.0), 585 file thay đổi,
+130.097 / −9.728 dòng**, 196 file mới.

### 1.1 Theo release (đánh dấu mức liên quan tới deployment VN)

| Release | Nội dung chính | Với ta |
|---|---|---|
| **3.24.0** (06-28) | Thị trường Đài/Nhật/Hàn (suffix-only + tư liệu 三大法人); abstraction `GenerationBackend`; `codex_cli` backend; prompt-cache capability registry; multi-time scheduling + runtime scheduler hot-reload; signal attribution, timeline tín hiệu 1 mã, xếp hạng concept board | 🟡 Scheduler + signal attribution dùng được ngay |
| **3.25.0** (07-03) | `claude_code_cli` / `opencode_cli` backend + panel trạng thái/smoke API; **báo cáo tiếng Hàn (`ko`)**; thông báo DingTalk; `/chat/stream` chuẩn hoá progress event | 🔴 **`ko` là tiền lệ i18n chính thức của upstream — pattern ta phải bám theo** |
| **3.26.1** (07-12) | Web home có workspace Lịch sử / Tự chọn / Hôm nay; phân tích theo lô; xếp hạng điểm; market-structure + context chủ đề; Feishu đẩy report dạng file; DSA Tool Surface | 🟡 UX đáng lấy |
| **3.27.0** (07-19) | Codex App Server single-agent prototype; multi-strategy structured opinion (phase 1); fix MiniMax `<think>` làm bẩn JSON; bổ sung PE/PB realtime cho US | 🟡 Fix `<think>` hữu ích nếu dùng model rẻ |
| **3.28.0** (07-26) | Multi-Agent deliberation phân lớp + mediator/self-review + multi-round; AI-advice theo decision style; `--portfolio futu`; **trigger market review theo từng market không cần đổi config global** | 🔴 Trigger theo market rất hợp ta (đang phải set `MARKET_REVIEW_REGION=vn` toàn cục) |
| **3.29.0** (08-02) | **Chọn cổ phiếu (screening) kiểu AlphaSift đưa hẳn vào core**: `src/services/screening/*` (~20 module), history run, deep-analysis ứng viên; ảnh chia sẻ 1080px; Skill Opinion Outcome + runtime weight | 🔴 **Giá trị cao nhất cho VN** — nhưng cần data path VN (screener trên OpenStock) |
| **3.30.0** (08-09) | LLM channel khai báo rõ **Chat Completions vs Responses API surface** (thống nhất route cho connection test / analysis / screening / image); Agent Chat lưu Skill theo session; Desktop restore history + share ảnh; **contract phân giải target phân tích đơn lẻ (siết chuẩn hoá suffix sàn / alias chỉ số / mã US)** | 🔴 API surface ảnh hưởng gateway local (freellmapi / OmniRoute); ⚠️ siết chuẩn hoá mã **đụng trực tiếp** nhận diện mã VN 3 chữ |
| **3.31.0** (08-23) | Timeout tool theo category + graceful degradation; **stock name resolution + `canonical_id` double-write**; fallback nhiều nguồn cho chỉ số A-share; ghi rõ khi tìm tin trống; **fix CVE-2026-54673**; xAI Grok | 🔴 CVE là lý do không nên tụt hậu 2 tháng; ⚠️ `canonical_id` lại là một điểm phải hook VN |

### 1.2 Hai điều quan trọng nhất rút ra

1. **Upstream không có và sẽ không có Việt Nam.** `grep -ri "vietnam|越南|VN_NEWS"` trên
   upstream main = **0 hit**. VN sẽ luôn là fork → phải đầu tư vào *khả năng merge*,
   không phải chờ upstream.
2. **Upstream đang siết chuẩn hoá mã chứng khoán** (3.30.0 target-resolution contract,
   3.31.0 `canonical_id` + name resolver, `src/services/market_symbol_utils.py`,
   `stock_list_parser.py`, `name_to_code_resolver.py`). `is_us_stock_code()` của họ =
   **1–5 chữ in hoa** → mã VN 3 chữ là tập con. Mỗi resolver mới upstream thêm là một
   chỗ nữa ta phải chèn "VN trước US". Đây là khoản thuế tăng dần → phải tập trung hoá.

---

## 2. Review adapter OpenStock

### 2.1 Số liệu bề mặt fork (đo bằng merge thật)

```
local vs base (ecf87ea0):     78 file   +5.960 / -1.555
  |- 13 file MOI (cua ta)            -> 0 xung dot
  |- 65 file SUA cua upstream        -> nguon xung dot

base -> upstream main:       585 file   +130.097 / -9.728

Trial merge (upstream main -> local):
  28 file xung dot, ~101 hunk
```

Top file xung đột:

| File | Hunk xung đột | Upstream thay đổi |
|---|---|---|
| `src/analyzer.py` | 15 | +915 / −126 |
| `src/report_language.py` | 13 | +538 / −28 |
| `src/market_analyzer.py` | 13 | +714 / −165 |
| `apps/dsa-web/src/pages/ChatPage.tsx` | 11 | +320 / −61 |
| `data_provider/base.py` | 6 | +690 / −79 |
| `apps/.../StockAutocomplete.tsx` | 5 | +24 / −4 |
| `src/core/market_review.py` | 4 | +311 / −26 |
| 21 file còn lại | 1–3 mỗi file | — |

Cách tái lập (khi repo local vẫn chưa có git):

```bash
curl -sSL -o base.tgz https://codeload.github.com/ZhuLinsen/daily_stock_analysis/tar.gz/ecf87ea0107f1394c7e7f2c0e21362a70c0244d1
```

Sau đó: `git init` một repo tạm, commit base, tạo branch `ours` (copy local) và
`theirs` (copy upstream main), rồi `git merge theirs` và đọc
`git diff --name-only --diff-filter=U`.

### 2.2 Những gì làm ĐÚNG (giữ nguyên, dùng làm mẫu)

- **File mới, không sửa file upstream**: `data_provider/openstock_fetcher.py`,
  `openstock_fundamental_adapter.py`, `openstock_symbols.py`. Đúng contract
  `BaseFetcher` (`_fetch_raw_data` / `_normalize_data` / `get_realtime_quote` /
  `get_stock_name`), có `name` / `priority`, `DataFetchError`, stub cho method đặc thù
  Trung Quốc. Docstring/log tiếng Trung theo đúng house style của upstream → merge dễ,
  PR ngược lên upstream cũng khả thi.
- **Feature flag `OPENSTOCK_ENABLED`** mặc định `false` → nhánh code chết khi tắt.
- **Xử lý đơn vị rõ ràng** (giá = nghìn VND, `amount`/`marketCap` = VND đầy đủ,
  `roe` ratio → %). Đây là loại lỗi âm thầm tệ nhất, đã tránh được.
- **`src/search_service.py` — chế độ tin tức VN là pattern chuẩn mực**: thêm 2 field
  config, 3 private method mới (`_vn_scope` / `_is_vn_domain` /
  `_restrict_response_to_vn`), tất cả gate sau `if self.vn_news_enabled`. Sửa +197/−15
  vào một file upstream đổi +490/−54 mà **chỉ 3 hunk xung đột**. Nhân rộng cách này.
- **Tài liệu**: `plan/daily_stock_analysis_adapter.md` + `openstock_adapter_gaps.md` có
  bảng đối chiếu contract, gap tracking, và §6 (BCTC) ghi cả **bằng chứng xác minh mã
  field VCI** — cực kỳ đúng: thà không có dữ liệu hơn là gán nhãn sai cho số đi vào
  khuyến nghị mua/bán.

### 2.3 Vấn đề — xếp theo mức nghiêm trọng

#### P0-1 · BUG: `OpenStockFundamentalAdapter` là dead code trong pipeline thật

`data_provider/base.py::get_fundamental_context` (dòng ~3011–3017):

```python
market = _market_tag(stock_code)           # -> "vn"
if market in {"us", "hk", "jp", "kr"}:     # vn KHONG nam trong day
    return self._build_offshore_fundamental_context(...)
...
lambda: self._fundamental_adapter.get_fundamental_bundle(stock_code)   # AkshareFundamentalAdapter
```

Hệ quả cho mã VN:
- `valuation` → lấy từ `get_realtime_quote` (OpenStock) ✅
- `growth` / `earnings` / `institution` → gọi **AkShare** với `"FPT"` → rỗng/lỗi ❌
- `capital_flow` / `dragon_tiger` / `boards` → bị chặn bởi
  `if _market_tag(stock_code) != "cn"` (dòng 3304 / 3368 / 3418) → **không gọi** ❌

Nghĩa là toàn bộ công việc BCTC ở `openstock_adapter_gaps.md §6` (`revenue_yoy`,
`net_profit_yoy`, `gross_margin`, `operating_cash_flow`) **và dòng tiền khối ngoại**
— tín hiệu quan trọng nhất của thị trường VN — **không tới được LLM**. Chỉ chạy được
qua `scripts/test_openstock_adapter.py`. `grep -rn "OpenStockFundamentalAdapter"` trong
`src/` và `api/` = 0 call-site.

#### P0-2 · Không có git repository

`git rev-parse` trong repo → `fatal: not a git repository`. Không có base commit, không
merge được, không revert được, không `git blame`, không biết chính xác đã sửa gì của
upstream. Toàn bộ phân tích ở tài liệu này phải dựng lại base bằng blob-sha probing.
Đây là rủi ro process lớn nhất — mọi việc khác phụ thuộc nó.

Phụ: file rác đang nằm trong tree — `scripts/_mr_done.json`, `scripts/_mr_test.json`,
`scripts/_vn_test.json`.

#### P1-1 · Viết lại `_init_default_fetchers` (6 hunk xung đột)

Mục tiêu (không bắt buộc cài `efinance`/`akshare`/`tushare` trong deployment chỉ dùng
VN) là hợp lý, nhưng cách làm — thay hard-import bằng `_safe_instantiate` + `base_specs`
+ đổi `data_provider/__init__.py` sang `_optional_import` — là **viết lại một hàm của
upstream** trong file upstream đổi +690/−79. Đây là cách đắt nhất để đạt mục tiêu đó.

#### P1-2 · Nhận diện mã VN bằng regex

`openstock_symbols.py`: `_VN_TICKER_RE = ^[A-Z]{3}$`,
`_VN_DERIVATIVE_RE = ^[A-Z]{2,4}[0-9]{2,6}$`.

- **False positive**: mọi mã US 3 chữ (IBM, AMD, KEY, GEV…) thành mã VN. Chỉ được cứu
  nhờ `openstock_enabled` → repo **không thể phục vụ đồng thời VN và US/CN nữa**.
- **False negative**: ETF VN (`FUEVFVND`, `E1VFVN30`), hợp đồng phái sinh (`VN30F2409`).
  Chứng quyền dạng `CFPT2401` khớp `_VN_DERIVATIVE_RE` một cách tình cờ, còn `FUEVFVND`
  thì không khớp gì.
- **Phân tán**: logic "VN trước US" bị chèn ở 6 chỗ trong `base.py` (dòng 255, 1293,
  1299, 1731…). Mỗi resolver mới của upstream (3.30/3.31) là thêm một chỗ.

#### P2 · Nhỏ hơn

- `/search` endpoint chèn trực tiếp vào `api/v1/endpoints/stocks.py` của upstream, đáng
  ra nên là `api/v1/endpoints/vn_search.py` + 1 dòng `include_router`.
- Field `nameZh` chở tên công ty tiếng Việt (comment đã thừa nhận là lý do lịch sử).
- `data_provider/realtime_types.py` sửa 1 dòng — kiểm tra xem có cần thật không.

---

## 3. Review i18n / tiếng Việt

### 3.1 Kiến trúc của upstream (phải hiểu trước khi sửa)

Upstream **đã tự thêm ngôn ngữ thứ 3** ở v3.25.0: `ko`.

```python
# src/report_language.py (upstream main)
SUPPORTED_REPORT_LANGUAGES = ("zh", "en", "ko")

_REPORT_LABELS: Dict[str, Dict[str, str]] = {      # lang -> {key: text}   THAN THIEN
    "zh": {...}, "en": {...}, "ko": {...},
}

_OPERATION_ADVICE_TRANSLATIONS = {                  # key -> {lang: text}  KHO MERGE
    "buy": {"zh": "买入", "en": "Buy", "ko": "매수"},
}
```

Ba điều quyết định thiết kế:

1. **Mọi lookup đi qua function đọc dict ở module level lúc runtime**
   (`_translate_from_map`, `get_report_labels`, `localize_*`) → **overlay/inject được
   `vi` mà không sửa 1 byte nào của file upstream**.
2. `_REPORT_LABELS` là `lang → {…}` → thêm block `"vi"` ở cuối = merge tự động sạch.
   Các `*_TRANSLATIONS` là `key → {lang}` → thêm `"vi"` vào từng dòng = **xung đột từng
   dòng** với `ko` của upstream. Đây chính là 13 hunk của `report_language.py`.
3. Số điểm chạm của một ngôn ngữ mới theo cách upstream: **109 vị trí / ~15 file python**
   (`report_language.py` 61, `analyzer.py` 9, `decision_action.py` 8,
   `daily_market_context_guardrail.py` 6, `phase_decision_guardrail.py` 5,
   `share_image.py` 4, `market_review.py` 4, `pipeline.py` 3, …). Đây là chi phí sàn,
   không tránh được.

### 3.2 Những gì làm ĐÚNG

- `apps/dsa-web/src/i18n/uiText.ts` — 673 key × 3 ngôn ngữ, `UiTextKey = keyof typeof zh`
  → TypeScript ép đủ key. Thêm ngôn ngữ là thao tác type-safe. **Giữ nguyên.**
- `featureText.ts` (28 map), thay ~14 ternary `=== 'zh'` bằng `Record<UiLanguage, …>`,
  date locale tham số hoá thay vì cứng `zh-CN`. Đúng hướng.
- `_REPORT_LABELS["vi"]`, `decision_action._ACTION_LABELS["vi"]`,
  `api/v1/schemas/analysis.py` Literal thêm `"vi"` — đúng chỗ, đúng cách.
- `VN_PROFILE` / `VN_BLUEPRINT` / market `('vn', …)` trong `market_profile.py` /
  `market_strategy.py` / `market_review.py` — **additive**, đúng pattern.
- Bỏ fallback `股票{code}`, lỗi API sang English — đúng.

### 3.3 Vấn đề gốc: ghi đè tại chỗ slot `zh` (anti-pattern)

Bằng chứng cụ thể — `src/market_phase_prompt.py`:

```python
_PHASE_LABELS_ZH = {
    "premarket": "trước phiên",        # ten bien noi ZH, noi dung la VI
    "intraday":  "trong phiên",
}

def _format_zh(ctx, phase):
    lines = ["", "## Bối cảnh giai đoạn thị trường", ...]   # body tieng Viet
```

Và dispatch (**code upstream, ta không sửa**):

```python
lang = "en" if str(report_language or "").lower() == "en" else "zh"
```

Cùng pattern ở: `src/stock_analyzer.py` (+62/−62), `src/market_analyzer.py` (+138/−138),
`src/market_context.py` (+15/−15), `src/market_phase_summary.py` (+22/−22),
`src/analysis_context_pack_prompt.py` (+41/−40) — tỉ lệ thêm/xoá bằng nhau = thay thế
1:1 từng dòng literal, không thêm tính năng.

**Bốn hệ quả:**

1. **Xung đột chắc chắn** mỗi lần upstream sửa bất kỳ chuỗi nào trong các file đó
   (`analyzer.py` 15 hunk, `market_analyzer.py` 13 hunk).
2. **Rò ngôn ngữ âm thầm** — nguy hiểm hơn xung đột vì *không báo lỗi*: upstream thêm
   một label mới → nó về dưới dạng tiếng Trung → đi thẳng vào report tiếng Việt.
3. **Test đã hỏng ngay hôm nay.** `tests/test_market_phase_prompt.py:48` assert
   `"盘中" in section`, nhưng source hiện emit `"trong phiên"` (đã verify bằng import
   trực tiếp `_PHASE_LABELS_ZH['intraday']`). 18 file test backend tham chiếu `盘中`,
   12 file tham chiếu `多头排列`, 64 file test frontend assert tiếng Trung.
   → **lưới an toàn để phát hiện merge sai đã mất.**
4. **`zh` không cứu lại được** và `SUPPORTED_REPORT_LANGUAGES=("zh","en","vi")` đối đầu
   trực diện `("zh","en","ko")` của upstream. Thêm nữa: khi merge `ko` về, `ko` sẽ rơi
   vào nhánh `else -> "zh"` và **nhận tiếng Việt**.

### 3.4 Kết luận i18n

Lớp UI text: **ổn, giữ**. Lớp label/report: **ổn về ý, sai về hình dạng dict** (sửa
được rẻ). Lớp prompt/context: **phải làm lại** — đây là nơi sinh ra phần lớn 101 hunk
xung đột và là nguồn rò tiếng Trung trong tương lai.

---

## 4. Plan chi tiết

### Phase 0 — Dựng nền quản lý fork (chặn mọi việc khác) · ~0.5–1 ngày

1. `git init` trong repo local. Tạo branch `vendor` chứa **upstream nguyên bản** tại
   `ecf87ea0` (giải nén tarball, commit 1 lần, không sửa gì).
2. Từ `vendor` tạo branch `main`, commit trạng thái local hiện tại → **diff của ta trở
   thành đối tượng review được**.
3. `git remote add upstream https://github.com/ZhuLinsen/daily_stock_analysis`.
   Từ nay catch-up = `git fetch upstream && git merge upstream/main` (hoặc rebase chuỗi
   patch).
4. `.gitignore`: `data/ logs/ reports/ backups/ .env node_modules/ __pycache__/ *.pyc`.
   Xoá `scripts/_mr_done.json`, `scripts/_mr_test.json`, `scripts/_vn_test.json`.
5. Tạo **`docs/vn-fork-touchpoints.md`** — danh sách canonical MỌI chỗ sửa file upstream:
   file · dòng · lý do · cách re-apply. Mỗi lần buộc phải sửa file upstream thì thêm 1
   dòng. Đây là tài liệu để merge lần sau đi trong 1 giờ thay vì 1 tuần.
6. Guard trong CI: script chạy `git diff vendor --name-only` và **fail nếu số file
   upstream bị sửa vượt ngân sách** (đề xuất trần: 25). Biến "bề mặt fork" thành con số
   được canh.

**DoD:** `git log` có 2 commit; `git diff vendor --stat` in ra đúng 78 file; CI guard chạy.

### Phase 1 — Fix P0-1: nối `OpenStockFundamentalAdapter` vào pipeline · ~1 ngày

1. File mới `data_provider/vn_fundamental_context.py`: hàm
   `build_vn_fundamental_context(manager, stock_code, budget_seconds) -> dict` — chứa
   toàn bộ logic, trả đúng shape của `_build_offshore_fundamental_context`
   (`valuation` / `growth` / `earnings` / `institution` / `capital_flow` / `boards` /
   `coverage` / `source_chain` / `errors`), gọi `OpenStockFundamentalAdapter`.
2. Sửa `base.py` **tối thiểu 3 dòng** (ghi vào `vn-fork-touchpoints.md`), đặt ngay
   trước nhánh `if market in {"us","hk","jp","kr"}`:
   ```python
   if market == "vn":
       from .vn_fundamental_context import build_vn_fundamental_context
       return build_vn_fundamental_context(self, stock_code, budget_seconds)
   ```
3. Mở guard cho `capital_flow` ở dòng ~3304: `!= "cn"` → `not in {"cn","vn"}`
   (giữ `dragon_tiger` / `boards` chặn — đúng bản chất VN).
4. Test mới `tests/test_vn_fundamental_context.py`: mock OpenStock, assert
   `growth.revenue_yoy` / `net_profit_yoy` / `gross_margin`,
   `earnings.operating_cash_flow`, `capital_flow.foreign_net` **có mặt trong context
   pack** đi vào LLM (không chỉ trong adapter).
5. Verify end-to-end: chạy 1 phân tích FPT, grep report thấy số YoY và khối ngoại thật.

**DoD:** report FPT chứa tăng trưởng doanh thu/LNST và dòng tiền khối ngoại; test xanh.

### Phase 2 — Thu hẹp bề mặt sửa upstream · ~2–3 ngày

**2a. Hoàn tác việc viết lại `_init_default_fetchers` / `data_provider/__init__.py`.**
Chọn 1 trong 3, theo thứ tự ưu tiên:
- (i) **Cài đủ dependency** trong deployment VN (rẻ nhất, diff = 0). `efinance`/`akshare`
  chỉ nặng lúc install, không tốn runtime nếu không gọi.
- (ii) Giữ code upstream nguyên vẹn, chỉ thêm **1 dòng** append fetcher:
  `if config.openstock_enabled: optional_fetchers.append(OpenStockFetcher())`.
- (iii) Nếu vẫn cần tolerant import: đưa `_optional_import` sang file mới
  `data_provider/_optional.py`, `__init__.py` chỉ thêm 1 dòng gọi.

Mục tiêu: `data_provider/base.py` từ 6 hunk xuống ≤2; `__init__.py` từ 64 dòng thêm
xuống ~8.

**2b. Tập trung hoá nhận diện mã VN.**
- `openstock_symbols.py` thành **single source of truth**, dữ liệu lấy từ OpenStock
  (`/search` hoặc thêm `/symbols`), cache trên đĩa + TTL, regex chỉ còn là fallback.
  Xử lý đúng: ETF (`FUEVFVND`, `E1VFVN30`), phái sinh (`VN30F2409`), chứng quyền, và
  **không** nhận mã 3 chữ không có trong universe.
- Chèn vào upstream tại **đúng 1 điểm**: `_market_tag()` trong `base.py`. Bỏ 5 chỗ
  `is_vn = _is_vn_market(...)` rải rác, thay bằng `market = _market_tag(code)` đã có.
- Với mỗi resolver mới của upstream (`market_symbol_utils`, `stock_list_parser`,
  `name_to_code_resolver`, target-resolution contract 3.30.0, `canonical_id` 3.31.0):
  thêm hook 1 dòng + 1 dòng trong `vn-fork-touchpoints.md`.
- Nếu muốn phục vụ đồng thời VN và US: yêu cầu suffix tường minh (`FPT.VN`) hoặc
  whitelist universe — đừng dựa vào flag global.

**2c.** Tách `/search` ra `api/v1/endpoints/vn_search.py` + 1 dòng `include_router`;
đưa `stocks.py` về gần nguyên bản. Thêm field `nameLocal` thay vì nhồi `nameZh`.

**DoD:** trial merge lại → số file xung đột giảm từ 28 xuống ≤18.

### Phase 3 — Làm lại i18n VI theo pattern `ko` của upstream · ~4–6 ngày

**3a. Phục hồi nguyên trạng chuỗi upstream (bắt buộc, làm trước).**
Lấy lại từ branch `vendor` cho các file bị ghi đè tại chỗ:
`src/market_phase_prompt.py`, `src/market_phase_summary.py`, `src/stock_analyzer.py`,
`src/market_context.py`, `src/analysis_context_pack_prompt.py`, `src/market_analyzer.py`
(phần literal; giữ lại nhánh `vn` thật sự additive).
Tiêu chí kiểm chứng:
```bash
git diff vendor -- src/market_phase_prompt.py src/market_phase_summary.py src/stock_analyzer.py src/market_context.py src/analysis_context_pack_prompt.py
```
→ phải **rỗng**.

**3b. Đăng ký `vi` bằng overlay, không sửa dict `key → {lang}`.**
- `SUPPORTED_REPORT_LANGUAGES = ("zh", "en", "ko", "vi")` — 1 dòng (khi merge `ko` về
  thì hợp nhất chứ không loại nhau).
- `_REPORT_LABELS["vi"] = {...}` — append block cuối dict (shape thân thiện, merge sạch).
- File mới **`src/report_language_vi.py`**:
  ```python
  VI_TRANSLATIONS = {
      "_OPERATION_ADVICE_TRANSLATIONS": {"buy": "Mua", "hold": "Nắm giữ"},
      "_TREND_PREDICTION_TRANSLATIONS": {},
      # ... du moi *_TRANSLATIONS
  }

  def register() -> None:
      """Chen key 'vi' vao cac dict translation cua upstream (khong sua file upstream)."""
      import src.report_language as rl
      for dict_name, entries in VI_TRANSLATIONS.items():
          target = getattr(rl, dict_name)
          for canonical, text in entries.items():
              target[canonical]["vi"] = text
  ```
  Gọi `register()` đúng **1 lần** — cuối `src/report_language.py` (1 dòng) hoặc trong
  app startup. Hợp lệ vì `_translate_from_map` đọc dict lúc runtime.
- **Test bao phủ** `tests/test_report_language_vi_coverage.py`: quét mọi
  `*_TRANSLATIONS` trong `report_language.py`, assert **mọi canonical key có entry `vi`**.
  → upstream thêm key mới thì **test đỏ ầm ĩ** thay vì rò tiếng Trung âm thầm.
  (Cần thiết vì `_translate_from_map` dùng `translations[canonical][lang]` → `KeyError`
  nếu thiếu.)

**3c. Tham số hoá formatter thay vì ghi đè `_format_zh`.**
- `market_phase_prompt.py`: thêm `_format_vi()`, đổi dispatch thành
  `_FORMATTERS = {"zh": _format_zh, "en": _format_en, "vi": _format_vi}` +
  `_FORMATTERS.get(lang, _format_zh)`. Sửa upstream ~3 dòng thay vì 29.
  Tương tự `market_phase_summary.py`.
- `stock_analyzer.py` / `market_context.py`: các hàm này trả **chuỗi hiển thị**
  (`ma_alignment`, trend text…). Cách đúng lâu dài: trả **canonical key**, localize ở
  biên. Đây là refactor lớn → **giải pháp trung gian**: giữ nguyên tiếng Trung của
  upstream, thêm file mới `src/vn_context_localizer.py` với
  `localize_context_pack(payload, language)` áp dụng **ngay trước khi ghép prompt**
  (1 file mới + 1 call-site). Map dịch nằm trong file của ta → upstream đổi chuỗi thì
  test coverage bắt được.

**3d. Nhánh chỉ thị ngôn ngữ output cho prompt — chấp nhận sửa in-tree, có kiểm soát.**
Thêm `elif report_language == "vi":` cạnh nhánh `ko` sẵn có của upstream tại:
`analyzer.py` (~1587, 1593, 3747, 4481), `market_analyzer.py`,
`schemas/decision_action.py`, `daily_market_context_guardrail.py`,
`phase_decision_guardrail.py`, `share_image.py`, `core/market_review.py`,
`core/pipeline.py`, `market_structure_prompt.py`, `services/empty_news.py`,
`services/history_service.py`, `agent/agents/decision_agent.py`, `agent/executor.py`
(~15 file). Mỗi chỗ 1–3 dòng **kề một nhánh đã tồn tại** → git thường auto-merge được.
Ghi tất cả vào `vn-fork-touchpoints.md`.

**3e. Frontend.** Giữ `UiLanguage = 'zh' | 'en' | 'vi'` và giữ dict `zh` làm nguồn
`UiTextKey` (đang đúng). Toggle chỉ EN↔VI là quyết định sản phẩm — giữ. Đồng bộ
`ReportLanguage` với `'zh'|'en'|'ko'|'vi'` khi merge `ko`.

**3f. Sửa test.** Sau 3a, các test assert tiếng Trung xanh lại. Với hành vi `vi` mới:
thêm test riêng set `report_language="vi"`. 64 file test FE assert tiếng Trung: set
language tường minh trong test setup thay vì đổi assertion (bảo toàn giá trị test cho zh).

**DoD:** `git diff vendor` cho các file ở 3a = rỗng; test coverage `vi` xanh;
1 report FPT tiếng Việt 100%, 0 ký tự Trung; trial merge → ≤10 file xung đột.

### Phase 4 — Catch up v3.31.0 · ~3–5 ngày (sau Phase 0–3)

Merge **tuần tự theo tag**, chạy test sau mỗi bước:
`v3.24.0 → v3.24.1 → v3.25.0 → v3.26.0/1 → v3.27.0 → v3.28.0 → v3.29.0 → v3.30.0 → v3.31.0`

| Bước | Việc cần làm thêm |
|---|---|
| v3.25.0 | Hợp nhất `SUPPORTED_REPORT_LANGUAGES` thành `("zh","en","ko","vi")`; kiểm tra `ko` **không** rơi vào nhánh `zh` (bug ở §3.3) |
| v3.28.0 | Dùng trigger market review theo market → bỏ `MARKET_REVIEW_REGION=vn` global |
| v3.29.0 | Screening: giá trị cao nhất cho VN. Cần `screening/dsa_provider.py` biết nguồn OpenStock (universe + chỉ tiêu). Ước tính riêng ~3–5 ngày |
| v3.30.0 | LLM API surface: khai báo đúng surface cho gateway local (freellmapi / OmniRoute); re-apply hook VN vào target-resolution contract |
| v3.31.0 | Re-apply hook VN vào `canonical_id` / name resolver; **lấy fix CVE-2026-54673** |

Sau đó: đặt nhịp catch-up **mỗi 2–4 tuần** (mỗi minor release), không để tụt 2 tháng nữa.

### Tổng ước lượng

| Phase | Ngày (người) | Chặn ai |
|---|---|---|
| 0 · git + vendor branch + touchpoints doc | 0.5–1 | chặn tất cả |
| 1 · fix dead-code fundamental | 1 | độc lập, làm ngay được |
| 2 · thu hẹp bề mặt adapter | 2–3 | sau 0 |
| 3 · làm lại i18n | 4–6 | sau 0 |
| 4 · catch up v3.31.0 | 3–5 (+3–5 nếu làm screening VN) | sau 2, 3 |

Thứ tự đề xuất: **0 → 1 (song song với 2) → 2 → 3 → 4.**

---

## 5. Nguyên tắc rút ra (cho mọi thay đổi sau này)

1. **Tính năng mới = file mới.** Chạm file upstream tối đa 1–3 dòng gọi hook.
2. **Không bao giờ ghi đè literal của upstream.** Thêm nhánh ngôn ngữ / overlay, đừng
   chiếm dụng slot `zh`.
3. **Gate mọi hành vi VN sau feature flag**, mặc định off → nhánh upstream giữ nguyên
   ngữ nghĩa.
4. **Additive + private helper** (mẫu: `search_service.py` VN news mode).
5. **Mỗi lần buộc phải sửa in-tree → ghi 1 dòng vào `docs/vn-fork-touchpoints.md`.**
6. **Có test cho ranh giới fork**: coverage `vi`, ngân sách số file upstream bị sửa.
   Cái gì không được canh bằng test thì sẽ âm thầm rò.
