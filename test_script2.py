from fastapi.testclient import TestClient
from app import app
import time

client = TestClient(app)

data_zone = {
    "regionName": "TestZoneRegion",
    "type": "zone",
    "primsHistory": [1000, 950, 900, 850, 800],
    "data": {
        "remaining_prims": 800,
        "status": "Online",
        "fps": 45.0,
        "lag": 2,
        "zones": [
            {
                "uuid": "zone-1",
                "name": "Central Plaza",
                "isDynamic": True,
                "occupancyText": "15",
                "dynamicText": "YES",
                "rezStatusText": "Deployed",
                "liEstText": "500"
            }
        ]
    },
    "previousData": {
        "remaining_prims": 850,
        "status": "Online",
        "fps": 44.0,
        "lag": 1,
        "zones": [
            {
                "uuid": "zone-1",
                "name": "Central Plaza",
                "isDynamic": True,
                "occupancyText": "10",
                "dynamicText": "YES",
                "rezStatusText": "Rezzing",
                "liEstText": "450"
            }
        ]
    }
}

start = time.time()
response = client.post("/render", json=data_zone)
end = time.time()

print(f"Status Code (zone): {response.status_code}")
print(f"Response (zone): {response.json()}")
print(f"Time taken (zone): {end - start:.4f} seconds")
