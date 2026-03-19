from fastapi.testclient import TestClient
from app import app
import time

client = TestClient(app)

data = {
    "regionName": "TestRegion",
    "type": "sim",
    "data": {
        "agents": 10,
        "fps": 45.0,
        "dilation": 1.0,
        "lag": 2,
        "users": [
            {
                "uuid": "test-uuid-1",
                "name": "User One",
                "category": 1,
                "isOOC": False,
                "isChar": True,
                "total": 100,
                "active": 50,
                "time": 2.5,
                "memory": 1024000,
                "complexity": 500
            }
        ]
    },
    "previousData": {
        "agents": 8,
        "fps": 44.0,
        "dilation": 0.9,
        "lag": 1,
        "users": [
            {
                "uuid": "test-uuid-1",
                "name": "User One",
                "category": 1,
                "isOOC": False,
                "isChar": True,
                "total": 90,
                "active": 40,
                "time": 2.0,
                "memory": 900000,
                "complexity": 450
            }
        ]
    }
}

start = time.time()
response = client.post("/render", json=data)
end = time.time()

print(f"Status Code: {response.status_code}")
print(f"Response: {response.json()}")
print(f"Time taken: {end - start:.4f} seconds")
