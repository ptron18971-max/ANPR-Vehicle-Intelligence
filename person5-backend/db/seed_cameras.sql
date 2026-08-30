INSERT INTO camera (camera_id, location, road_segment, status, installed_at) VALUES
('C01', ST_SetSRID(ST_MakePoint(77.5946, 12.9716), 4326), 'MG Road Junction', 'active', '2025-11-01T00:00:00Z'),
('C02', ST_SetSRID(ST_MakePoint(77.6010, 12.9760), 4326), 'Brigade Road', 'active', '2025-11-01T00:00:00Z'),
('C03', ST_SetSRID(ST_MakePoint(77.6080, 12.9800), 4326), 'Cunningham Road', 'active', '2025-11-02T00:00:00Z'),
('C04', ST_SetSRID(ST_MakePoint(77.6120, 12.9850), 4326), 'Residency Road', 'active', '2025-11-02T00:00:00Z'),
('C05', ST_SetSRID(ST_MakePoint(77.6050, 12.9900), 4326), 'Richmond Circle', 'offline', '2025-11-03T00:00:00Z'),
('C06', ST_SetSRID(ST_MakePoint(77.5900, 12.9680), 4326), 'Lalbagh Main Gate', 'active', '2025-11-03T00:00:00Z');