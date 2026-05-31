#!/usr/bin/env bash
set -euo pipefail

# MVP mobil smoke tekshiruvi:
# - bog'liqliklar
# - static analiz
# - widget/unit testlar
# - Android debug build (minSdk=26 qamrovi)

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd "$ROOT_DIR"

if command -v flutter >/dev/null 2>&1; then
  FLUTTER_BIN="$(command -v flutter)"
elif [ -x "$HOME/flutter/bin/flutter" ]; then
  FLUTTER_BIN="$HOME/flutter/bin/flutter"
else
  echo "ERROR: flutter topilmadi. Avval Flutter SDK o'rnating."
  exit 1
fi

echo "[1/6] Flutter doctor"
"$FLUTTER_BIN" doctor -v

echo "[2/6] Flutter pub get"
"$FLUTTER_BIN" pub get

echo "[3/6] Drift codegen"
"$FLUTTER_BIN" pub run build_runner build

echo "[4/6] Static analyze"
"$FLUTTER_BIN" analyze --no-fatal-infos --no-fatal-warnings

echo "[5/6] Testlar"
"$FLUTTER_BIN" test

echo "[6/6] Android debug build"
"$FLUTTER_BIN" build apk --debug

echo "OK: Mobil MVP smoke tekshiruvlari muvaffaqiyatli yakunlandi."
