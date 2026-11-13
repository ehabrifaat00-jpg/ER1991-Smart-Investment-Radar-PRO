#!/usr/bin/env bash
# ═══════════════════════════════════════════════════════════════════
# ER1991 Radar — التثبيت التلقائي عند إنشاء Codespace (يعمل مرة واحدة)
#  يثبّت: مكتبات النظام (poppler/خطوط عربية/WeasyPrint) + تبعيات بايثون + Jupyter
# ═══════════════════════════════════════════════════════════════════
set -e
cd "$(dirname "$0")/.."

echo "🔧 [1/3] تثبيت مكتبات النظام (poppler + خطوط Noto العربية + مكتبات WeasyPrint)..."
if command -v sudo > /dev/null 2>&1; then SUDO=sudo; else SUDO=; fi
$SUDO apt-get update -qq
$SUDO apt-get install -y -qq poppler-utils fonts-noto-core fonts-noto-color-emoji \
  libpango-1.0-0 libpangoft2-1.0-0 libharfbuzz-subset0 > /dev/null

echo "📦 [2/3] تثبيت تبعيات بايثون من requirements.txt..."
python -m pip install --upgrade pip -q
pip install -r requirements.txt -q
pip install ipykernel -q   # لتشغيل دفتر ER1991_Radar.ipynb داخل VS Code

echo "🧪 [3/3] فحص ذاتي سريع للمحرّك..."
python -c "import er1991_radar as m; m.selftest()"

echo ""
echo "✅ كل شيء جاهز! افتح الملف ER1991_Radar.ipynb واضغط ▶ على الخلية الأولى لعرض الواجهة التفاعلية."
echo "   أو شغّل من الطرفية: python run_radar.py"
