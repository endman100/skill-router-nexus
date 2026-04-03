---
name: system-monitor
description: "Read the latest system resource logs (CPU, GPU, RAM, Disk) from the local monitoring daemon. Use when the user asks about system load, resource usage, or how the machine is performing."
metadata: { "openclaw": { "emoji": "📊", "requires": { "files": ["C:/Users/endma/clawd/system_logs/"] } } }
---

# System Monitor Skill

Read and report the latest system resource statistics captured by the background daemon.

## When to Use

✅ **USE this skill when:**

- "What's the system load?"
- "How much GPU/VRAM am I using?"
- "Check system health"
- "Are the resources full?"
- "Show me the latest hardware stats"

## Usage

The monitoring daemon saves logs in `C:\Users\endma\clawd\system_logs/system_stats_YYYY-MM-DD.jsonl`.
This skill involves reading the last line of the current day's log file.

### Get Latest Stats (PowerShell)

```powershell
# Get the latest log file and read the last line
$today = Get-Date -Format "yyyy-MM-dd"
$logFile = "C:\Users\endma\clawd\system_logs\system_stats_$today.jsonl"
Get-Content $logFile -Tail 1
```

### Charting Data (Python Example with Zero-Padding)

When generating charts, ensure that missing values (e.g., if the daemon was down) are padded with `0` or handled gracefully to maintain time-series integrity.

```python
# Example logic for zero-padding missing intervals
# (Calculate expected timestamps vs actual timestamps in log)
```
