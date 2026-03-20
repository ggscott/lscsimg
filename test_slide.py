from fastapi.testclient import TestClient
from app import app
import time
import os

client = TestClient(app)

# Test 1: Adding a row
data_add = {
    "regionName": "TestSimAdd",
    "type": "sim",
    "data": {
        "agents": 3,
        "fps": 45.0,
        "dilation": 1.0,
        "lag": 2,
        "users": [
            {
                "uuid": "test-uuid-1",
                "name": "Alice",
                "category": 1,
                "isOOC": False,
                "isChar": True,
                "total": 100,
                "active": 50,
                "time": 2.5,
                "memory": 1024000,
                "complexity": 500
            },
            {
                "uuid": "test-uuid-2",
                "name": "Bob",
                "category": 1,
                "isOOC": False,
                "isChar": True,
                "total": 100,
                "active": 50,
                "time": 2.5,
                "memory": 1024000,
                "complexity": 500
            },
            {
                "uuid": "test-uuid-3", # newly added
                "name": "Charlie",
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
        "agents": 2,
        "fps": 44.0,
        "dilation": 0.9,
        "lag": 1,
        "users": [
            {
                "uuid": "test-uuid-1",
                "name": "Alice",
                "category": 1,
                "isOOC": False,
                "isChar": True,
                "total": 90,
                "active": 40,
                "time": 2.0,
                "memory": 900000,
                "complexity": 450
            },
            {
                "uuid": "test-uuid-3",
                "name": "Charlie",
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

# In data_add, previously Alice and Charlie. Now Alice, Bob, Charlie.
# Since Bob is alphabetically between Alice and Charlie (if category is same), Charlie should slide down.

print("Running Add Row Test...")
start = time.time()
response_add = client.post("/render", json=data_add)
end = time.time()

print(f"Status Code: {response_add.status_code}")
print(f"Response: {response_add.json()}")
print(f"Time taken: {end - start:.4f} seconds")

# Test 2: Removing a row
data_remove = {
    "regionName": "TestSimRemove",
    "type": "sim",
    "data": {
        "agents": 2,
        "fps": 45.0,
        "dilation": 1.0,
        "lag": 2,
        "users": [
            {
                "uuid": "test-uuid-1",
                "name": "Alice",
                "category": 1,
                "isOOC": False,
                "isChar": True,
                "total": 100,
                "active": 50,
                "time": 2.5,
                "memory": 1024000,
                "complexity": 500
            },
            {
                "uuid": "test-uuid-3",
                "name": "Charlie",
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
        "agents": 3,
        "fps": 44.0,
        "dilation": 0.9,
        "lag": 1,
        "users": [
            {
                "uuid": "test-uuid-1",
                "name": "Alice",
                "category": 1,
                "isOOC": False,
                "isChar": True,
                "total": 90,
                "active": 40,
                "time": 2.0,
                "memory": 900000,
                "complexity": 450
            },
            {
                "uuid": "test-uuid-2",
                "name": "Bob",
                "category": 1,
                "isOOC": False,
                "isChar": True,
                "total": 90,
                "active": 40,
                "time": 2.0,
                "memory": 900000,
                "complexity": 450
            },
            {
                "uuid": "test-uuid-3",
                "name": "Charlie",
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

# In data_remove, previously Alice, Bob, Charlie. Now Alice, Charlie.
# Charlie should slide up to replace Bob.

print("Running Remove Row Test...")
start = time.time()
response_remove = client.post("/render", json=data_remove)
end = time.time()

print(f"Status Code: {response_remove.status_code}")
print(f"Response: {response_remove.json()}")
print(f"Time taken: {end - start:.4f} seconds")
