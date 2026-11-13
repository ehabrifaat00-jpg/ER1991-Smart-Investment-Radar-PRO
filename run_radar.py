#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# =====================================================================================
# ER1991 Smart Investment Radar PRO — 🆕 v7.0-GitHub: مشغّل سطر الأوامر (run_radar.py)
# ---------------------------------------------------------------------
# الغرض: تشغيل الأداة دون واجهة على GitHub (Actions / طرفية Codespaces / أي سيرفر)
#  بنفس المدخلات والإعدادات والنتائج الموجودة في كولاب حرفياً.
# ملاحظة مهمة: هذا الملف لا يحتوي أي منطق تحليل — كل الحسابات والتصديرات تُستدعى
#  من er1991_radar.py (run_scan + export_html/excel/csv/pdf/png) كما هي دون تغيير.
#
# الاستخدام:
#   python run_radar.py                          # يقرأ config.json الموجود بجانبه
#   python run_radar.py --config my.json         # ملف إعدادات آخر
#   python run_radar.py --symbols "AAPL, COMI.CA"  # تجاوز الرموز من الطرفية
#   python er1991_radar.py --config config.json  # نفس الشيء (نقطة تشغيل بديلة)
#   python run_radar.py --selftest               # الفحص الذاتي للمحرّك فقط
# =====================================================================================
import argparse
import json
import os
import sys
import time
import traceback

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import er1991_radar as m   # noqa: E402  (نفس الكود الأساسي — بدون أي تعديل)


def _deep_merge_flat(d):
    """يحوّل المفاتيح المنقّطة («fvW.pe»: 0.3) إلى قواميس متداخلة ({'fvW': {'pe': 0.3}})
    تماماً كما تفعل لوحة الإعدادات في الواجهة (coe_over) قبل تمريرها إلى run_scan كـp_over."""
    out = {}
    for k, v in (d or {}).items():
        if k.startswith('_'):
            continue
        if '.' in k:
            a_, b_ = k.split('.', 1)
            out.setdefault(a_, {})[b_] = v
        else:
            out[k] = v
    return out or None


def _progress(i, n, label):
    print(f'   [{label}] {i}/{n}', flush=True)


def _print_summary(res, lang):
    """ملخص نصي للطرفية/سجل Actions — نفس قرارات التقرير دون أي إعادة حساب."""
    meta = res['meta']
    print('\n' + '=' * 78)
    print(f"✅ تم تحليل {meta['n']} من {meta['requested']} رمز | البيانات حتى {meta['as_of']} | الاستغراق {meta['secs']:.0f} ثانية")
    print('=' * 78)
    for line in meta['log']:
        print('  ' + str(line))
    ar = (lang == 'عربي')
    print('\n  ' + ('الرمز        القرار                     الدرجة    السعر' if ar else 'Symbol       Decision                   Score     Price'))
    print('  ' + '-' * 70)
    for r in res['recs']:
        name = m.DEC_NAME.get(r['uni_decision'], ('', '?'))[1 if ar else 0]
        price = f"{r['price']:,.2f}" if m.nn(r.get('price')) else '—'
        print(f"  {r['symbol']:<12} {name:<26} {r['uni_score']:>6.1f}   {price:>12}")
    print('\nℹ️ ' + (m.NOTE_AR if ar else m.NOTE_EN))


def _export_all(res, cfg, lang):
    """ينفّذ التصديرات المطلوبة بنفس دوال er1991_radar (نفس الملفات ونفس التصميم)."""
    ex = cfg.get('exports') or {}
    cards = int(cfg.get('cards_top', 30) or 30)
    made = []
    jobs = [('🌐 HTML تفاعلي', 'html', lambda: m.export_html(res, lang, cards)),
            ('📊 Excel', 'excel', lambda: m.export_excel(res, lang)),
            ('🧾 CSV', 'csv', lambda: m.export_csv(res, lang)),
            ('📄 PDF', 'pdf', lambda: m.export_pdf(res, lang, cards)),
            ('🖼️ صور PNG (ZIP)', 'png', lambda: m.export_png(res, lang, cards))]
    for label, key, fn in jobs:
        if not ex.get(key, True):
            print(f'⏭️ {label}: معطّل في الإعدادات.')
            continue
        try:
            out = fn()
            if isinstance(out, tuple):
                for x in out:
                    m._download(x)
                    made.append(x)
            else:
                m._download(out)
                made.append(out)
        except Exception as e:
            print(f'❌ {label}: {type(e).__name__}: {e}')
    return made


def cli_main(argv=None):
    ap = argparse.ArgumentParser(
        prog='run_radar',
        description='ER1991 Smart Investment Radar PRO — تشغيل سطر الأوامر على GitHub (نفس منطق كولاب حرفياً)')
    ap.add_argument('--config', default='config.json', help='ملف الإعدادات (افتراضياً config.json بجانب الكود)')
    ap.add_argument('--symbols', default=None, help='تجاوز الرموز: "AAPL, EGX:COMI, TADAWUL:2222"')
    ap.add_argument('--market', default=None, choices=['AUTO', 'US', 'EGX', 'TASI'], help='سوق الرموز المجردة')
    ap.add_argument('--bench', default=None, help='المؤشر المرجعي (AUTO أو ^NDX أو ^CASE30 ...)')
    ap.add_argument('--style', default=None, help='أسلوب الاستثمار (Auto/Value/Growth/Swing/Medium Term/Long Term)')
    ap.add_argument('--lang', default=None, choices=['عربي', 'English'], help='لغة النتائج والتقارير')
    ap.add_argument('--capital', type=float, default=None, help='رأس المال')
    ap.add_argument('--risk', type=float, default=None, help='نسبة المخاطرة %')
    ap.add_argument('--cards', type=int, default=None, help='عدد البطاقات في HTML/PDF/PNG')
    ap.add_argument('--no-deep', action='store_true', help='تعطيل التحليل المالي العميق (أسرع)')
    ap.add_argument('--no-ui-hint', dest='no_ui_hint', action='store_true', help=argparse.SUPPRESS)
    ap.add_argument('--selftest', action='store_true', help='فحص ذاتي للمحرّك فقط دون إنترنت')
    ap.add_argument('--pages', default=None, help='مجلد اختياري يُنسخ إليه تقرير HTML باسم index.html (لـGitHub Pages)')
    args = ap.parse_args(argv)

    if args.selftest:
        m.selftest()
        return 0

    cfg_path = args.config if os.path.isabs(args.config) else os.path.join(
        os.path.dirname(os.path.abspath(__file__)), args.config)
    cfg = {}
    if os.path.exists(cfg_path):
        with open(cfg_path, 'r', encoding='utf-8-sig') as f:
            cfg = json.load(f)
        print(f'📄 ملف الإعدادات: {cfg_path}')
    else:
        print(f'⚠️ ملف الإعدادات غير موجود ({cfg_path}) — سأستخدم الطرفية والقيم الافتراضية كما في كولاب.')

    symbols = args.symbols or cfg.get('symbols') or m.SAMPLE
    lang = args.lang or cfg.get('lang', 'عربي')
    run_kw = dict(
        market=args.market or cfg.get('market', 'AUTO'),
        bench_choice=args.bench or cfg.get('bench', 'AUTO'),
        style=args.style or cfg.get('style', 'Auto'),
        capital=float(args.capital if args.capital is not None else cfg.get('capital', 10000.0)),
        risk_pct=float(args.risk if args.risk is not None else cfg.get('risk_pct', 1.0)),
        deep=(not args.no_deep) if args.no_deep else bool(cfg.get('deep', True)),
        intraday=bool(cfg.get('intraday', False)),
        require_htf=bool(cfg.get('require_htf', True)),
        use_corr=bool(cfg.get('use_corr', True)),
        guard=bool(cfg.get('guard', True)),
        vt=bool(cfg.get('vt', True)),
        be_next_bar=bool(cfg.get('be_next_bar', False)),
        lang=lang,
        progress=_progress,
        p_over=_deep_merge_flat(cfg.get('settings') or {}),
    )

    print('⏳ جاري التحميل والتحليل... (قد يستغرق 1–5 دقائق لـ100 سهم)')
    t0 = time.time()
    try:
        res = m.run_scan(symbols, **run_kw)
    except Exception as e:
        print('❌ فشل الفحص:', type(e).__name__, e)
        traceback.print_exc()
        return 1
    m.STATE['res'] = res

    _print_summary(res, lang)
    made = _export_all(res, cfg, lang)

    pages = args.pages
    if pages and made:
        htmls = [x for x in made if str(x).endswith('.html')]
        if htmls:
            import shutil
            os.makedirs(pages, exist_ok=True)
            shutil.copyfile(htmls[0], os.path.join(pages, 'index.html'))
            print(f'📤 تقرير Pages جاهز: {os.path.join(pages, "index.html")}')

    print(f'\n🏁 اكتمل كل شيء في {time.time() - t0:.0f} ثانية — ملفات التقارير في مجلد: {m.OUT_DIR}')
    return 0


if __name__ == '__main__':
    sys.exit(cli_main())
