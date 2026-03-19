import os
import sys

# Import functions directly from app.py
from app import render_sim, render_zone

def get_sim_data():
    return {
        "agents": 15,
        "fps": 44.5,
        "dilation": 0.98,
        "lag": 5,
        "users": [
            {
                "uuid": "1111-2222-3333-4444",
                "name": "Alice Resident",
                "category": 1,
                "isOOC": False,
                "isChar": True,
                "total": 12,
                "active": 10,
                "time": 0.5,
                "memory": 204800,
                "complexity": 50000
            },
            {
                "uuid": "5555-6666-7777-8888",
                "name": "Bob OOC",
                "category": 2,
                "isOOC": True,
                "display_name": "Bob (AFK)",
                "isChar": False,
                "total": 5,
                "active": 2,
                "time": 0.1,
                "memory": 51200,
                "complexity": 15000
            },
            {
                "uuid": "9999-0000-aaaa-bbbb",
                "name": "Charlie Heavy",
                "category": 1,
                "isOOC": False,
                "isChar": False,
                "total": 50,
                "active": 45,
                "time": 6.2,
                "memory": 1572864,
                "complexity": 120000
            }
        ]
    }

def get_prev_sim_data():
    return {
        "agents": 14,
        "fps": 45.0,
        "dilation": 1.0,
        "lag": 2,
        "users": [
            {
                "uuid": "1111-2222-3333-4444",
                "name": "Alice Resident",
                "category": 1,
                "isOOC": False,
                "isChar": True,
                "total": 10,
                "active": 8,
                "time": 0.4,
                "memory": 102400,
                "complexity": 45000
            },
            {
                "uuid": "5555-6666-7777-8888",
                "name": "Bob OOC",
                "category": 2,
                "isOOC": True,
                "display_name": "Bob",
                "isChar": False,
                "total": 5,
                "active": 2,
                "time": 0.1,
                "memory": 51200,
                "complexity": 15000
            }
        ]
    }

def get_zone_data():
    return {
        "remaining_prims": 2500,
        "status": "Online",
        "fps": 44.5,
        "lag": 5,
        "zones": [
            {
                "uuid": "z1",
                "name": "Market Square",
                "isDynamic": False,
                "occupancyText": "12",
                "dynamicText": "Static",
                "rezStatusText": "-",
                "liEstText": "-"
            },
            {
                "uuid": "z2",
                "name": "Player House 1",
                "isDynamic": True,
                "occupancyText": "2",
                "dynamicText": "Ready",
                "rezStatusText": "Deployed",
                "liEstText": "150"
            },
            {
                "uuid": "z3",
                "name": "Player House 2",
                "isDynamic": True,
                "occupancyText": "0",
                "dynamicText": "Ready",
                "rezStatusText": "Not Deployed",
                "liEstText": "320"
            }
        ]
    }

def get_prev_zone_data():
    return {
        "remaining_prims": 2550,
        "status": "Online",
        "fps": 45.0,
        "lag": 2,
        "zones": [
            {
                "uuid": "z1",
                "name": "Market Square",
                "isDynamic": False,
                "occupancyText": "10",
                "dynamicText": "Static",
                "rezStatusText": "-",
                "liEstText": "-"
            },
            {
                "uuid": "z2",
                "name": "Player House 1",
                "isDynamic": True,
                "occupancyText": "0",
                "dynamicText": "Ready",
                "rezStatusText": "Not Deployed",
                "liEstText": "150"
            }
        ]
    }

def run_sim():
    print("Rendering sim data...")
    data = get_sim_data()
    prev_data = get_prev_sim_data()
    region_name = "Prototype Sim Region"

    # render_sim returns a list of PIL Images
    images = render_sim(data, prev_data, region_name)
    return images, "sim"

def run_zone():
    print("Rendering zone data...")
    data = get_zone_data()
    prev_data = get_prev_zone_data()
    region_name = "Prototype Zone Region"
    history = [2550, 2530, 2520, 2540, 2500]

    # render_zone returns a list of PIL Images
    images = render_zone(data, prev_data, region_name, history)
    return images, "zone"

def save_images(images, render_type):
    if not images:
        print("No images to save.")
        return

    os.makedirs("static", exist_ok=True)
    filename = f"prototype_render_{render_type}.gif"
    filepath = os.path.join("static", filename)

    if len(images) > 1:
        images[0].save(filepath, save_all=True, append_images=images[1:], duration=125, loop=1)
    else:
        images[0].save(filepath)

    print(f"[{render_type.upper()}] Success! Saved to: {os.path.abspath(filepath)}")

def main():
    import argparse
    parser = argparse.ArgumentParser(description="Prototype graphic improvements for render microservice.")
    parser.add_argument('render_type', nargs='?', choices=['sim', 'zone', 'both'], default='both',
                        help='Which type to render (sim, zone, or both). Default is both.')
    args = parser.parse_args()

    if args.render_type in ['sim', 'both']:
        images, render_type = run_sim()
        save_images(images, render_type)

    if args.render_type in ['zone', 'both']:
        images, render_type = run_zone()
        save_images(images, render_type)

if __name__ == "__main__":
    main()
