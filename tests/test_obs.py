"""Phase F observability — metrics registry rendering (hermetic)."""

from __future__ import annotations

from acip_core.obs import Metrics


def test_counter_and_summary_render_prometheus():
    m = Metrics()
    m.inc("vitrin_http_requests_total", {"method": "GET", "status": "200"})
    m.inc("vitrin_http_requests_total", {"method": "GET", "status": "200"})
    m.inc("vitrin_http_requests_total", {"method": "POST", "status": "500"})
    m.observe("vitrin_http_request_duration_seconds", 0.25, {"method": "GET"})
    m.gauge("vitrin_readyz_ok", 1.0)
    out = m.render()

    assert "# TYPE vitrin_http_requests_total counter" in out
    assert 'vitrin_http_requests_total{method="GET",status="200"} 2' in out
    assert 'vitrin_http_requests_total{method="POST",status="500"} 1' in out
    assert "# TYPE vitrin_http_request_duration_seconds summary" in out
    assert "vitrin_http_request_duration_seconds_count{method=\"GET\"} 1" in out
    assert "vitrin_readyz_ok 1" in out
    assert "vitrin_build_info" in out


def test_empty_registry_still_has_build_info():
    assert "vitrin_build_info" in Metrics().render()
