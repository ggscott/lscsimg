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
        "users": []
    }
}

start = time.time()
response = client.post("/render", json=data)
end = time.time()

print(f"Status Code: {response.status_code}")
print(f"Content Type: {response.headers.get('content-type')}")
print(f"Response Size: {len(response.content)} bytes")
print(f"Time taken: {end - start:.4f} seconds")
