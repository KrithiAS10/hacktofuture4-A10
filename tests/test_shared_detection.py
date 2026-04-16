from lerna_shared.detection import build_detection_run_result


def test_shared_detection_builds_incident_for_error_logs():
    loki_raw = {
        "data": {
            "result": [
                {
                    "stream": {
                        "lerna.source.service": "payment-service",
                        "lerna.source.namespace": "lerna",
                    },
                    "values": [
                        ["1710000000000000000", "Fatal timeout while calling upstream"],
                        ["1710000001000000000", "retry failed after exception"],
                    ],
                }
            ]
        }
    }
    snapshot = {
        "available": True,
        "namespace_scope": "lerna",
        "recent_events": [
            {
                "type": "Warning",
                "namespace": "lerna",
                "object": "payment-service",
                "message": "Back-off restarting failed container",
                "last_timestamp": "2026-04-16T00:00:00Z",
            }
        ],
    }

    result = build_detection_run_result(loki_raw, snapshot)

    assert result.check.has_error is True
    assert result.incident is not None
    assert result.incident.service == "payment-service"
    assert result.incident.namespace == "lerna"
    assert result.incident.incident_class in {"timeout", "crashloop", "application-error"}
    assert result.incident.fingerprint


def test_shared_detection_skips_incident_when_only_info_signals_exist():
    loki_raw = {
        "data": {
            "result": [
                {
                    "stream": {"lerna.source.service": "catalog"},
                    "values": [["1710000000000000000", "request completed successfully"]],
                }
            ]
        }
    }
    snapshot = {"available": True, "namespace_scope": "lerna", "recent_events": []}

    result = build_detection_run_result(loki_raw, snapshot)

    assert result.check.has_error is False
    assert result.incident is None
