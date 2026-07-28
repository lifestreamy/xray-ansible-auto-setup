<#
.SYNOPSIS
Provision and configure an XRAY+Amnezia VPN server via Linux/WSL + Ansible.

.DESCRIPTION
This script is a Windows/PowerShell wrapper around provision-vpn.sh.
It forwards connection parameters and cleanup options into WSL, runs
the Ansible-based provisioning, and ensures generated client configs
are copied to a Windows-accessible directory.

This script supports two parameter modes:
  - CLI mode (default): Pass connection parameters via flags
  - Inventory mode: Use pre-filled inventory.yml file (specify -UseInventory)

This project does not require Windows: on a native Linux environment you can
run provision-vpn.sh directly. On Windows, this PowerShell script provides
the same functionality by running the bash script through WSL.

For detailed usage, parameters, and examples, run:
  Get-Help .\Provision-VPN.ps1 -Full

.NOTES
If you want to be interactively prompted for an SSH password with
hidden input, specify neither -Pass nor -PKey.

+--------------------------------------------------------------+
| Release: v2025-12-13                                         |
| Author:  Tim Korelov                                         |
| Contact: https://github.com/lifestreamy                      |
| License: MIT                                                 |
+--------------------------------------------------------------+

.PARAMETER UseInventory
Use values from inventory.yml instead of CLI parameters.
When specified, connection/auth parameters are ignored.

.PARAMETER HostName
VPS IP or hostname to connect to (required in CLI mode).

.PARAMETER User
SSH user name. Defaults to 'root'.

.PARAMETER Port
SSH port. Defaults to 22.

.PARAMETER PKey
Path to the SSH private key for key-based authentication.
Mutually exclusive with -Pass.

.PARAMETER Pass
SSH password for password-based authentication (plain text).
If omitted and -PKey is not provided, you will be prompted in
interactive mode with hidden input.

.PARAMETER ClientsDir
Directory on Windows where generated client configs will be stored.
If omitted, a 'downloaded-clients' directory is created next to this script.

.PARAMETER CleanupMode
Controls cleanup behavior in the underlying bash script.
Allowed values:
  Default  - remove only the temporary workspace (maps to --cleanup)
  Full     - remove workspace AND any packages installed by the bash script
  None     - keep the temporary workspace for debugging

Defaults to Default.

.PARAMETER DryRun
Developer mode. Validates parameters and shows the WSL commands that
would be executed, but does not invoke WSL, the bash script, or Ansible.

.PARAMETER LogLevel
Controls output verbosity. Allowed values:
  None     - suppress all output except fatal errors
  Default  - show banner, essential progress messages
  Verbose  - show everything in Default plus detailed tracing

Defaults to Default.

.EXAMPLE
.\Provision-VPN.ps1 -HostName 1.2.3.4 -PKey C:\Keys\id_rsa

.EXAMPLE
.\Provision-VPN.ps1 -HostName vps.example.com -User root -Pass 'secret' `
    -ClientsDir C:\Users\Tim\Desktop\vpn-clients

.EXAMPLE
.\Provision-VPN.ps1 -HostName 1.2.3.4 -User root
# prompts for SSH password interactively with hidden input

.EXAMPLE
.\Provision-VPN.ps1 -UseInventory -CleanupMode Full
# Uses pre-filled inventory.yml, removes packages after run

.EXAMPLE
.\Provision-VPN.ps1 -HostName 1.2.3.4 -User root -DryRun -LogLevel Verbose
# dry run with full verbose output, does not execute anything
#>

[CmdletBinding()]
param(
    # Inventory mode flag
    [Parameter()]
    [switch]$UseInventory,

    # Common parameters
    [Parameter()]
    [Alias('H')]
    [string]$HostName,

    [Parameter()]
    [Alias('u')]
    [string]$User = 'root',

    [Parameter()]
    [Alias('p')]
    [int]$Port = 22,

    [Parameter()]
    [string]$ClientsDir,

    [Parameter()]
    [ValidateSet('Default', 'Full', 'None')]
    [string]$CleanupMode = 'Default',

    # Auth parameters (mutually exclusive, validated later)
    [Parameter()]
    [string]$PKey,

    [Parameter()]
    [string]$Pass,

    # Developer / dry-run mode
    [Parameter()]
    [switch]$DryRun,

    # LogLevel (independent of DryRun)
    [Parameter()]
    [ValidateSet('None', 'Default', 'Verbose')]
    [string]$LogLevel = 'Default'
)

# === Configuration for runtime banner ===
$boxWidth = 58  # internal box width
$title = "Xray VPN Provisioning Wrapper (Clash Verge, FlClash, Amnezia)"
$version = 'v2025-12-13' # YYYY-MM-DD
$license = 'MIT'
$author = 'Tim Korelov'
$contact = 'https://github.com/lifestreamy'

# === Logging helpers ===
function Write-LogDefault([string]$Message) {
    if ($LogLevel -in @('Default', 'Verbose')) {
        Write-Host $Message
    }
}

function Write-LogVerbose([string]$Message) {
    if ($LogLevel -eq 'Verbose') {
        Write-Host $Message -ForegroundColor DarkGray
    }
}

function Convert-ToWslPath {
    param([string]$Path)
    $Path = $Path.Trim('"').TrimEnd('\','/') -replace '[/\\]','/'
    if ($Path -match '^([A-Za-z]):(.*)') {
        return "/mnt/$($matches[1].ToLowerInvariant())$($matches[2])"
    }
    return $Path
}

# === The banner ===
Write-LogDefault "+--------------------------------------------------------------+"
Write-LogDefault ("| {0,-58} |" -f $title.PadLeft(($boxWidth + $title.Length) / 2).PadRight($boxWidth))
Write-LogDefault ("| {0,-58} |" -f "")  # blank separator line
Write-LogDefault ("| Release: {0,-49} |" -f $version)
Write-LogDefault ("| Author:  {0,-49} |" -f $author)
Write-LogDefault ("| Contact: {0,-49} |" -f $contact)
Write-LogDefault ("| License: {0,-49} |" -f $license)
Write-LogDefault "+--------------------------------------------------------------+"
Write-LogDefault ""
Write-LogDefault "Tip: Run 'Get-Help .\$(Split-Path -Leaf $MyInvocation.MyCommand.Path) -Full' for full documentation."
Write-LogDefault ""

if ($DryRun) {
    Write-LogDefault "[DryRun] Active: will validate parameters and show commands, but not execute them." -ForegroundColor Yellow
    Write-LogVerbose "[DryRun] Path conversions use best-effort mock; real runs use 'wsl wslpath -a'."
}

# === Mode detection ===
if ($UseInventory) {
    Write-LogDefault "Mode: Using inventory.yml for parameters"
    Write-LogVerbose "Inventory mode active; CLI connection/auth parameters will be ignored."
    
    # Warn if CLI params provided
    if ($HostName -or $PKey -or $Pass) {
        Write-Host "Warning: -UseInventory specified; ignoring CLI connection/auth parameters." -ForegroundColor Yellow
    }
}
else {
    Write-LogDefault "Mode: Using CLI parameters"
    Write-LogVerbose "Inputs: Host=$HostName User=$User Port=$Port CleanupMode=$CleanupMode LogLevel=$LogLevel"
    
    # Validate Host is required in CLI mode
    if (-not $HostName) {
        throw "Parameter -HostName is required in CLI mode. Use -UseInventory to use inventory.yml instead."
    }
}

# === Validate mutual exclusivity and presence of auth (CLI mode only) ===
if (-not $UseInventory) {
    if ($PKey -and $Pass) {
        throw "Parameters -PKey and -Pass are mutually exclusive; use only one."
    }

    Write-LogVerbose "Auth: PKeyProvided=$([bool]$PKey) PassProvided=$([bool]$Pass)"

    if (-not $DryRun) {
        if (-not $PKey -and -not $Pass) {
            # Prompt for password interactively with hidden input
            $secure = Read-Host "Enter SSH password" -AsSecureString
            $Pass = [System.Net.NetworkCredential]::new('', $secure).Password
            Write-LogVerbose "Password obtained via interactive prompt."
        }
    }
    else {
        if (-not $PKey -and -not $Pass) {
            Write-LogDefault "[DryRun] No -PKey or -Pass provided. In a real run, script would prompt for hidden SSH password." -ForegroundColor Yellow
        }
    }
}

# === Map CleanupMode -> bash flags ===
switch ($CleanupMode) {
    'Default' { $cleanupFlag = '--cleanup' }
    'Full' { $cleanupFlag = '--full-cleanup' }
    'None' { $cleanupFlag = '--no-cleanup' }
    default { throw "Unknown CleanupMode '$CleanupMode'." }
}

Write-LogVerbose "CleanupMode '$CleanupMode' mapped to bash flag '$cleanupFlag'."

# === Resolve script directory and provision-vpn.sh ===
$scriptDir = Split-Path -Parent $MyInvocation.MyCommand.Path
$bashScriptPath = Join-Path $scriptDir 'provision-vpn.sh'

Write-LogVerbose "Script directory (Windows): $scriptDir"
Write-LogVerbose "Bash script path (Windows): $bashScriptPath"

# === Convert paths to WSL style ===
$wslScriptPath = Convert-ToWslPath $bashScriptPath


Write-LogVerbose "Bash script path (WSL): $wslScriptPath"

# === Build WSL arguments ===
$wslArgs = @($cleanupFlag)

# Add inventory mode flag if specified
if ($UseInventory) {
    $wslArgs += '--use-inventory'
}
else {
    # CLI mode: add connection parameters
    $wslArgs += @(
        '--host', $HostName
        '--user', $User
        '--port', $Port
    )
}

# === Determine output directory for Amnezia VPN client configs (.json) ===
if ($ClientsDir) {
    $wslClientsDir = Convert-ToWslPath $ClientsDir
    $wslArgs += @('--clients-dir', $wslClientsDir)
    Write-LogVerbose "ClientsDir (Windows): $ClientsDir"
    Write-LogVerbose "ClientsDir (WSL): $wslClientsDir"
}
else {
    # Default: directory next to the script on Windows, mirrored into WSL path
    $defaultClientsDir = Join-Path $scriptDir 'downloaded-clients'
    if (-not (Test-Path $defaultClientsDir)) {
        New-Item -ItemType Directory -Path $defaultClientsDir | Out-Null
        Write-LogVerbose "Created default clients directory: $defaultClientsDir"
    }

    $wslDefaultClientsDir = Convert-ToWslPath $defaultClientsDir
    $wslArgs += @('--clients-dir', $wslDefaultClientsDir)
    Write-LogVerbose "Using default ClientsDir (Windows): $defaultClientsDir"
    Write-LogVerbose "Using default ClientsDir (WSL): $wslDefaultClientsDir"
}

# === Configure authentication method (CLI mode only) ===
if (-not $UseInventory) {
    if ($PKey) {
        $wslPKey = Convert-ToWslPath $PKey
        $wslArgs += @('--pkey', $wslPKey)
        Write-LogVerbose "PKey path (Windows): $PKey"
        Write-LogVerbose "PKey path (WSL): $wslPKey"
    }
    elseif ($Pass) {
        $wslArgs += @('--pass', $Pass)
        Write-LogVerbose "Using password authentication (password not logged)."
    }
}

Write-LogVerbose ("Final WSL args: " + ($wslArgs -join ' '))

if ($DryRun) {
    $wslArgs += '--dry-run'
}

# === DryRun output ===
if ($DryRun) {
    Write-LogDefault ""
    Write-LogDefault "[DryRun] Executing bash script in dry-run mode (safe, no changes made):" -ForegroundColor Yellow
    Write-LogDefault "  wsl chmod +x $wslScriptPath" -ForegroundColor Yellow
    Write-LogDefault "  wsl bash $wslScriptPath $($wslArgs -join ' ')" -ForegroundColor Yellow
    Write-LogVerbose ""
    Write-LogVerbose ("WSL args as array: " + ($wslArgs | ForEach-Object { "'$_'" }) -join ", ")
    Write-LogDefault ""  # blank line before bash output
}

# === Executing the bash script ===
Write-LogVerbose "Ensuring bash script is executable..."
wsl chmod +x $wslScriptPath

Write-LogDefault "Running Ansible provisioning via WSL..."
wsl bash $wslScriptPath @wslArgs

Write-LogDefault "Provisioning complete."

