# Example overlays (not loaded automatically)

| File | Purpose |
|------|---------|
| `secrets.example.yml` | Optional `-e @file` via `EXTRA_VARS_FILE` for passwords / CA URL |

```bash
cp examples/secrets.example.yml ~/node-foundation-secrets.yml
# edit; optionally: ansible-vault encrypt ~/node-foundation-secrets.yml
EXTRA_VARS_FILE=~/node-foundation-secrets.yml ./run.sh
```

Do **not** commit filled copies. Inventory sample: `../inventory-example.yml` → `inventory.yml`.
Host overlays: copy `../host_vars/example.yml` → `host_vars/<inventory_hostname>.yml`.
