#!/usr/bin/env bash
# Do "be mat fork": bao nhieu file cua upstream bi fork VN sua doi.
#
# Ly do ton tai: moi file upstream bi sua la mot nguon xung dot khi catch-up.
# Bien con so nay thanh mot nguong duoc canh, thay vi de no am tham phinh len.
#
# Dung:
#   bash scripts/check-fork-surface.sh              # do va check nguong
#   bash scripts/check-fork-surface.sh --list       # liet ke file bi sua
#   bash scripts/check-fork-surface.sh --merge-test # thu merge upstream/main, dem xung dot
#
# Chi tiet tung touchpoint: docs/vn-fork-touchpoints.md
# Ke hoach thu hep:         plan/fork_maintenance_and_i18n_rework.md

set -uo pipefail

VENDOR_REF="${VENDOR_REF:-vendor}"

# === Nguong (ha dan theo tung phase, dung nang len) ===
MAX_MODIFIED_FILES="${MAX_MODIFIED_FILES:-70}"   # muc tieu: <=45 sau Phase 2, <=30 sau Phase 3
MAX_CONFLICT_FILES="${MAX_CONFLICT_FILES:-30}"   # muc tieu: <=18 sau Phase 2, <=10 sau Phase 3

cd "$(dirname "$0")/.." || exit 1

if ! git rev-parse --verify --quiet "$VENDOR_REF" >/dev/null; then
    echo "LOI: khong tim thay ref '$VENDOR_REF'."
    echo "     Branch 'vendor' phai chua snapshot NGUYEN BAN cua upstream."
    echo "     Xem docs/vn-fork-touchpoints.md."
    exit 2
fi

mapfile -t modified < <(git diff --name-only --diff-filter=M "$VENDOR_REF" -- | sort)
mapfile -t added < <(git diff --name-only --diff-filter=A "$VENDOR_REF" -- | sort)

n_mod=${#modified[@]}
n_add=${#added[@]}

if [[ "${1:-}" == "--list" ]]; then
    echo "=== File UPSTREAM bi fork sua ($n_mod) — moi dong la mot nguon xung dot ==="
    git diff --numstat "$VENDOR_REF" -- "${modified[@]}" 2>/dev/null \
        | sort -k1,1rn | awk '{printf "  +%-6s -%-6s %s\n", $1, $2, $3}'
    echo
    echo "=== File MOI cua fork ($n_add) — khong gay xung dot ==="
    printf '  %s\n' "${added[@]}"
    exit 0
fi

if [[ "${1:-}" == "--merge-test" ]]; then
    target="${2:-upstream/main}"
    if ! git rev-parse --verify --quiet "$target" >/dev/null; then
        echo "LOI: khong co ref '$target'. Chay: git fetch upstream"
        exit 2
    fi
    if ! git diff --quiet || ! git diff --cached --quiet; then
        echo "LOI: working tree khong sach. Commit hoac stash truoc khi merge-test."
        exit 2
    fi
    # Bat buoc phai co merge base. Neu 'vendor' la commit orphan (khong noi vao
    # history that cua upstream) thi git tu choi merge va ta se dem ra 0 xung dot
    # => ket luan SAI. Kiem tra truoc.
    # LUU Y: `git merge-base` (khac `--is-ancestor`) KHONG co flag --quiet;
    # truyen no vao la loi cu phap (exit 129), bi hieu nham thanh "khong co
    # merge base" - dung chinh loi nay tung lam script bao SAI "0 xung dot".
    if [[ -z "$(git merge-base main "$target" 2>/dev/null)" ]]; then
        echo "LOI: khong co merge base giua HEAD va '$target'."
        echo "     'vendor' phai tro vao COMMIT THAT cua upstream, khong phai commit orphan"
        echo "     dung tu tarball. Chay: git fetch upstream && git log --oneline vendor"
        exit 2
    fi

    start_ref=$(git rev-parse --abbrev-ref HEAD)
    echo "=== Thu merge $target vao $start_ref (se abort ngay sau khi dem) ==="
    merge_out=$(git merge --no-commit --no-ff "$target" 2>&1)
    mapfile -t conflicts < <(git diff --name-only --diff-filter=U)
    # Merge co the that bai vi ly do khac han xung dot (unrelated histories,
    # local changes would be overwritten...). Khong duoc coi do la "0 xung dot".
    if [[ ${#conflicts[@]} -eq 0 ]] && ! git rev-parse --verify --quiet MERGE_HEAD >/dev/null; then
        echo "LOI: merge khong chay duoc (khong phai vi xung dot). Output cua git:"
        echo "$merge_out" | sed 's/^/     /'
        git merge --abort 2>/dev/null || git reset -q --merge 2>/dev/null
        exit 2
    fi
    n_conf=${#conflicts[@]}
    total_hunks=0
    for f in "${conflicts[@]}"; do
        h=$(grep -c '^<<<<<<<' "$f" 2>/dev/null || echo 0)
        total_hunks=$((total_hunks + h))
        printf "  %3s hunk  %s\n" "$h" "$f"
    done
    git merge --abort 2>/dev/null || git reset -q --merge 2>/dev/null
    echo
    echo "File xung dot: $n_conf (tran: $MAX_CONFLICT_FILES) · tong hunk: $total_hunks"
    if (( n_conf > MAX_CONFLICT_FILES )); then
        echo "FAIL: xung dot vuot tran."
        exit 1
    fi
    echo "OK"
    exit 0
fi

echo "=== Be mat fork VN (so voi '$VENDOR_REF') ==="
printf "  File upstream bi sua : %3d  (tran: %d)\n" "$n_mod" "$MAX_MODIFIED_FILES"
printf "  File moi cua fork    : %3d  (khong tinh vao tran)\n" "$n_add"
git diff --shortstat "$VENDOR_REF" -- | sed 's/^/  /'
echo
echo "  Chi tiet: bash scripts/check-fork-surface.sh --list"
echo "  Do xung dot: bash scripts/check-fork-surface.sh --merge-test upstream/main"
echo

if (( n_mod > MAX_MODIFIED_FILES )); then
    cat <<EOF
FAIL: fork dang sua $n_mod file cua upstream, vuot tran $MAX_MODIFIED_FILES.

Truoc khi nang tran, thu cac cach nay:
  1. Tinh nang moi -> FILE MOI, chi de lai 1-3 dong hook trong file upstream.
  2. Khong ghi de literal cua upstream. Them nhanh ngon ngu / overlay.
  3. Gate hanh vi VN sau feature flag, mac dinh off.
  4. Ghi moi touchpoint vao docs/vn-fork-touchpoints.md.
EOF
    exit 1
fi

echo "OK"
