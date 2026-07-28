# Secret Rotation Runbook

Checklist for rotating credentials after exposure or on schedule.  
**No real secrets are stored in this repository.** Replace `<VPS_IP>` etc. with actual values only when performing rotation on a live host.

## 1. Rotate Client UUIDs

1. Edit `group_vars/all.yml` — change `num_clients` if you need more/fewer UUIDs.
2. Re-run the playbook: `ansible-playbook -i inventory.yml deploy.yml`.
3. New UUIDs are generated and new client configs exported.
4. Old client configs (`/root/vpn-configs/client_*.json`, `/root/vpn-configs/clash_*.yaml`) are overwritten.
5. Distribute new configs to clients.

## 2. Rotate REALITY Key Pair

REALITY `privateKey` / `publicKey` are generated fresh on every playbook run (`teddysun/xray:26.6.27` keygen).
1. Delete (or rename) the old Xray config:  
   `ssh root@<VPS_IP> mv /root/xray-config/config.json /root/xray-config/config.json.old`
2. Re-run the playbook. A new key pair and shortId are generated.
3. New client configs reference the new public key.
4. Clients must import updated configs.

## 3. Rotate WARP Credentials

WARP credentials (WireGuard secret key, peer public key, IP addresses) come from `wgcf`.
1. SSH to VPS: `ssh root@<VPS_IP>`
2. Delete Cloudflare WARP identity files:
   ```bash
   rm -f /root/xray-config/wgcf-account.toml
   rm -f /root/xray-config/wgcf-profile.conf
   rm -f /root/xray-config/wgcf-identity.json
   ```
3. Re-run the playbook — `wgcf register` and `wgcf generate` create fresh credentials.
4. Verify WARP egress:  
   `ssh root@<VPS_IP> docker exec xray /usr/bin/curl --max-time 5 -s -o /dev/null -w '%{http_code}' http://1.1.1.1`  
   Should return `301` or `200`.

## 4. General Post-Rotation Verification

- `docker inspect xray` — image should be `teddysun/xray:26.6.27`.
- `journalctl -u xray --no-pager -n 30` — no REALITY auth errors.
- Port 443 TCP accepting: `nc -zv <VPS_IP> 443`.
- Upload new client config and test from at least one device.
