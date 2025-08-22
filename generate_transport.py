def seed_transport(cur):
    data = [
        (1, 1, 101, 'Route A', 'Pickup', 'Drop',
         'John Doe', 9876543210,"16.50", "80.64")        
    ]

    cur.executemany("""
        INSERT INTO student_transport
        (student_id, fk_route_id, fk_student_id, route_name, pickup_point, drop_point, driver_name, driver_phone, bus_lat, bus_lon)
        VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
    """, data)
