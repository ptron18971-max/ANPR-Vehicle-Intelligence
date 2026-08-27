"""Tunable thresholds for Person 4's analytics/anomaly modules. Kept in
one place so they can be recalibrated against real Person 3 data
without hunting through module code.
"""

TRAVEL_TIME_DEVIATION_THRESHOLD = 2.0  # observed / expected_max ratio that triggers a travel-time anomaly
RARE_EDGE_PROBABILITY_THRESHOLD = 0.2  # historical_probability below this counts as a rare-route anomaly
CONGESTION_VEHICLES_PER_HOUR = 10      # observations/hour at a camera above this counts as congested
