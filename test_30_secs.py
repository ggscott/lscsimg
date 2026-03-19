from fastapi.testclient import TestClient
from app import app
import time
import os
import threading

client = TestClient(app)

def delayed_file_creation(filepath):
    time.sleep(25) # Simulate a very long animation time + PVC sync
    os.makedirs(os.path.dirname(filepath), exist_ok=True)
    with open(filepath, 'wb') as f:
        f.write(b"fake gif content after 25s")

fake_filename = "delayed_30_secs_file.gif"
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
