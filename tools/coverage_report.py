"""Измерение покрытия тестами по строкам и генерация HTML-отчёта.

В среде разработки не удалось установить pytest-cov (нет доступа к PyPI),
поэтому покрытие считается скриптом на основе sys.settrace.
Запуск из корня проекта: python tools/coverage_report.py
Результат: docs/coverage_report.html
"""
import html
import os
import sys
import unittest
from collections import defaultdict
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
APP_DIR = ROOT / "app"
SERVICES_DIR = APP_DIR / "services"
REPORT_PATH = ROOT / "docs" / "coverage_report.html"

executed = defaultdict(set)
app_prefix = str(APP_DIR) + os.sep


def local_tracer(frame, event, arg):
    if event == "line":
        executed[frame.f_code.co_filename].add(frame.f_lineno)
    return local_tracer


def global_tracer(frame, event, arg):
    if frame.f_code.co_filename.startswith(app_prefix):
        executed[frame.f_code.co_filename].add(frame.f_lineno)
        return local_tracer
    return None


def executable_lines(path):
    code = compile(path.read_text(encoding="utf-8"), str(path), "exec")
    lines = set()
    stack = [code]
    while stack:
        current = stack.pop()
        for _, _, line in current.co_lines():
            if line is not None:
                lines.add(line)
        stack.extend(c for c in current.co_consts if hasattr(c, "co_lines"))
    return lines


def run_tests():
    sys.path.insert(0, str(ROOT))
    os.chdir(ROOT)
    sys.settrace(global_tracer)
    try:
        suite = unittest.defaultTestLoader.discover(str(ROOT / "tests"), top_level_dir=str(ROOT))
        result = unittest.TextTestRunner(verbosity=1).run(suite)
    finally:
        sys.settrace(None)
    return result


def collect():
    rows = []
    for path in sorted(APP_DIR.rglob("*.py")):
        lines = executable_lines(path)
        if not lines:
            continue
        hit = executed.get(str(path), set()) & lines
        rows.append((path, lines, hit))
    return rows


def percent(hit, total):
    return 100.0 * hit / total if total else 100.0


def render(rows, result):
    def group_total(predicate):
        total = sum(len(lines) for p, lines, _ in rows if predicate(p))
        hit = sum(len(h) for p, _, h in rows if predicate(p))
        return hit, total

    svc_hit, svc_total = group_total(lambda p: SERVICES_DIR in p.parents)
    all_hit, all_total = group_total(lambda p: True)

    parts = [
        "<!DOCTYPE html><html lang='ru'><head><meta charset='utf-8'>",
        "<title>Отчёт о покрытии тестами</title>",
        "<style>body{font-family:sans-serif;margin:24px}table{border-collapse:collapse}"
        "td,th{border:1px solid #bbb;padding:4px 10px;text-align:left}"
        "pre{background:#f6f6f6;padding:8px;font-size:13px}"
        ".miss{background:#ffd6d6}.hit{background:#e2f5e2}.num{color:#888}</style></head><body>",
        "<h1>Отчёт о покрытии тестами (по строкам)</h1>",
        f"<p>Запущено тестов: {result.testsRun}, "
        f"ошибок: {len(result.errors)}, падений: {len(result.failures)}.</p>",
        f"<p><b>Сервисный слой (app/services): {percent(svc_hit, svc_total):.1f}%</b> "
        f"({svc_hit} из {svc_total} строк).<br>"
        f"Весь пакет app: {percent(all_hit, all_total):.1f}% ({all_hit} из {all_total} строк).</p>",
        "<table><tr><th>Файл</th><th>Строк</th><th>Покрыто</th><th>%</th></tr>",
    ]
    for path, lines, hit in rows:
        rel = path.relative_to(ROOT).as_posix()
        parts.append(
            f"<tr><td><a href='#{rel}'>{rel}</a></td><td>{len(lines)}</td>"
            f"<td>{len(hit)}</td><td>{percent(len(hit), len(lines)):.1f}</td></tr>"
        )
    parts.append("</table>")
    for path, lines, hit in rows:
        rel = path.relative_to(ROOT).as_posix()
        parts.append(f"<h3 id='{rel}'>{rel}</h3><pre>")
        for number, text in enumerate(path.read_text(encoding="utf-8").splitlines(), 1):
            css = "" if number not in lines else ("hit" if number in hit else "miss")
            parts.append(
                f"<span class='{css}'><span class='num'>{number:4d}</span>  "
                f"{html.escape(text)}</span>"
            )
        parts.append("</pre>")
    parts.append("</body></html>")
    return "\n".join(parts), percent(svc_hit, svc_total), percent(all_hit, all_total)


if __name__ == "__main__":
    test_result = run_tests()
    table = collect()
    page, services_percent, total_percent = render(table, test_result)
    REPORT_PATH.write_text(page, encoding="utf-8")
    print()
    for p, lines, hit in table:
        print(f"{p.relative_to(ROOT).as_posix():38s} {len(hit):4d}/{len(lines):<4d} "
              f"{percent(len(hit), len(lines)):6.1f}%")
    print(f"\nСервисный слой: {services_percent:.1f}%   Весь пакет app: {total_percent:.1f}%")
    print(f"Отчёт: {REPORT_PATH.relative_to(ROOT).as_posix()}")
    sys.exit(0 if test_result.wasSuccessful() and services_percent >= 70 else 1)
