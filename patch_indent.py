with open('app.py', 'r') as f:
    lines = f.readlines()

with open('app.py', 'w') as f:
    for i, line in enumerate(lines):
        if i >= 641 and i <= 644:  # lines 642-645
            if line.startswith('        if'):
                f.write(line[4:])
            elif line.startswith('        images'):
                f.write(line[4:])
            elif line.startswith('    else:'):
                f.write(line)
            else:
                f.write(line)
        else:
            f.write(line)
