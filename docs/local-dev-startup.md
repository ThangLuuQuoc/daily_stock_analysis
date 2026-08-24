# Khởi động toàn hệ thống (local dev)

Tài liệu này mô tả cách bật **toàn bộ stack local** cho `daily_stock_analysis` ở thị trường VN: nguồn dữ liệu (OpenStock), gateway LLM miễn phí (freellmapi), backend/CLI phân tích, và web dashboard. Dành cho cả **người dev** và **AI agent** khi cần biết thứ tự + lệnh khởi động.

> Mọi lệnh chạy trên Windows. Shell mặc định PowerShell; các block dưới đây viết kiểu POSIX (Git Bash) — đổi cú pháp env (`A=B cmd`) sang PowerShell (`$env:A='B'; cmd`) nếu cần.

## 1. Sơ đồ phụ thuộc

```
[OpenStock :3000]  --dữ liệu VN-->  [daily_stock_analysis backend/CLI :8000]  <--/api proxy--  [dsa-web :5173]
                                              |
                                              | gọi LLM (LiteLLM channel "freellm")
                                              v
                                     [freellmapi :3001]  --auto-failover-->  free LLM providers
```

Thứ tự khởi động khuyến nghị: **OpenStock → freellmapi → backend/CLI → (tuỳ chọn) web**. Backend không *crash* nếu OpenStock/freellmapi chưa lên (có fallback/skip), nhưng phân tích sẽ thiếu dữ liệu hoặc lỗi LLM.

## 2. Bố cục thư mục (máy hiện tại)

| Thành phần | Đường dẫn |
|---|---|
| Dự án chính | `F:\2026\2027\dailysignals\daily_stock_analysis` |
| freellmapi (gateway LLM) | `F:\2026\2027\dailysignals\freellmapi` (sibling) |
| OpenStock (nguồn dữ liệu VN) | `F:\2026\2027\openstockV1` |

## 3. Bảng port

| Port | Service | Ghi chú |
|---|---|---|
| 3000 | OpenStock API | `…/api/v1` |
| 3001 | freellmapi | dashboard + `/v1` (OpenAI-compatible) |
| 8000 | daily_stock_analysis backend (FastAPI) + **web UI** | chỉ khi chạy `--serve`/`--serve-only`; phục vụ luôn dashboard + `/docs` |
| 5173 | dsa-web (Vite dev, tuỳ chọn) | chỉ khi dev frontend; proxy `/api` → `127.0.0.1:8000` |

> Lưu ý: nếu chạy cả **frontend của OpenStock** thì nó cũng dùng 5173 → xung đột với dsa-web. Khi chỉ chạy `bun run dev` (API thuần) thì không xung đột.

## 4. Khởi động từng service

### 4.1. OpenStock (nguồn dữ liệu VN) — port 3000

```bash
cd /f/2026/2027/openstockV1
bun run dev            # = bun run src/index.ts
# Healthy khi log có: "🚀 Stock API running on port 3000"
```

Cần Bun ≥ 1.3 và Redis/DB của OpenStock đã sẵn sàng (đã seed từ trước).

### 4.2. freellmapi (gateway LLM miễn phí) — port 3001

```bash
cd /f/2026/2027/dailysignals/freellmapi
# Lần đầu: tạo .env (giữ nguyên cho các lần sau, đừng đổi ENCRYPTION_KEY)
[ -f .env ] || printf "ENCRYPTION_KEY=%s\nPORT=3001\n" "$(openssl rand -hex 32)" > .env
docker compose up -d
# Kiểm tra: docker compose ps  → STATUS "Up (healthy)"
# curl http://localhost:3001/api/ping  → 200
```

Lần đầu cần cấu hình qua dashboard `http://localhost:3001`:
1. Trang **Keys**: nạp free API key (Groq/Gemini/OpenRouter/NVIDIA NIM…), copy **unified key** `freellmapi-...`.
2. Trang **Fallback Chain**: bật/sắp model, kiểm tra health.
3. Unified key đã được điền sẵn trong `.env` của dự án chính (xem 4.3); nếu xoay key thì cập nhật lại.

### 4.3. daily_stock_analysis — phân tích (CLI) hoặc backend

Cấu hình LLM nằm trong `.env` của dự án: channel `LLM_CHANNELS=freellm` trỏ `http://localhost:3001/v1`. Xem chi tiết tại [llm-providers.md](llm-providers.md#freellmapi-本地网关聚合免费-llm).

**Biến môi trường bắt buộc khi chạy trên Windows:**
- `OPENBLAS_NUM_THREADS=1 OMP_NUM_THREADS=1` — tránh numpy ngốn RAM.
- `PYTHONUTF8=1 PYTHONIOENCODING=utf-8` — console cp1252 không in được tiếng Việt nếu thiếu.

**Chạy phân tích 1 lượt (CLI):**

```bash
cd /f/2026/2027/dailysignals/daily_stock_analysis
OPENBLAS_NUM_THREADS=1 OMP_NUM_THREADS=1 PYTHONUTF8=1 PYTHONIOENCODING=utf-8 \
  python main.py --stocks FPT --debug
# Báo cáo: reports/report_<YYYYMMDD>.md  &  reports/market_review_<YYYYMMDD>.md
```

Các flag hữu ích: `--dry-run` (bỏ qua phân tích AI, chỉ lấy/lưu dữ liệu), `--no-notify` (không gửi thông báo), `--market-review` (chỉ phục thị), `--stocks A,B,C` (danh sách mã), không truyền `--stocks` thì dùng `STOCK_LIST` trong `.env`.

**Chạy backend FastAPI (cho web/desktop):**

```bash
OPENBLAS_NUM_THREADS=1 OMP_NUM_THREADS=1 python main.py --serve
# hoặc: uvicorn server:app --host 0.0.0.0 --port 8000
```

### 4.4. Web frontend (dashboard)

Có **2 cách** truy cập web UI:

**Cách A — dùng ngay (khuyến nghị): backend tự build & phục vụ UI tại `:8000`.**

```bash
cd /f/2026/2027/dailysignals/daily_stock_analysis
OPENBLAS_NUM_THREADS=1 OMP_NUM_THREADS=1 PYTHONUTF8=1 PYTHONIOENCODING=utf-8 \
  python main.py --serve-only
# Lần đầu sẽ chạy `npm run build` gắn frontend vào static/ (~30s) rồi serve.
# Mở: http://localhost:8000   |   API docs: http://localhost:8000/docs
```

- `--serve-only`: chỉ web service (không kèm scheduler). `--serve`: web + lịch phân tích.
- Frontend (React/Vite) được FastAPI phục vụ như static cùng cổng `:8000`; không cần chạy Vite riêng.
- Health check: `curl http://localhost:8000/api/v1/health` → `{"status":"ok"}`.

**Cách B — dev frontend có hot-reload: Vite tại `:5173`.**

```bash
cd /f/2026/2027/dailysignals/daily_stock_analysis/apps/dsa-web
npm ci          # lần đầu
npm run dev     # Vite :5173, proxy /api → :8000 (vẫn cần backend Cách A đang chạy)
```

Dùng Cách B khi sửa code frontend; còn chỉ để xem/dùng dashboard thì Cách A là đủ.

### 4.5. News tiếng Việt (`VN_NEWS_ENABLED`)

Tìm tin theo thị trường VN (cafef/vietstock/vneconomy…) thay vì mặc định Trung/Mỹ. Bật trong `.env`:

```env
VN_NEWS_ENABLED=true
# (tuỳ chọn) mở rộng/ghi đè domain — để trống dùng default
# VN_NEWS_DOMAINS=cafef.vn,vietstock.vn,vneconomy.vn,...
SERPAPI_API_KEYS=<serpapi-key>            # engine khuyến nghị cho VN (Google, locale gl=vn)
SEARXNG_PUBLIC_INSTANCES_ENABLED=false    # tắt SearXNG công cộng (TQ-oriented, hay 429)
```

Khi bật: query đổi sang tiếng Việt, SerpAPI dùng locale VN (`gl=vn/hl=vi`), kết quả lọc về **nguồn VN** (domain `.vn` + allowlist). Mã VN (FPT/VNM…) không còn bị nhận nhầm là cổ phiếu Mỹ. Phần tìm tin **không qua LLM/freellmapi**.

> Lưu ý: SerpAPI free + Google có độ biến thiên (đôi khi một số truy vấn trả rỗng). Muốn ổn định/đầy đủ hơn: dùng nhiều search key, key trả phí, hoặc Tavily (hỗ trợ `include_domains` native).

## 5. Smoke test nhanh toàn stack

```bash
# 1) freellmapi sống
curl -s http://localhost:3001/api/ping

# 2) gateway trả lời (thay <UNIFIED_KEY>)
curl -s http://localhost:3001/v1/chat/completions \
  -H "Authorization: Bearer <UNIFIED_KEY>" -H "Content-Type: application/json" \
  -d '{"model":"auto","messages":[{"role":"user","content":"OK?"}],"max_tokens":8}'

# 3) OpenStock sống
curl -s -o /dev/null -w "%{http_code}\n" http://localhost:3000/api/v1

# 4) full pipeline 1 mã
cd /f/2026/2027/dailysignals/daily_stock_analysis
OPENBLAS_NUM_THREADS=1 OMP_NUM_THREADS=1 PYTHONUTF8=1 PYTHONIOENCODING=utf-8 \
  python main.py --stocks FPT --debug --no-notify
```

## 6. Sự cố thường gặp

| Triệu chứng | Nguyên nhân & xử lý |
|---|---|
| `UnicodeEncodeError ... cp1252` khi in tiếng Việt | Thiếu `PYTHONUTF8=1 PYTHONIOENCODING=utf-8`. |
| Log: `Agent 主模型未出现在当前渠道...` | `AGENT_LITELLM_MODEL` không có trong `LLM_FREELLM_MODELS`. Thêm model vào list (vd `LLM_FREELLM_MODELS=auto,llama-3.3-70b`). |
| LLM call rất chậm / timeout | Free tier chậm + reasoning model; nới `LLM_TIMEOUT_SEC` (đang 150). Một mã có thể ~3-5 phút. |
| Report ghi "Không có tin tức mới" | Chưa có search key, SearXNG public hay 429. Phần tìm tin **không qua freellmapi**; nạp `TAVILY_API_KEYS`/`BRAVE_API_KEYS` vào `.env`. |
| Gateway trả 401 | `LLM_FREELLM_API_KEY` sai/trống — dán lại unified key `freellmapi-...` từ dashboard. |
| dsa-web 5173 bị chiếm | Đang chạy frontend OpenStock. Tắt nó hoặc đổi port Vite. |
| `No module named 'akshare'/'efinance'` | Bình thường (nguồn dữ liệu TQ không cài trong deploy VN-only), không block. |

## 7. Dừng hệ thống

```bash
# freellmapi
cd /f/2026/2027/dailysignals/freellmapi && docker compose down
# OpenStock & backend & web: Ctrl+C ở terminal tương ứng (hoặc đóng tiến trình bun/python/node)
```

## 8. Quick-start cho AI agent

Khi cần chạy phân tích đầu-cuối, kiểm tra/khởi động theo thứ tự, rồi chạy smoke test §5:

1. `curl http://localhost:3000/api/v1` (OpenStock). Chưa lên → `cd F:\2026\2027\openstockV1 && bun run dev`.
2. `curl http://localhost:3001/api/ping` (freellmapi). Chưa lên → `cd F:\2026\2027\dailysignals\freellmapi && docker compose up -d`.
3. Chạy 1 lượt: `main.py --stocks <MÃ> --debug --no-notify` với 4 biến env Windows ở §4.3.
   Hoặc bật web UI: `main.py --serve-only` → http://localhost:8000 (lần đầu tự build ~30s).
4. Kiểm chứng đi qua gateway: log có `POST http://localhost:3001/v1/chat/completions` và header `X-Routed-Via`.

Chi tiết tích hợp LLM: [llm-providers.md](llm-providers.md). Quy tắc cộng tác: [../AGENTS.md](../AGENTS.md).
