with open("static/script.js", "r") as f:
    content = f.read()

content = content.replace(
    """        name = (name || "").toString().replace(/let name = item.name || 'Unknown';/g, "&amp;").replace(/</g, "&lt;").replace(/>/g, "&gt;").replace(/"/g, "&quot;").replace(/'/g, "&#039;");""",
    """        name = (name || "").toString().replace(/&/g, "&amp;").replace(/</g, "&lt;").replace(/>/g, "&gt;").replace(/"/g, "&quot;").replace(/'/g, "&#039;");"""
)

content = content.replace(
    """        const name = (rawName || "").toString().replace(/const name = item.name || 'Unknown Zone';/g, "&amp;").replace(/</g, "&lt;").replace(/>/g, "&gt;").replace(/"/g, "&quot;").replace(/'/g, "&#039;");""",
    """        const name = (rawName || "").toString().replace(/&/g, "&amp;").replace(/</g, "&lt;").replace(/>/g, "&gt;").replace(/"/g, "&quot;").replace(/'/g, "&#039;");"""
)

with open("static/script.js", "w") as f:
    f.write(content)
