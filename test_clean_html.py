def clean_html(s: str) -> str:
    """
    Guarantees that NO line in the HTML string starts with 4 or more spaces,
    which would cause Streamlit/Markdown to parse it as a <pre><code> block.
    Strips leading and trailing whitespace from every line.
    """
    if not s:
        return ""
    return "\n".join(line.strip() for line in s.splitlines() if line.strip())

sample = """
    <div style="color: red;">
        <span class="badge">Hello</span>
        <img src="data:image/png;base64,1234" />
    </div>
"""
res = clean_html(sample)
print("Result:")
print(repr(res))
for line in res.splitlines():
    assert not line.startswith("    "), f"Failed: {line}"
print("ASSERTION PASSED: No line starts with 4 spaces!")

