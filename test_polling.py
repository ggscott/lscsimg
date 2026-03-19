from fastapi.testclient import TestClient
from app import app
import time
import os
import threading

client = TestClient(app)

def delayed_file_creation(filepath):
    time.sleep(3)
    os.makedirs(os.path.dirname(filepath), exist_ok=True)
    with open(filepath, 'wb') as f:
        f.write(b"fake gif content")

# Test 1: File is created instantly by /render
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
resp = client.post("/render", json=data)
print(f"Render POST: {resp.status_code}, {resp.json()}")

url_path = resp.json()['url'].split('http://testserver')[1]
print(f"Fetching {url_path}...")
start = time.time()
resp_get = client.get(url_path)
end = time.time()
print(f"Instant GET: {resp_get.status_code}, length: {len(resp_get.content)}, time: {end-start:.2f}s")


# Test 2: File is delayed (simulating network sync delay)
fake_filename = "delayed_file.gif"
fake_filepath = os.path.join("static", fake_filename)

if os.path.exists(fake_filepath):
    os.remove(fake_filepath)

threading.Thread(target=delayed_file_creation, args=(fake_filepath,)).start()

start = time.time()
resp_get_delayed = client.get(f"/static/{fake_filename}")
end = time.time()
print(f"Delayed GET: {resp_get_delayed.status_code}, length: {len(resp_get_delayed.content)}, time: {end-start:.2f}s")

# Clean up
if os.path.exists(fake_filepath):
    os.remove(fake_filepath)
