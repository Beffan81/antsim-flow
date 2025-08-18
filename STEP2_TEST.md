# Step 2 - Start Mechanism Testing

## Quick Test
```bash
# Terminal 1: Start backend
python start_backend.py

# Terminal 2: Run tests
python test_step2.py
```

## Manual Testing

### 1. Test /start endpoint
```bash
curl -X POST http://127.0.0.1:8000/start \
  -H "Content-Type: application/json" \
  -d '{
    "simulation": {
      "environment": {"width": 100, "height": 100, "entry_positions": [[50, 50]]},
      "agent": {"energy": 100, "max_energy": 100, "stomach_capacity": 50, "social_stomach_capacity": 50, "hunger_threshold": 30},
      "behavior_tree": {
        "root": {"type": "step", "name": "test_move", "step": {"name": "move", "params": {}}}
      }
    },
    "options": {"format": "json"}
  }'
```

### 2. Test /status endpoint (use run_id from start response)
```bash
curl http://127.0.0.1:8000/status/YOUR_RUN_ID
```

### 3. Test /stop endpoint
```bash
curl -X POST http://127.0.0.1:8000/stop/YOUR_RUN_ID
```

## Expected Behavior

1. **Start**: Returns `{"ok": true, "run_id": "...", "pid": 12345, "config_path": "/tmp/..."}`
2. **Status**: Returns `{"state": "running", "pid": 12345}` or `{"state": "exited", "exit_code": 0, "pid": 12345}`
3. **Stop**: Returns `{"ok": true, "state": "exited", "exit_code": null, "pid": 12345}`

## Troubleshooting

- If start fails with "missing steps": Check that plugins are loaded with `curl http://127.0.0.1:8000/plugins`
- If subprocess fails: Check that `python -m antsim` works in your environment
- If validation fails: Use `/validate` endpoint first to check your config