#!/usr/bin/env bash
# ─────────────────────────────────────────────────────────────────────────────
# backup.sh — snapshot code của daily_stock_analysis (chỉ trong repo này)
#
# Dùng:
#   bash scripts/backup.sh             # nhãn mặc định "snapshot"
#   bash scripts/backup.sh phase1      # gắn nhãn
#
# Kết quả: backups/dsa_<label>_<YYYYMMDD_HHMM>.tar.gz
# Loại trừ: node_modules, venv, __pycache__, logs, backups, build/cache.
# Bao gồm cả .env (đây là backup cục bộ — KHÔNG chia sẻ file này ra ngoài).
# ─────────────────────────────────────────────────────────────────────────────

set -euo pipefail

PROJECT_ROOT="$(cd "$(dirname "$0")/.." && pwd)"
BACKUP_DIR="${PROJECT_ROOT}/backups"
DATE="$(date +%Y%m%d_%H%M)"
LABEL="${1:-snapshot}"
LABEL="${LABEL// /_}"
ARCHIVE_NAME="dsa_${LABEL}_${DATE}.tar.gz"
ARCHIVE_PATH="${BACKUP_DIR}/${ARCHIVE_NAME}"

EXCLUDES=(
  "--exclude=./backups"
  "--exclude=./.git"
  # node deps / build (frontend apps)
  "--exclude=./apps/dsa-web/node_modules"
  "--exclude=./apps/dsa-web/dist"
  "--exclude=./apps/dsa-web/.vite"
  "--exclude=./apps/dsa-desktop/node_modules"
  "--exclude=./apps/dsa-desktop/dist"
  "--exclude=./static"
  # python
  "--exclude=./.venv"
  "--exclude=./venv"
  "--exclude=*/__pycache__"
  "--exclude=*.pyc"
  # logs / cache / temp
  "--exclude=./logs"
  "--exclude=./.cache"
  "--exclude=*.log"
)

mkdir -p "${BACKUP_DIR}"

echo "📦 Đang tạo backup: ${ARCHIVE_NAME}"
echo "   Nguồn : ${PROJECT_ROOT}"
echo "   Đích  : ${ARCHIVE_PATH}"

tar "${EXCLUDES[@]}" -czf "${ARCHIVE_PATH}" -C "${PROJECT_ROOT}" .

SIZE="$(du -h "${ARCHIVE_PATH}" | cut -f1)"
echo
echo "✅ Xong!"
echo "   File : ${ARCHIVE_PATH}"
echo "   Size : ${SIZE}"
echo
echo "📋 Danh sách backup:"
ls -1t "${BACKUP_DIR}"/*.tar.gz 2>/dev/null | head -5
