from __future__ import annotations

from dataclasses import dataclass
from html import escape
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from typing import Mapping
from urllib.parse import parse_qs

from quantum_trainer.today_command import TodayAnalysisOutput, run_today_analysis


@dataclass(frozen=True)
class LocalAppConfig:
    project_root: Path
    host: str = "127.0.0.1"
    port: int = 8765


def run_form_analysis(
    project_root: Path | str,
    form: Mapping[str, str],
    dry_run: bool = False,
) -> TodayAnalysisOutput:
    stock = str(form.get("stock", "")).strip() or None
    refresh_market_data = str(form.get("refresh_market_data", "on")).lower() in {"on", "true", "1", "yes"}
    return run_today_analysis(
        project_root=Path(project_root),
        stock=stock,
        refresh_market_data=refresh_market_data,
        dry_run=dry_run,
    )


def render_home(result: TodayAnalysisOutput | None = None, error: str | None = None) -> str:
    result_html = _render_result(result) if result else ""
    error_html = f'<section class="notice error">{escape(error)}</section>' if error else ""
    return "\n".join(
        [
            "<!doctype html>",
            '<html lang="ko">',
            "<head>",
            '<meta charset="utf-8">',
            '<meta name="viewport" content="width=device-width, initial-scale=1">',
            "<title>퀀트 트레이너</title>",
            "<style>",
            _css(),
            "</style>",
            "</head>",
            "<body>",
            '<main class="page">',
            '<header class="topbar">',
            "<div>",
            "<h1>퀀트 트레이너</h1>",
            "<p>종목 추가부터 오늘 결론까지 한 화면에서 확인합니다.</p>",
            "</div>",
            '<span class="safe">주문 실행 없음</span>',
            "</header>",
            '<section class="workflow">',
            '<form method="post" action="/run" class="panel">',
            "<h2>종목 입력</h2>",
            '<div class="input-row">',
            '<input name="stock" type="text" placeholder="삼성전자, 현대차, 005930" autocomplete="off">',
            '<button type="submit">오늘 분석 실행</button>',
            "</div>",
            '<label class="check-row">',
            '<input name="refresh_market_data" type="hidden" value="off">',
            '<input name="refresh_market_data" type="checkbox" checked>',
            "<span>최신 가격 갱신</span>",
            "</label>",
            "</form>",
            '<section class="panel action-panel">',
            "<h2>오늘 결론 보기</h2>",
            '<a class="button-link" href="/dashboard" target="_blank" rel="noreferrer">대시보드 열기</a>',
            "</section>",
            "</section>",
            error_html,
            result_html,
            "</main>",
            "</body>",
            "</html>",
        ]
    )


def run_local_app(project_root: Path | str, host: str = "127.0.0.1", port: int = 8765) -> None:
    config = LocalAppConfig(project_root=Path(project_root).resolve(), host=host, port=port)
    server = ThreadingHTTPServer((config.host, config.port), _handler(config))
    try:
        server.serve_forever()
    finally:
        server.server_close()


def _handler(config: LocalAppConfig) -> type[BaseHTTPRequestHandler]:
    class LocalAppHandler(BaseHTTPRequestHandler):
        def do_GET(self) -> None:  # noqa: N802
            if self.path in {"/", "/index.html"}:
                _send_html(self, render_home())
                return
            if self.path == "/dashboard":
                dashboard = config.project_root / "reports" / "dashboard" / "index.html"
                if dashboard.exists():
                    _send_html(self, dashboard.read_text(encoding="utf-8"))
                else:
                    _send_html(self, render_home(error="대시보드가 아직 없습니다. 오늘 분석 실행을 먼저 누르세요."))
                return
            if self.path == "/health":
                _send_text(self, "OK")
                return
            self.send_error(404)

        def do_POST(self) -> None:  # noqa: N802
            if self.path != "/run":
                self.send_error(404)
                return
            length = int(self.headers.get("Content-Length", "0"))
            body = self.rfile.read(length).decode("utf-8")
            parsed = {key: values[-1] for key, values in parse_qs(body).items()}
            try:
                result = run_form_analysis(project_root=config.project_root, form=parsed)
                _send_html(self, render_home(result=result))
            except Exception as exc:  # pragma: no cover - defensive HTTP boundary
                _send_html(self, render_home(error=str(exc)))

        def log_message(self, format: str, *args: object) -> None:
            return

    return LocalAppHandler


def _render_result(result: TodayAnalysisOutput) -> str:
    rows = "".join(f"<li>{escape(line)}</li>" for line in result.lines)
    dashboard_path = escape(str(result.pipeline.summary["dashboard_path"]))
    return "\n".join(
        [
            '<section class="panel result-panel">',
            "<h2>실행 결과</h2>",
            f"<ol>{rows}</ol>",
            f'<p class="muted">대시보드 파일: {dashboard_path}</p>',
            '<a class="button-link" href="/dashboard" target="_blank" rel="noreferrer">오늘 결론 보기</a>',
            "</section>",
        ]
    )


def _send_html(handler: BaseHTTPRequestHandler, html: str) -> None:
    payload = html.encode("utf-8")
    handler.send_response(200)
    handler.send_header("Content-Type", "text/html; charset=utf-8")
    handler.send_header("Content-Length", str(len(payload)))
    handler.end_headers()
    handler.wfile.write(payload)


def _send_text(handler: BaseHTTPRequestHandler, text: str) -> None:
    payload = text.encode("utf-8")
    handler.send_response(200)
    handler.send_header("Content-Type", "text/plain; charset=utf-8")
    handler.send_header("Content-Length", str(len(payload)))
    handler.end_headers()
    handler.wfile.write(payload)


def _css() -> str:
    return """
:root {
  color-scheme: light;
  --ink: #18242c;
  --muted: #667680;
  --line: #d7dee4;
  --paper: #f5f7f8;
  --panel: #ffffff;
  --blue: #176b87;
  --green: #16794c;
  --red: #b42318;
}
* { box-sizing: border-box; }
body {
  margin: 0;
  background: var(--paper);
  color: var(--ink);
  font: 16px/1.6 "Segoe UI", "Malgun Gothic", Arial, sans-serif;
}
.page { width: min(1040px, calc(100% - 28px)); margin: 24px auto 44px; }
.topbar {
  display: flex;
  justify-content: space-between;
  align-items: center;
  gap: 14px;
  margin-bottom: 16px;
}
h1, h2, p { margin-top: 0; letter-spacing: 0; }
h1 { margin-bottom: 4px; font-size: 32px; line-height: 1.15; }
h2 { margin-bottom: 12px; font-size: 20px; }
.topbar p, .muted { color: var(--muted); }
.safe {
  border: 1px solid var(--green);
  color: var(--green);
  border-radius: 999px;
  padding: 7px 11px;
  font-size: 13px;
  font-weight: 800;
  background: #fff;
}
.workflow {
  display: grid;
  grid-template-columns: minmax(0, 1fr) 280px;
  gap: 12px;
  align-items: stretch;
}
.panel, .notice {
  background: var(--panel);
  border: 1px solid var(--line);
  border-radius: 8px;
  padding: 18px;
}
.input-row {
  display: grid;
  grid-template-columns: minmax(0, 1fr) 150px;
  gap: 10px;
}
input[type="text"] {
  width: 100%;
  border: 1px solid var(--line);
  border-radius: 6px;
  padding: 12px 13px;
  font: inherit;
  background: #fff;
}
button, .button-link {
  display: inline-flex;
  align-items: center;
  justify-content: center;
  min-height: 48px;
  border: 0;
  border-radius: 6px;
  padding: 0 16px;
  background: var(--blue);
  color: #fff;
  font: inherit;
  font-weight: 800;
  text-decoration: none;
  cursor: pointer;
}
.check-row {
  display: flex;
  align-items: center;
  gap: 8px;
  margin-top: 12px;
  color: var(--muted);
  font-size: 14px;
}
.action-panel { display: flex; flex-direction: column; justify-content: center; }
.result-panel, .notice { margin-top: 12px; }
.result-panel ol { margin: 0 0 12px; padding-left: 22px; }
.error { border-color: var(--red); color: var(--red); }
@media (max-width: 760px) {
  .topbar, .workflow { grid-template-columns: 1fr; flex-direction: column; align-items: flex-start; }
  .input-row { grid-template-columns: 1fr; }
  button, .button-link { width: 100%; }
}
"""
