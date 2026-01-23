#!/usr/bin/env bash
set -euo pipefail

VERSION="v2025-12-13" # YYYY-MM-DD
LICENSE="MIT"
AUTHOR="Tim Korelov"
CONTACT_URL="https://github.com/lifestreamy"

show_banner() {
  echo "=== XRAY+Amnezia VPN Provisioning Script (${VERSION}) ==="
  echo "Author: ${AUTHOR}  |  ${CONTACT_URL}"
  echo "License: ${LICENSE}"
  echo "Tip: Run '$(basename "$0") --help' to see the project description, all options, and examples."
  echo
}

show_help() {
  cat <<EOF
provision-vpn.sh - Provision and configure a VPN server via Ansible.

Usage:
  $(basename "$0") [OPTIONS]

This script:
  - Sets up a temporary workspace with your Ansible project.
  - Ensures required packages (python3, python3-venv, ansible, sshpass) are installed.
  - Runs the Ansible playbook (deploy.yml) against the target VPS.
  - Copies generated client configs from 'downloaded-configs/' to a chosen directory.

Parameter modes:
  --use-inventory           Use values from inventory.yml instead of CLI parameters.
                            Validates that inventory.yml has all required fields.
                            Ignores any CLI connection/auth parameters provided.
                            Default: CLI mode (parameters required via flags).

Connection options (CLI mode):
  -H, --host VALUE          VPS IP / hostname (required in CLI mode).
  -u, --user VALUE          SSH user (default: root).
  -p, --port VALUE          SSH port (default: 22).

Authentication options (CLI mode):
  --pkey PATH               Path to SSH private key for key-based auth.
  --pass PASSWORD           SSH password for password-based auth (plain text).
                            If neither --pkey nor --pass is provided, you will be
                            interactively prompted for a hidden SSH password.
  --pkey and --pass are mutually exclusive.

Client config output:
  --clients-dir PATH        Directory to store generated client configs.
                            If omitted, a 'downloaded-clients' directory is created
                            next to this script.

Cleanup options:
  --cleanup                 Default. Remove only the temporary workspace after run.
  --full-cleanup            Remove temporary workspace AND any packages installed
                            by this script.
  --no-cleanup              Keep the temporary workspace for debugging/inspection.

Other:
  -h, --help                Show this help message and exit.
  --dry-run                 Simulate actions without changing the system.
                            Shows what would be done but does not install
                            packages, run Ansible, or remove anything.

Examples:
  CLI mode (default):
    $(basename "$0") -H 1.2.3.4 --pkey /home/user/.ssh/id_rsa
    $(basename "$0") -H vps.example.com -u root --pass 'secret' --clients-dir /tmp/vpn-clients
    $(basename "$0") -H 1.2.3.4 -u root  (prompts for SSH password interactively)
    $(basename "$0") -H 1.2.3.4 --pkey ~/.ssh/id_rsa --no-cleanup

  All options:
    $(basename "$0") -H 192.168.1.100 -u admin -p 2222 --pkey ~/.ssh/vps_key --clients-dir ~/vpn-configs --full-cleanup --dry-run
  
  Inventory mode:
    $(basename "$0") --use-inventory --full-cleanup --clients-dir ~/vpn-configs
EOF
}

# Extract value from inventory.yml
get_inventory_value() {
  local key="$1"
  local file="${2:-$SCRIPT_DIR/inventory.yml}"
  grep "^\s*${key}:" "$file" 2>/dev/null | sed "s/.*${key}:\s*//" | xargs
}

# Validate inventory.yml has all required fields
validate_inventory() {
  local inv_host=$(get_inventory_value "ansible_host")
  local inv_user=$(get_inventory_value "ansible_user")
  local inv_port=$(get_inventory_value "ansible_port")
  local inv_key=$(get_inventory_value "ansible_ssh_private_key_file")
  local inv_pass=$(get_inventory_value "ansible_ssh_pass")
  
  local missing=()
  
  [[ -z "$inv_host" ]] && missing+=("ansible_host")
  [[ -z "$inv_user" ]] && missing+=("ansible_user")
  [[ -z "$inv_port" ]] && missing+=("ansible_port")
  [[ -z "$inv_key" && -z "$inv_pass" ]] && missing+=("auth (ansible_ssh_private_key_file or ansible_ssh_pass)")
  
  if [[ ${#missing[@]} -gt 0 ]]; then
    echo "Error: inventory.yml missing required fields:" >&2
    for field in "${missing[@]}"; do
      echo "  - $field" >&2
    done
    return 1
  fi
  
  # Check mutual exclusion
  if [[ -n "$inv_key" && -n "$inv_pass" ]]; then
    echo "Error: You have both private key and password defined in inventory.yml." >&2
    echo "Leave only one in the config (ansible_ssh_private_key_file OR ansible_ssh_pass)." >&2
    return 1
  fi

  return 0
}

CLEANUP_MODE="cleanup"
DRY_RUN=0
USE_INVENTORY=0

CLIENTS_DIR=""
HOST=""
USER_NAME="root"
PORT="22"
PKEY=""
PASS=""

show_banner

while [[ $# -gt 0 ]]; do
  case $1 in
    --cleanup)
      CLEANUP_MODE="cleanup"
      shift
      ;;
    --full-cleanup)
      CLEANUP_MODE="full-cleanup"
      shift
      ;;
    --no-cleanup)
      CLEANUP_MODE="no-cleanup"
      shift
      ;;
    --dry-run)
      DRY_RUN=1
      shift
      ;;
    --use-inventory)
      USE_INVENTORY=1
      shift
      ;;
    -h|--help)
      show_help
      exit 0
      ;;
    -H|--host)
      HOST="$2"
      shift 2
      ;;
    -u|--user)
      USER_NAME="$2"
      shift 2
      ;;
    -p|--port)
      PORT="$2"
      shift 2
      ;;
    --pkey)
      PKEY="$2"
      shift 2
      ;;
    --pass)
      PASS="$2"
      shift 2
      ;;
    --clients-dir)
      CLIENTS_DIR="$2"
      shift 2
      ;;
    *)
      echo "Unknown flag: $1" >&2
      echo "Use '--help' to see available options."
      exit 1
      ;;
  esac
done

echo "Cleanup mode: $CLEANUP_MODE"

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"

# Mode-specific validation
if [[ "$USE_INVENTORY" -eq 1 ]]; then
  echo "Mode: Using inventory.yml for parameters"
  
  # Validate inventory.yml
  if [[ "$DRY_RUN" -eq 1 ]]; then
    echo "[dry-run] Would validate inventory.yml has all required fields"
  else
    if ! validate_inventory; then
      exit 1
    fi
    echo "[OK] inventory.yml validation passed (all fields present, pkey and pass are mutually exclusive)"
  fi
  
  # Warn if CLI params provided
  if [[ -n "$HOST" || -n "$PKEY" || -n "$PASS" || -n "$PORT" || -n "$USER_NAME" ]]; then
    echo "Warning: --use-inventory specified; ignoring CLI connection/auth parameters" >&2
    # Clear to avoid conflicts later 
    HOST=""
    PKEY=""
    PASS=""
    PORT=""
    USER_NAME=""
  fi

  # Parameters verified at this point, either PASS or PKEY exists, the other must be empty
  HOST=$(get_inventory_value "ansible_host")
  PKEY=$(get_inventory_value "ansible_ssh_private_key_file")
  PASS=$(get_inventory_value "ansible_ssh_pass")
  PORT=$(get_inventory_value "ansible_port")
  USER_NAME=$(get_inventory_value "ansible_user")
else
  echo "Mode: Using CLI parameters"
  
  # Validate required CLI arguments
  if [[ -z "$HOST" ]]; then
    echo "Error: --host is required in CLI mode." >&2
    echo "Use '--help' to see usage or '--use-inventory' to use inventory.yml."
    exit 1
  fi

  if [[ -n "$PKEY" && -n "$PASS" ]]; then
    echo "Error: --pkey and --pass are mutually exclusive; use only one." >&2
    exit 1
  fi

  # If neither provided, prompt for password (hidden)
  if [[ -z "$PKEY" && -z "$PASS" ]]; then
    if [[ "$DRY_RUN" -eq 1 ]]; then
      echo "[dry-run] No --pkey or --pass provided. In a real run, you would be prompted for a hidden SSH password."
    else
      read -s -p "SSH password: " PASS
      echo
    fi
  fi
fi

if [[ "$DRY_RUN" -eq 1 ]]; then
  WORK_DIR="/tmp/provision-vpn-DRYRUN"
  echo "[dry-run] Would create workspace under: $WORK_DIR"
else
  WORK_DIR="$(mktemp -d)"
  echo "Workspace: $WORK_DIR"
fi

# Marker file to record what we installed
MARKER="$WORK_DIR/.installed_by_provision"
if [[ "$DRY_RUN" -eq 1 ]]; then
  echo "[dry-run] Would create marker file: $MARKER"
else
  touch "$MARKER"
fi

install_if_missing() {
  local pkg="$1"

  if [[ "$DRY_RUN" -eq 1 ]]; then
    echo "[dry-run] Would check and possibly install package: $pkg"
    return
  fi

  if ! dpkg -s "$pkg" >/dev/null 2>&1; then
    echo "Installing $pkg..."
    sudo apt-get update -y
    sudo apt-get install -y "$pkg"
    echo "$pkg" >> "$MARKER"
  else
    echo "$pkg already present, not recording for removal."
  fi
}

echo "Checking prerequisites..."
install_if_missing "python3"
install_if_missing "python3-venv"
install_if_missing "ansible"
install_if_missing "sshpass"

# Copy project (excluding junk/venv)
if [[ "$DRY_RUN" -eq 1 ]]; then
  echo "[dry-run] Would rsync project from: $SCRIPT_DIR/ to: $WORK_DIR/"
  echo "[dry-run] Would change directory to: $WORK_DIR"
else
  rsync -a \
    --exclude='.venv/' \
    --exclude='.ansible/' \
    --exclude='__pycache__/' \
    --exclude='.git/' \
    --exclude='downloaded-configs/' \
    "$SCRIPT_DIR/" "$WORK_DIR/"

  cd "$WORK_DIR"
fi

# Prepare inventory based on mode
if [[ "$USE_INVENTORY" -eq 1 ]]; then
  # Inventory mode: use as-is, no backup needed
  if [[ "$DRY_RUN" -eq 1 ]]; then
    echo "[dry-run] Would use inventory.yml as-is (no modifications or backup)"
  else
    echo "Using existing inventory.yml values..."
  fi
else
  # CLI mode: fill inventory template with CLI values
  if [[ "$DRY_RUN" -eq 1 ]]; then
    echo "[dry-run] Preparing to run Ansible with provided parameters..."
    echo "[dry-run] Would backup inventory.yml:"
    echo "from $SCRIPT_DIR/inventory.yml to $WORK_DIR/inventory.yml.backup"
    echo "[dry-run] Would fill inventory.yml with:"
    echo "  ansible_host: $HOST"
    echo "  ansible_user: $USER_NAME"
    echo "  ansible_port: $PORT"
    [[ -n "$PKEY" ]] && echo "  ansible_ssh_private_key_file: $PKEY"
    [[ -n "$PASS" ]] && echo "  ansible_ssh_pass: (hidden)"
  else
    echo "Preparing to run Ansible with provided parameters..."

    # Backup original inventory.yml (to revert afterwards)
    cp "$SCRIPT_DIR/inventory.yml" "$WORK_DIR/inventory.yml.backup"

    # Fill host connection details
    sed -i "s|ansible_host:.*|ansible_host: $HOST|" "$WORK_DIR/inventory.yml"
    sed -i "s|ansible_user:.*|ansible_user: $USER_NAME|" "$WORK_DIR/inventory.yml"
    sed -i "s|ansible_port:.*|ansible_port: $PORT|" "$WORK_DIR/inventory.yml"
    
    # Fill auth (ensure mutual exclusion for private key file and password parameters)
    if [[ -n "$PKEY" ]]; then
      sed -i "s|ansible_ssh_private_key_file:.*|ansible_ssh_private_key_file: $PKEY|" "$WORK_DIR/inventory.yml"
      sed -i '/ansible_ssh_pass:/d' "$WORK_DIR/inventory.yml"  # Remove password line
    elif [[ -n "$PASS" ]]; then
      sed -i "s|ansible_ssh_pass:.*|ansible_ssh_pass: $PASS|" "$WORK_DIR/inventory.yml"
      sed -i '/ansible_ssh_private_key_file:/d' "$WORK_DIR/inventory.yml"  # Remove key line
    fi
  fi
fi


export ANSIBLE_HOST_KEY_CHECKING=False

# Running the playbook itself
if [[ "$DRY_RUN" -eq 1 ]]; then
  echo "[dry-run] Would run: ansible-playbook -i inventory.yml deploy.yml -e \"num_clients=3 reality_camouflage_domain=www.microsoft.com\""
else
  ansible-playbook -i "$WORK_DIR/inventory.yml" deploy.yml \
    -e "num_clients=${NUM_CLIENTS:-3} reality_camouflage_domain=${DOMAIN:-www.microsoft.com}"
fi

# Decide where to download generated client configs
if [[ -n "$CLIENTS_DIR" ]]; then
  TARGET_DIR="$CLIENTS_DIR"
else
  TARGET_DIR="$SCRIPT_DIR/downloaded-clients"
fi

if [[ "$DRY_RUN" -eq 1 ]]; then
  echo "[dry-run] Would create target directory: $TARGET_DIR"
  echo "[dry-run] Would fetch /root/vpn-configs/*.json from VPS via scp"
else
  mkdir -p "$TARGET_DIR"

  # Fetch client configs from VPS using validated auth method
  echo "Fetching client configs from VPS..."
  if [[ -n "$PKEY" ]]; then
    # Key-based authentication
    scp -i "$PKEY" -P "$PORT" -o StrictHostKeyChecking=no \
      "$USER_NAME@$HOST:/root/vpn-configs/*.json" "$TARGET_DIR/" 2>/dev/null \
      && echo "Client configs saved to: $TARGET_DIR" \
      || echo "Warning: scp failed. Check VPS connection or auth."
  elif [[ -n "$PASS" ]]; then
    # Password-based authentication
    sshpass -p "$PASS" scp -P "$PORT" -o StrictHostKeyChecking=no \
      "$USER_NAME@$HOST:/root/vpn-configs/*.json" "$TARGET_DIR/" 2>/dev/null \
      && echo "Client configs saved to: $TARGET_DIR" \
      || echo "Warning: scp failed. Check VPS connection or auth."
  fi
fi

# Cleanup logic

# Restore inventory.yml from backup (CLI mode only)
if [[ "$CLEANUP_MODE" != "no-cleanup" && "$USE_INVENTORY" -eq 0 ]]; then
  # Only restore in CLI mode (inventory mode never created backup)
  if [[ "$DRY_RUN" -eq 1 ]]; then
    echo "[dry-run] Would restore inventory.yml from inventory.yml.backup file"
  else
    if [[ -f "$WORK_DIR/inventory.yml.backup" ]]; then
      cp "$WORK_DIR/inventory.yml.backup" "$SCRIPT_DIR/inventory.yml"
      echo "[OK] Restored inventory.yml to template state"
      rm -f "$WORK_DIR/inventory.yml.backup"
    fi
  fi
elif [[ "$CLEANUP_MODE" == "no-cleanup" ]]; then
  if [[ "$DRY_RUN" -eq 1 ]]; then
    echo "[dry-run] [no-cleanup] Would leave workspace as is"
  else
    if [[ "$USE_INVENTORY" -eq 0 ]]; then
      echo "[no-cleanup] Keeping inventory.yml.backup for reference"
    fi
  fi
fi

case "$CLEANUP_MODE" in
  cleanup)
    if [[ "$DRY_RUN" -eq 1 ]]; then
      echo "[dry-run] Would remove temp workspace: $WORK_DIR"
    else
      echo "Cleanup: removing temp workspace..."
      rm -rf "$WORK_DIR"
    fi
    ;;
  full-cleanup)
    if [[ "$DRY_RUN" -eq 1 ]]; then
      echo "[dry-run] Would remove temp workspace and any packages listed in: $MARKER"
    else
      echo "Full cleanup: removing temp workspace and packages we installed..."
      if [[ -s "$MARKER" ]]; then
        mapfile -t pkgs < <(sort -u "$MARKER")
        echo "Removing packages: ${pkgs[*]}"
        sudo apt-get remove -y "${pkgs[@]}" || true
        sudo apt-get autoremove -y || true
      else
        echo "No packages recorded as installed by script; nothing to remove."
      fi
      echo "Cleanup: removing temp workspace..."
      rm -rf "$WORK_DIR"
    fi
    ;;
  no-cleanup)
    if [[ "$DRY_RUN" -eq 1 ]]; then
      echo "[dry-run] Would leave workspace at: $WORK_DIR"
    else
      echo "No cleanup: workspace left at $WORK_DIR"
    fi
    ;;
esac

if [[ "$DRY_RUN" -eq 1 ]]; then
  echo "[dry-run] Done (no changes applied)."
else
  echo "Done."
fi
