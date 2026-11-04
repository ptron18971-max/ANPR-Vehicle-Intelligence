from datetime import datetime, timedelta
from graph import G


def validate_transition(edge: dict, observed_time_sec: float) -> bool:
    """Validates if the observed transition time falls within edge bounds."""
    min_time = edge.get("min_travel_time_sec", 0)
    max_time = edge.get("max_travel_time_sec", float("inf"))
    return min_time <= observed_time_sec <= max_time

if __name__ == "__main__":
    edge = G["C01"]["C02"]
    # Example 2: Calculating observed_time_sec from datetime objects
    t1 = datetime(2026, 8, 27, 10, 0, 0)
    t2 = datetime(2026, 8, 27, 10, 2, 20)
    
    time_delta_sec = (t2 - t1).total_seconds()
    print(validate_transition(edge, time_delta_sec))