
#!/usr/bin/env python3
import subprocess
import sys

result = subprocess.run(
    ["python3", "-m", "pytest", "tests/", "-v"],
    cwd="/var/lib/alan-portfolio/workspaces/alan/rag-engine-alan-vo/backend",
    capture_output=True,
    text=True
)
print(result.stdout)
print(result.stderr, file=sys.stderr)
sys.exit(result.returncode)

