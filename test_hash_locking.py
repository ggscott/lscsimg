from fastapi.testclient import TestClient
from app import app
import time
import os
import threading
from concurrent.futures import ThreadPoolExecutor

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

def make_request(i):
    start = time.time()
    resp = client.post("/render", json=data)
    end = time.time()
    print(f"Request {i} finished in {end-start:.4f}s with status {resp.status_code}")
    return resp.json()

# Make 10 concurrent requests
start = time.time()
with ThreadPoolExecutor(max_workers=10) as executor:
    results = list(executor.map(make_request, range(10)))
end = time.time()

print(f"Total time for 10 concurrent requests: {end-start:.4f}s")

# Ensure all returned the exact same URL
url = results[0]['url']
print(f"Returned URL: {url}")
all_match = all(r['url'] == url for r in results)
print(f"All URLs match: {all_match}")
