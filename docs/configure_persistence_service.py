import sys
import os
import platform
import subprocess
from pathlib import Path

def install_linux_systemd_service(binary_path: Path, config_path: Path) -> None:
    """Compiles and registers a native systemd background daemon service for persistent Linux operation."""
    if os.getuid() != 0:
        print("Installation Fault: Root superuser administrative clearance required to install systemd services.", file=sys.stderr)
        sys.exit(1)
        
    print("[INSTALLER] Configuring Linux systemd service persistence matrix...")
    
    service_unit_content = f"""[Unit]
Description=UNIVAC-IX Tactical Mainframe Emergency Recovery Server
After=network.target

[Service]
Type=simple
WorkingDirectory={config_path.parent}
ExecStart={binary_path} listen-server --config {config_path} --purge-timeout 5.0
Restart=always
RestartSec=3
StandardOutput=syslog
StandardError=syslog
SyslogIdentifier=univac_core

[Install]
WantedBy=multi-user.target
"""
    
    unit_file_path = Path("/etc/systemd/system/univac_core.service")
    
    try:
        with open(unit_file_path, "w", encoding="utf-8") as f:
            f.write(service_unit_content)
            
        subprocess.run(["systemctl", "daemon-reload"], check=True)
        subprocess.run(["systemctl", "enable", "univac_core.service"], check=True)
        subprocess.run(["systemctl", "start", "univac_core.service"], check=True)
        print("[SUCCESS] UNIVAC-IX Server is mounted and running. Automatic system boot startup active.")
    except Exception as e:
        print(f"Installation Fault: Failed to write systemd configurations: {e}", file=sys.stderr)
        sys.exit(2)

def install_windows_service_manager(binary_path: Path, config_path: Path) -> None:
    """Registers a persistent background service running directly inside the Windows Service Control manager."""
    print("[INSTALLER] Verifying Windows administrative execution permissions...")
    
    try:
        # Check for elevated token privileges by attempting to execute a restricted command channel
        subprocess.check_output("net session", stderr=subprocess.STDOUT, shell=True)
    except subprocess.CalledProcessError:
        print("Installation Fault: Elevated Administrator command prompt privileges required to mount Windows services.", file=sys.stderr)
        sys.exit(1)
        
    print("[INSTALLER] Configuring Windows Service Control manager persistence hooks...")
    
    service_command = f'sc create univac_core binPath= "{binary_path} listen-server --config {config_path}" start= auto'
    
    try:
        subprocess.run(service_command, shell=True, check=True)
        subprocess.run("sc start univac_core", shell=True, check=True)
        print("[SUCCESS] UNIVAC-IX Windows Service configured. Automatic system boot startup active.")
    except Exception as e:
        print(f"Installation Fault: Windows Service Control configuration failed: {e}", file=sys.stderr)
        sys.exit(2)

def execute_cross_platform_installation() -> None:
    """Autonomous platform evaluation matrix detects OS target constraints and launches matching service setups."""
    current_os = platform.system().upper()
    
    # Establish standard baseline paths for compiled terminal deployment binaries
    target_binary = Path("dist/main")
    if current_os == "WINDOWS":
        target_binary = Path("dist/main.exe")
        
    target_config = Path("config.yaml").absolute()
    
    if not target_config.exists():
        print(f"Configuration Fault: Topology configuration profile missing at path: '{target_config}'", file=sys.stderr)
        sys.exit(1)
        
    if current_os == "LINUX":
        install_linux_systemd_service(target_binary.absolute(), target_config)
        return
        
    if current_os == "WINDOWS":
        install_windows_service_manager(target_binary.absolute(), target_config)
        return
        
    print(f"Installation Fault: Target platform operating system environment '{current_os}' is completely unsupported.", file=sys.stderr)
    sys.exit(3)

if __name__ == "__main__":
    execute_cross_platform_installation()
