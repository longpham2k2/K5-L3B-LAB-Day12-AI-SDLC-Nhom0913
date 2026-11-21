#!/usr/bin/env bash
# Đóng gói bản phát hành từ một commit/tag: bash tools/package_release.sh [ref=HEAD] [version=v1.0.0]
# -> dist/quan-an-cho-noi-<version>.zip (git archive: đúng nội dung đã commit, không lẫn file rác cục bộ),
#    rồi tự kiểm: giải nén vào thư mục tạm và chạy toàn bộ test trong đó.
set -euo pipefail
cd "$(dirname "$0")/.."
REF=${1:-HEAD}; VER=${2:-v1.0.0}; NAME=quan-an-cho-noi-$VER
mkdir -p dist
git archive --format=zip --prefix="$NAME/" -o "dist/$NAME.zip" "$REF"
T=$(mktemp -d); trap 'rm -rf "$T"' EXIT
unzip -q "dist/$NAME.zip" -d "$T"
(cd "$T/$NAME" && PYTHONPATH=tests:. python3 -m unittest discover -s tests 2>&1 | tail -1)
echo "dist/$NAME.zip ($(git rev-parse --short "$REF"))"
