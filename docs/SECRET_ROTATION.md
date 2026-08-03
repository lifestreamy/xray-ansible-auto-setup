# Secret Rotation Runbook

Runbook for rotating credentials after exposure or on schedule. Replace `<VPS_IP>` and other placeholders only when performing rotation on a live host.

This document describes the actual behavior of the working Ansible role. If anything here does not match what a playbook run actually did, file an issue — the runbook is the source of truth for the operation, the role is the source of truth for the code.

## 1. Normal rerun

By default, a playbook run does **not** rotate anything. The role keeps your existing identity and credentials.

- REALITY `private_key`, `public_key`, `short_id`, and `client_uuids` are stored in `/root/xray-config/reality-state.json` (mode `0600`).
- WARP credentials are stored in `wgcf-account.toml` and `wgcf-profile.conf` under `/root/xray-config/`.
- The TEMPLATE `xray_config.json` is regenerated on every run from the stored state and the configured parameters.

So if you did not change anything between two runs, the second run produces identical client configs and the same Xray server identity.

## 2. Rotate the REALITY identity (full rekey)

Use this when the REALITY keys or short ID have been compromised, or on a scheduled rekey.

The role has a single switch:

```yaml
xray_reality_rotate: true
```

Pass it via `group_vars/all.yml` for a one-off run, or via `-e xray_reality_rotate=true` on the command line:

```bash
ansible-playbook -i inventory.yml deploy.yml -e xray_reality_rotate=true
```

What happens on a run with the toggle on:

1. The existing `reality-state.json` is backed up to `reality-state.json.bak-YYYY-MM-DD-HH:MM:SS` in the same directory.
2. The current state file is removed.
3. A fresh X25519 key pair is generated, a new random short ID is rolled, and client UUIDs are regenerated.
4. A new `reality-state.json` is written.
5. The Xray service is restarted with the new `config.json`.

After the run:

- Verify the new client configs in `/root/vpn-configs/` on the VPS, or download them locally (`downloaded-clients/`).
- Distribute the new configs to clients.
- Set `xray_reality_rotate` back to `false` in `group_vars/all.yml`. Leaving it `true` will rotate the identity on every playbook run, which you almost certainly do not want.

## 3. UUID-only changes

`num_clients` controls how many client configs are exported. With persistent state, the role has append-only behavior:

- Increase `num_clients` → new UUIDs are added to `reality-state.json` and new client configs are exported.
- Decrease `num_clients` → already-existing UUIDs in `reality-state.json` are kept; only the number of exported configs shrinks.
- Increase again → previously retained UUIDs become used again.

If you want to actually rotate (regenerate) the client UUIDs, go through the full rotation in section 2.

## 4. Rotate WARP credentials

WARP credentials come from `wgcf` and are stored in two files on the VPS:

- `/root/xray-config/wgcf-account.toml`
- `/root/xray-config/wgcf-profile.conf`

Note: there is no `wgcf-identity.json` in this setup. Older versions of the runbook mentioned that file; ignore that reference.

To rotate:

1. SSH to the VPS: `ssh root@<VPS_IP>`.
2. Remove the two files above.
3. Re-run the playbook. The role will call `wgcf register` and `wgcf generate` again, and the WARP outbound in `xray_config.json` will pick up the new credentials.

To verify WARP egress, do it from outside the VPS with a real client connected through the new WARP outbound — for example, check `https://ifconfig.io` or `https://cloudflare.com/cdn-cgi/trace` while the VPN is active. Do not rely on `curl` from inside the Xray container.

## 5. Recovery

The role already takes a timestamped backup before rotation, so a failed rotation is rarely destructive. A typical recovery:

1. SSH to the VPS: `ssh root@<VPS_IP>`.
2. List the backups: `ls -la /root/xray-config/reality-state.json.bak-*`.
3. If you want to revert to the previous state:
   ```bash
   cp /root/xray-config/reality-state.json.bak-YYYY-MM-DD-HH:MM:SS \
      /root/xray-config/reality-state.json
   chown root:root /root/xray-config/reality-state.json
   chmod 0600 /root/xray-config/reality-state.json
   ```
4. Make sure `xray_reality_rotate` is set to `false` in `group_vars/all.yml`.
5. Re-run the playbook. The role will reuse the restored state and regenerate `config.json` and the client configs to match it.

Keep at least the most recent backup until you have verified the new rotation end-to-end.

## 6. Post-deploy verification

After a successful rotation (or any playbook run):

- `docker inspect xray --format '{{ .Config.Image }}'` should return `teddysun/xray:26.6.27` (or whatever `xray_docker_image` is set to).
- `journalctl -u xray --no-pager -n 30` should not show REALITY handshake errors.
- The Xray TCP port (`xray_port`, default `443`) should be listening on the VPS: `nc -zv <VPS_IP> 443`.
- Connect from at least one real client (Clash Verge / FlClash / Amnezia) and verify that traffic goes through.

The post-deploy checks the role itself runs are non-fatal and only cover the pinned image, the listening port, and obvious journal errors. They do not replace the manual checks above.
