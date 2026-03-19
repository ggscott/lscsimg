import re

with open('app.py', 'r') as f:
    content = f.read()

# render_sim
content = content.replace("frames = 32 if anyChanges else 1", "frames = 8 if anyChanges else 1")
content = content.replace("slideProgress = min(1.0, f / 16.0)", "slideProgress = min(1.0, f / 4.0)")
content = content.replace("if frames > 1 and f >= 16:", "if frames > 1 and f >= 4:")
content = content.replace("pulsePhase = (f - 16) / 15.0", "pulsePhase = (f - 4) / 3.0")

with open('app.py', 'w') as f:
    f.write(content)
