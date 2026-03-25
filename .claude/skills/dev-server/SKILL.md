---
name: dev-server
description: Launch the gwent dev server in the background with file logging and auto-rotation
allowed-tools: Bash
---

Launch the gwent dev server in the background using the dev-server.sh script.

Run the following command in the background:

```bash
bash scripts/dev-server.sh
```

After launching, confirm the process is running and remind the user they can watch logs with `tail -f /tmp/logs/gwent.log`.
