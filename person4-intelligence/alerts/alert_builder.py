"""Package an anomaly dict into the person4_to_person5.json alert
contract that Person 5's backend ingests.
"""


def _severity_for_travel_time(deviation_pct):
    if deviation_pct >= 200:
        return "HIGH"
    if deviation_pct >= 100:
        return "MEDIUM"
    return "LOW"


def build_travel_time_alert(anomaly):
    """anomaly: one item from anomaly.travel_time_anomaly.check_trajectory()."""
    return {
        "vehicle_id": anomaly["vehicle_id"],
        "event_type": "TRAJECTORY_ANOMALY",
        "severity": _severity_for_travel_time(anomaly["deviation_pct"]),
        "confidence": min(0.99, 0.5 + anomaly["deviation_pct"] / 400),
        "reason": anomaly["reason"],
    }


def build_route_alert(anomaly):
    """anomaly: one item from anomaly.route_anomaly.check_trajectory()."""
    return {
        "vehicle_id": anomaly["vehicle_id"],
        "event_type": "ROUTE_ANOMALY",
        "severity": "MEDIUM",
        "confidence": 0.75,
        "reason": anomaly["reason"],
    }


def build_blacklist_alert(anomaly):
    """anomaly: one item from anomaly.blacklist_check.check_trajectory()."""
    return {
        "vehicle_id": anomaly["vehicle_id"],
        "event_type": "BLACKLIST_MATCH",
        "severity": "HIGH",
        "confidence": 1.0,
        "reason": anomaly["reason"],
    }


def build_alerts(travel_time_anomalies, route_anomalies, blacklist_anomalies=()):
    """Convenience: combine all anomaly types for one vehicle into a
    flat list of alert contract dicts.
    """
    alerts = [build_travel_time_alert(a) for a in travel_time_anomalies]
    alerts.extend(build_route_alert(a) for a in route_anomalies)
    alerts.extend(build_blacklist_alert(a) for a in blacklist_anomalies)
    return alerts
