with open('app.py', 'r') as f:
    content = f.read()

content = content.replace('for _ in range(15):', 'for _ in range(30):')
content = content.replace('# Poll up to 15 times, waiting 1 second between checks', '# Poll up to 30 times, waiting 1 second between checks')

with open('app.py', 'w') as f:
    f.write(content)
