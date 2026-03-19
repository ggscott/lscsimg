with open('app.py', 'r') as f:
    lines = f.readlines()

for i, line in enumerate(lines):
    if 635 <= i <= 655:
        print(f"{i}: {repr(line)}")

with open('app.py', 'w') as f:
    for i, line in enumerate(lines):
        if i == 641:
            f.write("    if render_type == \"zone\":\n")
        elif i == 642:
            f.write("        images = render_zone(data, prev_data, regionName, primsHistory)\n")
        elif i == 643:
            f.write("    else:\n")
        elif i == 644:
            f.write("        images = render_sim(data, prev_data, regionName)\n")
        else:
            f.write(line)
