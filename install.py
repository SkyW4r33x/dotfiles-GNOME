#!/usr/bin/python3
# -*- coding: utf-8 -*-
#
# Author: Jordan aka SkyW4r33x
# Description: GNOME dotfiles installer
# Version: 1.2.0

import os
import json
import subprocess
import urllib.request
import zipfile
import tempfile
import sys
import shutil
import time
from pathlib import Path
import logging
import hashlib

# ------------------------------- Kali Style Class --------------------------- #

class KaliStyle:
    RESET = '\033[0m'
    BOLD = '\033[1m'
    BLUE = '\033[38;2;39;127;255m'  
    TURQUOISE = '\033[38;2;71;212;185m' 
    ORANGE = '\033[38;2;255;138;24m' 
    WHITE = '\033[37m'
    GREY = '\033[38;5;242m'
    RED = '\033[38;2;220;20;60m'  
    GREEN = '\033[38;2;71;212;185m' 
    YELLOW = '\033[0;33m'
    MAGENTA = '\033[0;35m'
    CYAN = '\033[0;36m'
    SUDO_COLOR = '\033[38;2;94;189;171m' 
    APT_COLOR = '\033[38;2;73;174;230m' 
    SUCCESS = f"   {TURQUOISE}{BOLD}✔{RESET}"
    ERROR = f"   {RED}{BOLD}✘{RESET}"
    INFO = f"{BLUE}{BOLD}[i]{RESET}"
    WARNING = f"{YELLOW}{BOLD}[!]{RESET}"

# ------------------------------- Combined Installer Class --------------------------- #

class CombinedInstaller:

    def __init__(self):
        if os.getuid() == 0:
            print(f"{KaliStyle.ERROR} Do not run this script with sudo or as root. Use a normal user like 'kali'.")
            sys.exit(1)
        
        original_user = os.environ.get('SUDO_USER', os.environ.get('USER') or Path.home().name)
        self.home_dir = os.path.expanduser(f'~{original_user}')
        self.current_user = original_user
        self.extensions_dir = os.path.join(self.home_dir, '.local/share/gnome-shell/extensions')
        self.temp_dir = '/tmp/gnome-extensions-install'
        self.config_dir = os.path.join(self.home_dir, '.config')
        self.script_dir = os.path.dirname(os.path.realpath(__file__))
        self.pictures_dir = os.path.join(self.home_dir, 'Pictures')
        self.actions_taken = []  
        self.needs_gdm_restart = False
        self.dash_to_panel_installed = False
        
        log_path = os.path.join(self.script_dir, 'install.log')
        if os.path.exists(log_path) and not os.access(log_path, os.W_OK):
            print(f"{KaliStyle.WARNING} Fixing permissions on {log_path}...")
            subprocess.run(['sudo', 'rm', '-f', log_path], check=True)
        logging.basicConfig(filename=log_path, level=logging.INFO, 
                            format='%(asctime)s - %(levelname)s - %(message)s')

    def show_banner(self):
        print(f"{KaliStyle.BLUE}{KaliStyle.BOLD}")
        print("""
██████╗  ██████╗ ████████╗███████╗██╗██╗     ███████╗███████╗
██╔══██╗██╔═══██╗╚══██╔══╝██╔════╝██║██║     ██╔════╝██╔════╝
██║  ██║██║   ██║   ██║   █████╗  ██║██║     █████╗  ███████╗
██║  ██║██║   ██║   ██║   ██╔══╝  ██║██║     ██╔══╝  ╚════██║
██████╔╝╚██████╔╝   ██║   ██║     ██║███████╗███████╗███████║
╚═════╝  ╚═════╝    ╚═╝   ╚═╝     ╚═╝╚══════╝╚══════╝╚══════╝""")
        print(f"{KaliStyle.WHITE}\t\t [ Dotfiles GNOME - v.1.2.0 ]{KaliStyle.RESET}")
        print(f"{KaliStyle.GREY}\t\t  [ Created by SkyW4r33x ]{KaliStyle.RESET}\n")

    def run_command(self, command, shell=False, sudo=False, quiet=True):
        try:
            if sudo and not shell:
                command = ['sudo'] + command
            result = subprocess.run(
                command,
                shell=shell,
                check=True,
                stdout=subprocess.PIPE if quiet else None,
                stderr=subprocess.PIPE if quiet else None,
                text=True
            )
            return True
        except subprocess.CalledProcessError as e:
            if not quiet:
                print(f"{KaliStyle.ERROR} Error executing command: {command}")
                print(f"Output: {e.stdout}")
                print(f"Error: {e.stderr}")
            logging.error(f"Error executing command: {command} - {e}\nOutput: {e.stdout}\nError: {e.stderr}")
            return False
        except PermissionError:
            print(f"{KaliStyle.ERROR} Insufficient permissions to execute: {command}")
            return False

    def check_command(self, command):
        try:
            subprocess.run([command, "--version"], stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
            return True
        except FileNotFoundError:
            return False

    def get_gnome_version(self):
        try:
            result = subprocess.run(['gnome-shell', '--version'], capture_output=True, text=True)
            version_str = result.stdout.strip().split()[-1]  
            major = int(version_str.split('.')[0])
            return major
        except Exception as e:
            logging.error(f"Error getting GNOME version: {str(e)}")
            return None

    def check_os(self):
        if not os.path.exists('/etc/debian_version'):
            print(f"{KaliStyle.ERROR} This script is designed for Debian/Kali based systems")
            return False
        return True

    def check_sudo_privileges(self):
        try:
            result = subprocess.run(['sudo', '-n', 'true'], stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
            if result.returncode == 0:
                return True
            else:
                print(f"{KaliStyle.WARNING} This script needs to execute commands with sudo.")
                return True
        except Exception as e:
            print(f"{KaliStyle.ERROR} Could not verify sudo privileges: {str(e)}")
            return False

    def check_required_files(self):
        required_files = [
            "dash-to-panel-settings.dconf", 
            "top-bar-organizer.dconf",
            "top-bar-organizer-dash-to-dock.dconf",
            "JetBrainsMono.zip",
            "extractPorts.py", 
            ".zshrc", 
            "terminator", 
            "kitty", 
            "sudo-plugin",
            "wallpaper/kali-simple-3840x2160.png", 
            "wallpaper/browser-home-page-banner.jpg",
            "wallpaper/grub-16x9.png",
            "wallpaper/grub-4x3.png",
            "gnome-extensions"
        ]
        missing = [f for f in required_files if not os.path.exists(os.path.join(self.script_dir, f))]
        if missing:
            print(f"{KaliStyle.ERROR} Missing required files: {', '.join(missing)}")
            print(f"{KaliStyle.INFO} Make sure they are in {self.script_dir}")
            return False
        return True

    def install_custom_extensions(self):
        print(f"\n{KaliStyle.INFO} Installing custom extensions...")
        
        source_extensions_dir = os.path.join(self.script_dir, "gnome-extensions")
        if not os.path.exists(source_extensions_dir):
            print(f"{KaliStyle.ERROR} gnome-extensions folder not found in {source_extensions_dir}")
            return False
        
        custom_extensions = [
            "top-panel-ethernet@kali.org",
            "top-panel-target@kali.org", 
            "top-panel-vpnip@kali.org",
            "top-bar-organizer@julian.gse.jsts.xyz"
        ]
        
        os.makedirs(self.extensions_dir, exist_ok=True)
        
        success_count = 0
        for extension in custom_extensions:
            source_path = os.path.join(source_extensions_dir, extension)
            dest_path = os.path.join(self.extensions_dir, extension)
            
            if not os.path.exists(source_path):
                print(f"{KaliStyle.ERROR} Extension {extension} not found in {source_path}")
                continue
                
            if os.path.exists(dest_path):
                print(f"{KaliStyle.WARNING} Extension {extension} already exists, skipping copy.")
                success_count += 1
                continue
            
            try:
                shutil.copytree(source_path, dest_path)
                self.actions_taken.append({'type': 'dir_copy', 'dest': dest_path})
                print(f"{KaliStyle.SUCCESS} Extension {extension} installed")
                success_count += 1
                
            except Exception as e:
                print(f"{KaliStyle.ERROR} Error copying {extension}: {str(e)}")
                logging.error(f"Error copying extension {extension}: {str(e)}")
        
        if success_count == len(custom_extensions):
            print(f"{KaliStyle.SUCCESS} All custom extensions installed correctly")
            return True
        elif success_count > 0:
            print(f"{KaliStyle.WARNING} {success_count}/{len(custom_extensions)} extensions installed")
            return True
        else:
            print(f"{KaliStyle.ERROR} Could not install any custom extension")
            return False

    def check_graphical_environment(self):
        if not os.environ.get('DISPLAY'):
            print(f"{KaliStyle.ERROR} No graphical environment detected.")
            return False
        return True

    def check_gnome_requirements(self):
        print(f"{KaliStyle.INFO} Checking requirements for GNOME extensions...")
        requirements = {
            'git': {'pkg': 'git', 'desc': 'Git'},
            'make': {'pkg': 'make', 'desc': 'Make'},
            'msgfmt': {'pkg': 'gettext', 'desc': 'Gettext'},
            'gnome-extensions': {'pkg': 'gnome-shell', 'desc': 'GNOME Extensions CLI'},
            'dconf': {'pkg': 'dconf-cli', 'desc': 'Dconf CLI'}
        }
        
        missing_pkgs = []
        for command, info in requirements.items():
            if not self.check_command(command):
                missing_pkgs.append(info['pkg'])
                print(f"{KaliStyle.ERROR} Missing {command} ({info['desc']})")
            else:
                print(f"{KaliStyle.SUCCESS} Found {command}")

        gnome_major = self.get_gnome_version()
        if gnome_major is None or gnome_major < 42 or gnome_major > 48:
            print(f"{KaliStyle.ERROR} Incompatible GNOME version or not detected (detected: {gnome_major}). Extensions may fail.")
            missing_pkgs.append('gnome-shell')  

        if missing_pkgs:
            print(f"\n{KaliStyle.INFO} Install manually:\n   {KaliStyle.BLUE}→{KaliStyle.RESET} {KaliStyle.SUDO_COLOR}sudo {KaliStyle.APT_COLOR}apt {KaliStyle.RESET}install {' '.join(missing_pkgs)}{KaliStyle.SUDO_COLOR} -y{KaliStyle.RESET}")
            return False
        print(f"{KaliStyle.SUCCESS} Requirements verified")
        return True

    def install_additional_packages(self):
        print(f"\n{KaliStyle.INFO} Installing tools")
        self.packages = [
            'xclip', 'zsh', 'lsd', 'bat', 'terminator', 'kitty',
            'keepassxc', 'gnome-shell-extensions', 'flameshot'
        ]
        self.max_length = max(len(pkg) for pkg in self.packages)
        self.state_length = 12
        self.states = {pkg: f"{KaliStyle.GREY}Pending{KaliStyle.RESET}" for pkg in self.packages}
        
        def print_status(first_run=False):
            if not first_run:
                print(f"\033[{len(self.packages) + 1}A", end="")
            
            print(f"{KaliStyle.INFO} Installing packages:")
            for pkg, state in self.states.items():
                print(f"\033[K", end="")
                print(f"  {KaliStyle.YELLOW}•{KaliStyle.RESET} {pkg:<{self.max_length}} {state:<{self.state_length}}")
            sys.stdout.flush()

        try:
            print(f"{KaliStyle.INFO} Updating repositories...")
            if not self.run_command(['apt', 'update'], sudo=True, quiet=True):
                print(f"{KaliStyle.ERROR} Error updating repositories")
                return False
            print(f"{KaliStyle.SUCCESS} Repositories updated")

            print_status(first_run=True)
            failed_packages = []
            for pkg in self.packages:
                check_installed = subprocess.run(['dpkg-query', '-s', pkg], stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
                if check_installed.returncode == 0:
                    self.states[pkg] = f"{KaliStyle.GREEN}Already installed{KaliStyle.RESET}"
                    print_status()
                    continue
                
                self.states[pkg] = f"{KaliStyle.YELLOW}Installing...{KaliStyle.RESET}"
                print_status()
                try:
                    if self.run_command(['apt', 'install', '-y', pkg], sudo=True, quiet=True):
                        self.states[pkg] = f"{KaliStyle.GREEN}Completed{KaliStyle.RESET}"
                        self.actions_taken.append({'type': 'package', 'pkg': pkg})  
                    else:
                        self.states[pkg] = f"{KaliStyle.RED}Failed{KaliStyle.RESET}"
                        failed_packages.append(pkg)
                        print(f"{KaliStyle.WARNING} Warning: Failed to install {pkg}, continuing...")
                except subprocess.CalledProcessError as e:
                    self.states[pkg] = f"{KaliStyle.RED}Failed{KaliStyle.RESET}"
                    failed_packages.append(pkg)
                    logging.error(f"Error installing {pkg}: {e}\nOutput: {e.stdout}\nError: {e.stderr}")
                    print(f"{KaliStyle.WARNING} Warning: Failed to install {pkg}, continuing...")
                print_status()
                time.sleep(0.2)
            
            if failed_packages:
                print(f"\n{KaliStyle.WARNING} The following packages failed: {', '.join(failed_packages)}")
                print(f"{KaliStyle.INFO} Check install.log for more details.")
            else:
                print(f"\n{KaliStyle.SUCCESS} Installation completed")
            return True
        except Exception as e:
            print(f"\n{KaliStyle.ERROR} Error installing packages: {str(e)}")
            logging.error(f"General error in install_additional_packages: {str(e)}")
            return False

    def ask_dash_to_panel_installation(self):
        """Pregunta al usuario si desea instalar Dash to Panel"""
        print(f"\n{KaliStyle.INFO} Configuration Options")
        print(f"{KaliStyle.GREY}{'─' * 40}{KaliStyle.RESET}")
        print(f"{KaliStyle.YELLOW}[?]{KaliStyle.RESET} Do you want to install {KaliStyle.BOLD}Dash to Panel{KaliStyle.RESET}?")
        print(f" {KaliStyle.TURQUOISE}→{KaliStyle.RESET} {KaliStyle.WHITE}Yes{KaliStyle.RESET}: Install Dash to Panel (replaces default Dash to Dock) - {KaliStyle.BLUE}https://i.imgur.com/uO0oKGG.png{KaliStyle.RESET}")
        print(f" {KaliStyle.TURQUOISE}→{KaliStyle.RESET} {KaliStyle.WHITE}No{KaliStyle.RESET}: Keep default Dash to Dock - {KaliStyle.BLUE}https://i.imgur.com/Ro4z815.png{KaliStyle.RESET}")
        while True:
            try:
                response = input(f"\n{KaliStyle.SUDO_COLOR}[*]{KaliStyle.RESET} Install Dash to Panel? (Y/n): ").lower().strip()
                if response == '' or response == 'y' or response == 'yes':
                    self.dash_to_panel_installed = True
                    print(f"{KaliStyle.SUCCESS} Dash to Panel will be installed")
                    return True
                elif response == 'n' or response == 'no':
                    self.dash_to_panel_installed = False
                    print(f"{KaliStyle.SUCCESS} Default Dash to Dock will be preserved")
                    return True
                else:
                    print(f"{KaliStyle.WARNING} Please enter 'y' for yes or 'n' for no")
            except KeyboardInterrupt:
                print(f"\n{KaliStyle.WARNING} Installation cancelled")
                return False

    def install_gnome_extensions(self):
        print(f"\n{KaliStyle.INFO} Installing GNOME extensions...")
        if os.path.exists(self.temp_dir):
            shutil.rmtree(self.temp_dir)
        os.makedirs(self.temp_dir)
        os.chdir(self.temp_dir)

        if not self.ask_dash_to_panel_installation():
            return False

        if self.dash_to_panel_installed:
            if not self.install_dash_to_panel():
                return False
        else:
            print(f"{KaliStyle.INFO} Skipping Dash to Panel installation. Keeping Dash to Dock active.")

        self.manage_extensions(quiet=True)
        return True 

    def install_dash_to_panel(self):
        print(f"\n{KaliStyle.INFO} Installing Dash to Panel (latest release)...")
        ext_paths = [
            os.path.join(self.extensions_dir, "dash-to-panel@jderose9.github.com"),
            "/usr/share/gnome-shell/extensions/dash-to-panel@jderose9.github.com"
        ]
        if any(os.path.exists(path) for path in ext_paths):
            print(f"{KaliStyle.WARNING} Dash to Panel already installed, skipping.")
            return True
        
        try:
            tags_output = subprocess.check_output(["git", "ls-remote", "--tags", "https://github.com/home-sweet-gnome/dash-to-panel.git"])
            tags = [line.decode().split()[-1].replace('refs/tags/', '') for line in tags_output.splitlines() if '^' not in line.decode()]
            latest_tag = sorted(tags, key=lambda t: int(t.replace('v', '')))[-1]  
            
            zip_url = f"https://github.com/home-sweet-gnome/dash-to-panel/releases/download/{latest_tag}/dash-to-panel@jderose9.github.com_{latest_tag}.zip"
            zip_path = os.path.join(self.temp_dir, "dash-to-panel.zip")
            
            urllib.request.urlretrieve(zip_url, zip_path)
            print(f"{KaliStyle.SUCCESS} Downloaded zip of version {latest_tag}")
            
            if self.run_command(["gnome-extensions", "install", "--force", zip_path], quiet=True):
                print(f"{KaliStyle.SUCCESS} Dash to Panel installed from release {latest_tag}")
                self.actions_taken.append({'type': 'dir_copy', 'dest': ext_paths[0]})
                return True
            else:
                print(f"{KaliStyle.ERROR} Error installing zip with gnome-extensions")
                return False
        except Exception as e:
            print(f"{KaliStyle.ERROR} Error installing Dash to Panel: {str(e)}")
            logging.error(f"Error in install_dash_to_panel: {str(e)}")
            return False

    def manage_extensions(self, quiet=False):
        if not quiet:
            print(f"\n{KaliStyle.INFO} Checking and disabling existing extensions")
        try:
            extensions_to_disable = [
                'system-monitor@gnome-shell-extensions.gcampax.github.com',
                'apps-menu@gnome-shell-extensions.gcampax.github.com',
                'top-panel-vpnip@kali.org'
            ]
            if self.dash_to_panel_installed:
                extensions_to_disable.append('dash-to-dock@micxgx.gmail.com')
            for ext in extensions_to_disable:
                subprocess.run(['gnome-extensions', 'disable', ext], stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
                if not quiet:
                    print(f"{KaliStyle.SUCCESS} Extension {ext} disabled (if it was active)")
        except Exception as e:
            if not quiet:
                print(f"{KaliStyle.WARNING} Could not manage all extensions")
            logging.error(f"Error in manage_extensions: {str(e)}")

    def enable_extensions(self):
        print(f"\n{KaliStyle.INFO} Enabling extensions...")
        
        extensions = [
            "top-panel-ethernet@kali.org",
            "top-panel-target@kali.org", 
            "top-panel-vpnip@kali.org",
            "top-bar-organizer@julian.gse.jsts.xyz"
        ]
        if self.dash_to_panel_installed:
            extensions.insert(0, "dash-to-panel@jderose9.github.com")
        
        enabled_count = 0
        for ext in extensions:
            try:
                subprocess.run(['gnome-extensions', 'enable', ext], check=True, stdout=subprocess.DEVNULL)
                print(f"{KaliStyle.SUCCESS} {ext} enabled")
                enabled_count += 1
            except subprocess.CalledProcessError as e:
                print(f"{KaliStyle.ERROR} Error enabling {ext}: {str(e)}")
                logging.error(f"Error enabling extension {ext}: {str(e)}")
            except Exception as e:
                print(f"{KaliStyle.ERROR} Unexpected error enabling {ext}: {str(e)}")
                logging.error(f"Error in enable_extensions: {str(e)}")

        if self.dash_to_panel_installed:
            dash_config_source = os.path.join(self.script_dir, "dash-to-panel-settings.dconf")
            if os.path.exists(dash_config_source) and os.path.getsize(dash_config_source) > 0:
                try:
                    with open(dash_config_source, 'rb') as f:
                        subprocess.run(['dconf', 'load', '/org/gnome/shell/extensions/dash-to-panel/'], 
                                       input=f.read(), check=True)
                    print(f"{KaliStyle.SUCCESS} Dash to Panel configuration applied")
                except Exception as e:
                    print(f"{KaliStyle.ERROR} Error applying Dash to Panel configuration: {str(e)}")
                    logging.error(f"Error applying Dash to Panel configuration: {str(e)}")

        top_bar_config_filename = "top-bar-organizer.dconf" if self.dash_to_panel_installed else "top-bar-organizer-dash-to-dock.dconf"
        top_bar_config_source = os.path.join(self.script_dir, top_bar_config_filename)
        if os.path.exists(top_bar_config_source) and os.path.getsize(top_bar_config_source) > 0:
            try:
                with open(top_bar_config_source, 'rb') as f:
                    subprocess.run(['dconf', 'load', '/org/gnome/shell/extensions/top-bar-organizer/'], 
                                   input=f.read(), check=True)
                print(f"{KaliStyle.SUCCESS} Top Bar Organizer configuration applied")
            except Exception as e:
                print(f"{KaliStyle.ERROR} Error applying Top Bar Organizer configuration: {str(e)}")
                logging.error(f"Error applying Top Bar Organizer configuration: {str(e)}")
        
        if enabled_count > 0:
            print(f"{KaliStyle.SUCCESS} {enabled_count}/{len(extensions)} extensions enabled")
            return True
        else:
            print(f"{KaliStyle.ERROR} Could not enable any extension")
            return False

    def verify_installation(self):
        print(f"\n{KaliStyle.INFO} Verifying installation...")
        
        extensions_to_check = [
            "top-panel-ethernet@kali.org",
            "top-panel-target@kali.org", 
            "top-panel-vpnip@kali.org",
            "top-bar-organizer@julian.gse.jsts.xyz"
        ]
        if self.dash_to_panel_installed:
            extensions_to_check.insert(0, "dash-to-panel@jderose9.github.com")
        
        installed_count = 0
        for ext in extensions_to_check:
            ext_path = os.path.join(self.extensions_dir, ext)
            system_path = f"/usr/share/gnome-shell/extensions/{ext}"
            if os.path.exists(ext_path) or os.path.exists(system_path):
                print(f"{KaliStyle.SUCCESS} {ext} found")
                installed_count += 1
            else:
                print(f"{KaliStyle.ERROR} {ext} not found")
        
        if installed_count > 0:
            print(f"\n{KaliStyle.WARNING} Restart GNOME Shell {KaliStyle.GREY}(Alt + F2, 'r'){KaliStyle.RESET}")
            input(f"\n{KaliStyle.SUDO_COLOR}[*]{KaliStyle.RESET} Press Enter after restarting GNOME Shell...")
            self.enable_extensions()
            return True
        return False

    def setup_dotfiles(self):
        print(f"\n{KaliStyle.INFO} Setting up dotfiles...")
        success = True
        zshrc_path = os.path.join(self.home_dir, '.zshrc')
        if os.path.exists(zshrc_path):
            backup_path = f"{zshrc_path}.backup.{time.strftime('%Y%m%d_%H%M%S')}"
            shutil.copy2(zshrc_path, backup_path)
            self.actions_taken.append({'type': 'file_copy', 'dest': backup_path})
            print(f"{KaliStyle.SUCCESS} Backup of .zshrc created")

        required_files = {'.zshrc': os.path.join(self.script_dir, ".zshrc")}
        for name, path in required_files.items():
            if not os.path.exists(path):
                print(f"{KaliStyle.ERROR} {name} not found")
                success = False
        
        if success:
            shutil.copy2(required_files['.zshrc'], self.home_dir)
            self.actions_taken.append({'type': 'file_copy', 'dest': zshrc_path})
            self.install_fzf(self.current_user)
            self.install_fzf("root")
            if self.home_dir != '/root':  
                subprocess.run(['sudo', 'ln', '-sf', zshrc_path, "/root/.zshrc"], check=True, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
            else:
                print(f"{KaliStyle.WARNING} Skipping link for root, as the script should not run as root.")
            self.install_neovim()
            print(f"{KaliStyle.SUCCESS} Dotfiles configured")
        return success

    def install_fzf(self, user):
        home_dir = f"/home/{user}" if user != "root" else "/root"
        fzf_dir = os.path.join(home_dir, ".fzf")
        
        if user == "root":
            check_result = subprocess.run(['sudo', 'test', '-d', fzf_dir], stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
            exists = (check_result.returncode == 0)
        else:
            exists = os.path.exists(fzf_dir)
        
        if not exists:
            print(f"{KaliStyle.INFO} Installing fzf for {user}...")
            cmd = ["sudo"] if user == "root" else []
            try:
                subprocess.run(cmd + ["git", "clone", "--depth", "1", "https://github.com/junegunn/fzf.git", fzf_dir], check=True, stdout=subprocess.DEVNULL, stderr=subprocess.PIPE)
                subprocess.run(cmd + [f"{fzf_dir}/install", "--all"], check=True, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
                print(f"{KaliStyle.SUCCESS} fzf installed for {user}")
            except subprocess.CalledProcessError as e:
                print(f"{KaliStyle.ERROR} Error installing fzf for {user}: {e.stderr.decode()}")
                logging.error(f"Error in install_fzf for {user}: {str(e)}")
                return False
        else:
            print(f"{KaliStyle.WARNING} fzf already exists for {user}, skipping installation")
        return True

    def install_neovim(self):
        print(f"\n{KaliStyle.INFO} Installing Neovim and NvChad...")
        nvim_url = "https://github.com/neovim/neovim/releases/download/nightly/nvim-linux-x86_64.tar.gz"
        nvim_archive = os.path.join(self.script_dir, "nvim-linux-x86_64.tar.gz")
        backup_archive = os.path.join(self.script_dir, "nvim-x86_64.tar.gz")
        
        try:
            urllib.request.urlretrieve(nvim_url, nvim_archive)
            archive_to_use = nvim_archive
            opt_archive = "/opt/nvim-linux-x86_64.tar.gz"
        except Exception as download_error:
            print(f"{KaliStyle.WARNING} Error downloading Neovim. Using local backup...")
            if os.path.exists(backup_archive):
                archive_to_use = backup_archive
                opt_archive = "/opt/nvim-x86_64.tar.gz"
            else:
                print(f"{KaliStyle.ERROR} Backup not found {backup_archive}")
                logging.error(f"Backup not found {backup_archive}")
                return False
        
        try:
            subprocess.run(["sudo", "cp", archive_to_use, opt_archive], check=True, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)

            subprocess.run(["sudo", "tar", "xzf", opt_archive, "-C", "/opt/"], check=True, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)

            nvim_config = os.path.join(self.config_dir, "nvim")
            if os.path.exists(nvim_config):
                shutil.move(nvim_config, f"{nvim_config}.bak")
            subprocess.run(["git", "clone", "https://github.com/NvChad/starter", nvim_config], check=True, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
            subprocess.run(["sudo", "git", "clone", "https://github.com/NvChad/starter", "/root/.config/nvim"], check=True, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
            print(f"{KaliStyle.SUCCESS} Neovim and NvChad installed")
            return True
        except Exception as e:
            print(f"{KaliStyle.ERROR} Error installing Neovim: {str(e)}")
            logging.error(f"Error in install_neovim: {str(e)}")
            return False

    def install_extract_ports(self):
        print(f"\n{KaliStyle.INFO} Installing extractPorts...")
        extractports_path = os.path.join(self.script_dir, "extractPorts.py")
        dest_path = "/usr/bin/extractPorts.py"
        if os.path.exists(extractports_path):
            if os.path.exists(dest_path):
                print(f"{KaliStyle.WARNING} extractPorts already installed, skipping.")
                return True
            subprocess.run(["chmod", "+x", extractports_path], check=True, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
            subprocess.run(["sudo", "cp", extractports_path, dest_path], check=True, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
            subprocess.run(["sudo", "chmod", "+x", dest_path], check=True, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
            print(f"{KaliStyle.SUCCESS} extractPorts installed")
            self.actions_taken.append({'type': 'file_copy', 'dest': dest_path})
            return True
        return False
        
    def setup_aliases(self):
        print(f"\n{KaliStyle.INFO} Setting up aliases...")
        zshrc_path = f"{self.home_dir}/.zshrc"
        
        target_dir = os.path.join(self.config_dir, "bin", "target")
        os.makedirs(target_dir, exist_ok=True)
        self.actions_taken.append({'type': 'dir_copy', 'dest': target_dir})
        print(f"{KaliStyle.SUCCESS} Directory {target_dir} created or verified")
        
        target_file = os.path.join(target_dir, "target.txt")
        try:
            with open(target_file, 'a') as f:
                pass
            self.actions_taken.append({'type': 'file_copy', 'dest': target_file})
            print(f"{KaliStyle.SUCCESS} File {target_file} created")
        except Exception as e:
            print(f"{KaliStyle.ERROR} Error creating {target_file}: {str(e)}")
            logging.error(f"Error creating {target_file}: {str(e)}")
            return False

        aliases_and_functions = [
            f"\n# Aliases\nalias {self.current_user}='su {self.current_user}'",
            "\nalias bat='batcat'",
            f"""\n# settarget function
    function settarget() {{

        local WHITE='\\033[1;37m'
        local GREEN='\\033[0;32m'
        local YELLOW='\\033[1;33m'
        local RED='\\033[0;31m'
        local BLUE='\\033[0;34m'
        local CYAN='\\033[1;36m'
        local PURPLE='\\033[1;35m'
        local GRAY='\\033[38;5;244m'
        local BOLD='\\033[1m'
        local ITALIC='\\033[3m'
        local COMAND='\\033[38;2;73;174;230m'
        local NC='\\033[0m' # No color
        
        local target_file="{target_file}"
        
        mkdir -p "$(dirname "$target_file")" 2>/dev/null
        
        if [ $# -eq 0 ]; then
            if [ -f "$target_file" ]; then
                rm -f "$target_file"
                echo -e "\\n${{CYAN}}[${{BOLD}}+${{NC}}${{CYAN}}]${{NC}} Target cleared successfully\\n"
            else
                echo -e "\\n${{YELLOW}}[${{BOLD}}!${{YELLOW}}]${{NC}} No target to clear\\n"
            fi
            return 0
        fi
        
        local ip_address="$1"
        local machine_name="$2"
        
        if [ -z "$ip_address" ] || [ -z "$machine_name" ]; then
            echo -e "\\n${{RED}}▋${{NC}} Error${{RED}}${{BOLD}}:${{NC}}${{ITALIC}} usage mode.${{NC}}"
            echo -e "${{GRAY}}—————————————————————${{NC}}"
            echo -e "  ${{CYAN}}• ${{NC}}${{COMAND}}settarget ${{NC}}192.168.1.100 WebServer "
            echo -e "  ${{CYAN}}• ${{NC}}${{COMAND}}settarget ${{GRAY}}${{ITALIC}}(clear target)${{NC}}\\n"
            return 1
        fi
        
        if ! echo "$ip_address" | grep -qE '^[0-9]{{1,3}}\\.[0-9]{{1,3}}\\.[0-9]{{1,3}}\\.[0-9]{{1,3}}$'; then
            echo -e "\\n${{RED}}▋${{NC}} Error${{RED}}${{BOLD}}:${{NC}}"
            echo -e "${{GRAY}}————————${{NC}}"
            echo -e "${{RED}}[${{BOLD}}✘${{NC}}${{RED}}]${{NC}} Invalid IP format ${{YELLOW}}→${{NC}} ${{RED}}$ip_address${{NC}}"
            echo -e "${{BLUE}}${{BOLD}}[+] ${{NC}}Valid example:${{NC}} ${{GRAY}}192.168.1.100${{NC}}\\n"
            return 1
        fi
        
        if ! echo "$ip_address" | awk -F'.' '{{
            for(i=1; i<=4; i++) {{
                if($i < 0 || $i > 255) exit 1
                if(length($i) > 1 && substr($i,1,1) == "0") exit 1
            }}
        }}'; then
            echo -e "\\n${{RED}}[${{BOLD}}✘${{NC}}${{RED}}]${{NC}} Invalid IP ${{RED}}→${{NC}} ${{BOLD}}$ip_address${{NC}}"
            return 1
        fi
        
        echo "$ip_address $machine_name" > "$target_file"
        
        if [ $? -eq 0 ]; then
            echo -e "\\n${{YELLOW}}▌${{NC}}Target set successfully${{YELLOW}}${{BOLD}}:${{NC}}"
            echo -e "${{GRAY}}—————————————————————————————————${{NC}}"
            echo -e "${{CYAN}}→${{NC}} IP Address:${{GRAY}}...........${{NC}} ${{GREEN}}$ip_address${{NC}}"
            echo -e "${{CYAN}}→${{NC}} Machine Name:${{GRAY}}.........${{NC}} ${{GREEN}}$machine_name${{NC}}\\n"
        else
            echo -e "\\n${{RED}}[${{BOLD}}✘${{NC}}${{RED}}]${{NC}} Could not save the target\\n"
            return 1
        fi
        
        return 0
    }}"""
        ]
        try:
            with open(zshrc_path, 'a') as f:
                f.writelines(aliases_and_functions)
            print(f"{KaliStyle.SUCCESS} Aliases configured")
            return True
        except Exception as e:
            print(f"{KaliStyle.ERROR} Error setting aliases in {zshrc_path}: {str(e)}")
            logging.error(f"Error setting aliases: {str(e)}")
            return False

    def install_fonts(self):
        print(f"\n{KaliStyle.INFO} Installing JetBrainsMono fonts...")
        fonts_archive = os.path.join(self.script_dir, "JetBrainsMono.zip")
        if os.path.exists(fonts_archive):
            subprocess.run(["sudo", "mkdir", "-p", "/usr/share/fonts/JetBrainsMono"], check=True, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
            subprocess.run(["sudo", "unzip", "-o", fonts_archive, "-d", "/usr/share/fonts/JetBrainsMono/"], check=True, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
            subprocess.run(["sudo", "fc-cache", "-f", "-v"], check=True, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
            print(f"{KaliStyle.SUCCESS} Fonts installed")
            return True
        return False

    def install_sudo_plugin(self):
        print(f"\n{KaliStyle.INFO} Installing sudo plugin...")
        sudo_plugin_dir = os.path.join(self.script_dir, "sudo-plugin")
        if os.path.exists(sudo_plugin_dir):
            subprocess.run(["sudo", "mkdir", "-p", "/usr/share/sudo-plugin"], check=True, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
            subprocess.run(["sudo", "cp", "-r", f"{sudo_plugin_dir}/.", "/usr/share/sudo-plugin/"], check=True, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
            subprocess.run(["sudo", "chown", "-R", f"{self.current_user}:{self.current_user}", "/usr/share/sudo-plugin"], check=True, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
            print(f"{KaliStyle.SUCCESS} Sudo plugin installed")
            return True
        return False

    def install_config_folder(self, source_dir, dest_dir, config_name):
        print(f"\n{KaliStyle.INFO} Installing {config_name} configuration...")
        if os.path.exists(dest_dir):
            if os.path.isdir(dest_dir):
                print(f"{KaliStyle.WARNING} {config_name} configuration already exists, skipping.")
                return True
            else:
                print(f"{KaliStyle.WARNING} {dest_dir} exists but is not a directory, deleting...")
                os.remove(dest_dir)
        os.makedirs(dest_dir, exist_ok=True)
        if os.path.exists(source_dir):
            shutil.copytree(source_dir, dest_dir, dirs_exist_ok=True)  
            self.actions_taken.append({'type': 'dir_copy', 'dest': dest_dir})
            print(f"{KaliStyle.SUCCESS} {config_name} configuration installed")
            return True
        return False

    def install_terminator_config(self):
        return self.install_config_folder(
            os.path.join(self.script_dir, "terminator"),
            os.path.join(self.home_dir, '.config', 'terminator'),
            "Terminator"
        )

    def install_kitty_config(self):
        return self.install_config_folder(
            os.path.join(self.script_dir, "kitty"),
            os.path.join(self.home_dir, '.config', 'kitty'),
            "Kitty"
        )

    def setup_wallpaper(self):
        print(f"\n{KaliStyle.INFO} Setting up wallpaper...")
        wallpaper_source_dir = os.path.join(self.script_dir, "wallpaper")
        wallpaper_file = os.path.join(wallpaper_source_dir, "kali-simple-3840x2160.png")
        wallpaper_dest_dir = os.path.join(self.pictures_dir, "wallpaper")
        wallpaper_dest_path = os.path.join(wallpaper_dest_dir, "kali-simple-3840x2160.png")

        try:
            if not os.path.exists(wallpaper_file):
                print(f"{KaliStyle.ERROR} Wallpaper not found in {wallpaper_file}")
                return False

            os.makedirs(wallpaper_dest_dir, exist_ok=True)

            shutil.copy2(wallpaper_file, wallpaper_dest_path)
            self.actions_taken.append({'type': 'file_copy', 'dest': wallpaper_dest_path})

            subprocess.run(['gsettings', 'set', 'org.gnome.desktop.background', 'picture-uri', f"file://{wallpaper_dest_path}"], check=True, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
            subprocess.run(['gsettings', 'set', 'org.gnome.desktop.background', 'picture-uri-dark', f"file://{wallpaper_dest_path}"], check=True, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
            subprocess.run(['gsettings', 'set', 'org.gnome.desktop.background', 'picture-options', 'zoom'], check=True, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
            print(f"{KaliStyle.SUCCESS} Wallpaper set")
            return True
        except Exception as e:
            print(f"{KaliStyle.ERROR} Error setting wallpaper: {str(e)}")
            logging.error(f"Error in setup_wallpaper: {str(e)}")
            return False

    def setup_gdm_wallpaper(self):
        print(f"\n{KaliStyle.INFO} Setting up GDM wallpaper...")
        wallpaper_source_dir = os.path.join(self.script_dir, "wallpaper")
        wallpaper_source_file = os.path.join(wallpaper_source_dir, "gdm_wallpaper.png")
        gdm_wallpaper_dest_dir = "/usr/share/backgrounds/kali"
        gdm_wallpaper_dest_file = os.path.join(gdm_wallpaper_dest_dir, "login-blurred")
        backup_file = f"{gdm_wallpaper_dest_file}.bak.{time.strftime('%Y%m%d_%H%M%S')}"

        try:
            if not os.path.exists(wallpaper_source_file):
                print(f"{KaliStyle.ERROR} Wallpaper not found in {wallpaper_source_file}")
                return False
            print(f"{KaliStyle.SUCCESS} Wallpaper file found: {wallpaper_source_file}")

            if not os.path.exists(gdm_wallpaper_dest_dir):
                if not self.run_command(['mkdir', '-p', gdm_wallpaper_dest_dir], sudo=True, quiet=True):
                    print(f"{KaliStyle.ERROR} Could not create directory {gdm_wallpaper_dest_dir}")
                    return False
                print(f"{KaliStyle.SUCCESS} Directory created: {gdm_wallpaper_dest_dir}")

            if os.path.exists(gdm_wallpaper_dest_file):
                if not self.run_command(['cp', gdm_wallpaper_dest_file, backup_file], sudo=True, quiet=True):
                    print(f"{KaliStyle.ERROR} Could not create backup of {gdm_wallpaper_dest_file}")
                    return False
                self.actions_taken.append({'type': 'file_copy', 'dest': backup_file})
                print(f"{KaliStyle.SUCCESS} Backup created: {backup_file}")

            if not self.run_command(['cp', wallpaper_source_file, gdm_wallpaper_dest_file], sudo=True, quiet=True):
                print(f"{KaliStyle.ERROR} Could not copy wallpaper to {gdm_wallpaper_dest_file}")
                return False
            if not self.run_command(['chmod', '644', gdm_wallpaper_dest_file], sudo=True, quiet=True):
                print(f"{KaliStyle.ERROR} Could not set permissions on {gdm_wallpaper_dest_file}")
                return False
            self.actions_taken.append({'type': 'file_copy', 'dest': gdm_wallpaper_dest_file})
            print(f"{KaliStyle.SUCCESS} Wallpaper copied and renamed to {gdm_wallpaper_dest_file}")

            self.needs_gdm_restart = True

            print(f"{KaliStyle.SUCCESS} GDM wallpaper configured")
            return True
        except Exception as e:
            print(f"{KaliStyle.ERROR} Error setting GDM wallpaper: {str(e)}")
            logging.error(f"Error in setup_gdm_wallpaper: {str(e)}")
            return False

    def setup_browser_wallpaper(self):
        print(f"\n{KaliStyle.INFO} Setting up browser wallpaper...")
        wallpaper_source_dir = os.path.join(self.script_dir, "wallpaper")
        wallpaper_file = os.path.join(wallpaper_source_dir, "browser-home-page-banner.jpg")
        target_dir = "/usr/share/kali-defaults/web/images"
        target_file = os.path.join(target_dir, "browser-home-page-banner.jpg")
        backup_file = os.path.join(target_dir, "browser-home-page-banner.jpg.bak")

        try:
            if not os.path.exists(wallpaper_file):
                print(f"{KaliStyle.ERROR} Browser wallpaper not found in {wallpaper_file}")
                return False

            os.makedirs(target_dir, exist_ok=True)

            if os.path.exists(target_file):
                self.run_command(['mv', target_file, backup_file], sudo=True, quiet=True)
                self.actions_taken.append({'type': 'file_copy', 'dest': backup_file})

            self.run_command(['cp', wallpaper_file, target_file], sudo=True, quiet=True)
            self.actions_taken.append({'type': 'file_copy', 'dest': target_file})

            self.run_command(['chmod', '644', target_file], sudo=True, quiet=True)
            print(f"{KaliStyle.SUCCESS} Browser wallpaper configured correctly.")
            return True
        except Exception as e:
            print(f"{KaliStyle.ERROR} Error setting browser wallpaper: {str(e)}")
            logging.error(f"Error in setup_browser_wallpaper: {str(e)}")
            return False

    def setup_grub_images(self):
        print(f"\n{KaliStyle.INFO} Setting up GRUB boot images...")
        wallpaper_source_dir = os.path.join(self.script_dir, "wallpaper")
        dest_dirs = [
            "/boot/grub/themes/kali",
            "/usr/share/grub/themes/kali",
            "/usr/share/desktop-base/kali-theme/grub"
        ]
        image_names = ["grub-16x9.png", "grub-4x3.png"]

        try:
            for dest_dir in dest_dirs:
                if not os.path.exists(dest_dir):
                    continue
                print(f"{KaliStyle.INFO} Updating in {dest_dir}...")
                for image_name in image_names:
                    source = os.path.join(wallpaper_source_dir, image_name)
                    if not os.path.exists(source):
                        print(f"{KaliStyle.ERROR} Image not found: {source}")
                        continue

                    dest = os.path.join(dest_dir, image_name)
                    backup = f"{dest}.bak.{time.strftime('%Y%m%d_%H%M%S')}"

                    if os.path.exists(dest):
                        if not self.run_command(['cp', dest, backup], sudo=True, quiet=True):
                            print(f"{KaliStyle.ERROR} Failed to backup {dest}")
                            continue
                        self.actions_taken.append({'type': 'backup', 'backup': backup, 'original': dest})
                        print(f"{KaliStyle.SUCCESS} Backup created: {backup}")

                    if not self.run_command(['cp', source, dest], sudo=True, quiet=True):
                        print(f"{KaliStyle.ERROR} Failed to copy {source} to {dest}")
                        continue
                    self.actions_taken.append({'type': 'file_copy', 'dest': dest})

                    self.run_command(['chmod', '644', dest], sudo=True, quiet=True)
                    print(f"{KaliStyle.SUCCESS} Installed {image_name} in {dest_dir}")

            print(f"{KaliStyle.INFO} Updating GRUB configuration...")
            if not self.run_command(['update-grub'], sudo=True, quiet=True):
                print(f"{KaliStyle.ERROR} Failed to update GRUB")
                return False

            print(f"{KaliStyle.SUCCESS} GRUB images updated")
            return True
        except Exception as e:
            print(f"{KaliStyle.ERROR} Error updating GRUB images: {str(e)}")
            logging.error(f"Error in setup_grub_images: {str(e)}")
            return False

    def setup_ctf_folders(self):
        print(f"\n{KaliStyle.INFO} Setting up CTF folders...")
        ctf_folders = [
            "/root/machines_vuln/HTB",
            "/root/machines_vuln/Vulnhub",
            "/root/machines_vuln/DockerLabs"
        ]

        try:
            for folder in ctf_folders:
                check_result = subprocess.run(['sudo', 'test', '-d', folder], stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
                if check_result.returncode == 0:
                    print(f"{KaliStyle.WARNING} Folder {folder} already exists")
                    continue
                self.run_command(['mkdir', '-p', folder], sudo=True, quiet=True)
                self.actions_taken.append({'type': 'dir_copy', 'dest': folder})
                print(f"{KaliStyle.SUCCESS} Created folder {folder}")
            print(f"\n{KaliStyle.SUCCESS} CTF folders configured")
            return True
        except Exception as e:
            print(f"{KaliStyle.ERROR} Error creating CTF folders: {str(e)}")
            logging.error(f"Error in setup_ctf_folders: {str(e)}")
            return False

    def configure_keyboard_shortcuts(self):
        print(f"\n{KaliStyle.INFO} Setting up keyboard shortcuts...")
        default_keys = ['screenshot', 'screenshot-clip', 'window-screenshot', 'window-screenshot-clip', 'area-screenshot', 'area-screenshot-clip']
        shell_keys = ['screenshot', 'screenshot-window', 'show-screenshot-ui']
        
        for key in default_keys + shell_keys:
            schema = 'org.gnome.settings-daemon.plugins.media-keys' if key in default_keys else 'org.gnome.shell.keybindings'
            subprocess.run(['gsettings', 'set', schema, key, '[]'], stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)

        shortcuts = [
            {"name": "Terminator", "command": "/usr/bin/terminator", "shortcut": "<Super>Return"},
            {"name": "Obsidian", "command": "/usr/bin/obsidian", "shortcut": "<Super><Shift>o"},
            {"name": "Screenshot", "command": "flameshot gui", "shortcut": "Print"},
            {"name": "Burpsuite", "command": "/usr/bin/burpsuite", "shortcut": "<Super><Shift>b"},
            {"name": "Firefox", "command": "/usr/bin/firefox", "shortcut": "<Super><Shift>f"},
            {"name": "Nautilus", "command": "/usr/bin/nautilus", "shortcut": "<Super>e"}
        ]

        paths = [f"'/org/gnome/settings-daemon/plugins/media-keys/custom-keybindings/custom{i}/'" for i in range(len(shortcuts))]
        subprocess.run(['gsettings', 'set', 'org.gnome.settings-daemon.plugins.media-keys', 'custom-keybindings', f"[{', '.join(paths)}]"], check=True, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
        for i, shortcut in enumerate(shortcuts):
            base_path = f"org.gnome.settings-daemon.plugins.media-keys.custom-keybinding:/org/gnome/settings-daemon/plugins/media-keys/custom-keybindings/custom{i}/"
            subprocess.run(['gsettings', 'set', base_path, 'name', shortcut['name']], check=True, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
            subprocess.run(['gsettings', 'set', base_path, 'command', shortcut['command']], check=True, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
            subprocess.run(['gsettings', 'set', base_path, 'binding', shortcut['shortcut']], check=True, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
            print(f"{KaliStyle.SUCCESS} Shortcut configured: {shortcut['name']}")
        return True
    
# ------------------------------------- MESSSAGES FINISHING INSTALLATION ------------------------------------- #
    def show_final_message(self):
        time.sleep(2)
        os.system('clear')
        print(f"\n\t\t[{KaliStyle.BLUE}{KaliStyle.BOLD}+{KaliStyle.RESET}] Installation Summary [{KaliStyle.BLUE}{KaliStyle.BOLD}+{KaliStyle.RESET}]\n\n")

        print(f"[{KaliStyle.BLUE}{KaliStyle.BOLD}+{KaliStyle.RESET}] Keyboard Shortcuts")
        shortcuts = [
            ("Terminator", "Super + Enter"),
            ("Flameshot", "Print"),
            ("Firefox", "Super + Shift + F"),
            ("Obsidian", "Super + Shift + O"),
            ("Burpsuite", "Super + Shift + B"),
            ("Nautilus", "Super + E")
        ]
        
        for name, shortcut in shortcuts:
            print(f"   {KaliStyle.YELLOW}▸{KaliStyle.RESET} {KaliStyle.WHITE}{name:<12}{KaliStyle.RESET} {KaliStyle.GREY}→{KaliStyle.RESET} {KaliStyle.TURQUOISE}{shortcut}{KaliStyle.RESET}")
        
        print()
        
        print(f"[{KaliStyle.BLUE}{KaliStyle.BOLD}+{KaliStyle.RESET}] Development Tools")
        tools = [
            ("Neovim", "Advanced text editor with NvChad"),
            ("ZSH", "Enhanced shell with custom configuration"),
            ("FZF", "Fuzzy finder for quick navigation"),
            ("LSD", "Modern replacement for 'ls' command"),
            ("BAT", "Syntax highlighting for file viewing"),
            ("Terminator", "Advanced terminal multiplexer")
        ]
        
        for name, desc in tools:
            print(f"   {KaliStyle.YELLOW}▸{KaliStyle.RESET} {KaliStyle.WHITE}{name:<12}{KaliStyle.RESET} {KaliStyle.GREY}→{KaliStyle.RESET} {desc}")
        
        print()

        print(f"[{KaliStyle.BLUE}{KaliStyle.BOLD}+{KaliStyle.RESET}] GNOME Extensions")
        extensions = [
            ("Dash to Panel", "Customizable taskbar and panel"),
            ("Top Panel Ethernet", "Network interface monitoring"),
            ("Top Panel Target", "Target machine information"),
            ("Top Panel VPN IP", "VPN connection status"),
            ("Top Bar Organizer", "Panel element organization")
        ]
        
        for name, desc in extensions:
            print(f"   {KaliStyle.YELLOW}▸{KaliStyle.RESET} {KaliStyle.WHITE}{name:<18}{KaliStyle.RESET} {KaliStyle.GREY}→{KaliStyle.RESET} {desc}")
        
        print()

        print(f"[{KaliStyle.BLUE}{KaliStyle.BOLD}+{KaliStyle.RESET}] Additional Features")
        features = [
            ("Custom Wallpapers", "Desktop and GDM login backgrounds - by SkyW4r33x"),
            ("GRUB Boot Images", "Custom boot screen images - by SkyW4r33x"),
            ("CTF Directories", "Organized folders for pentesting"),
            ("ExtractPorts Tool", "Network scanning utility"),
            ("Custom Aliases", "Enhanced command shortcuts"),
            ("JetBrains Mono", "Professional coding font")
        ]
        
        for name, desc in features:
            print(f"   {KaliStyle.YELLOW}▸{KaliStyle.RESET} {KaliStyle.WHITE}{name:<17}{KaliStyle.RESET} {KaliStyle.GREY}→{KaliStyle.RESET} {desc}")
        print(f"\n[{KaliStyle.GREEN}{KaliStyle.BOLD}*{KaliStyle.RESET}] {KaliStyle.BOLD}UPDATE 28/03/2025:{KaliStyle.RESET} New background for the Kali Linux boot manager")
        print(f"[{KaliStyle.BLUE}{KaliStyle.BOLD}i{KaliStyle.RESET}] {KaliStyle.BLUE}https://i.imgur.com/b6zaCgi.png{KaliStyle.RESET}")
        print(f"\n{KaliStyle.TURQUOISE}{'═' * 50}{KaliStyle.RESET}")
        print(f"\n[{KaliStyle.BLUE}{KaliStyle.BOLD}+{KaliStyle.RESET}]{KaliStyle.BOLD} Recommended installations:{KaliStyle.RESET}{KaliStyle.BLUE} https://github.com/SkyW4r33x/searchCommand{KaliStyle.RESET}")
        print(f"[{KaliStyle.GREEN}{KaliStyle.BOLD}*{KaliStyle.RESET}]{KaliStyle.BOLD} searchCommand{KaliStyle.RESET} is a tool search tool that also includes local binary search using {KaliStyle.BOLD}GTFObins{KaliStyle.RESET} data, {KaliStyle.BOLD}GTFSearch {KaliStyle.RESET}")
        print(f"\n{KaliStyle.TURQUOISE}{'═' * 50}{KaliStyle.RESET}")
        print(f"\n{KaliStyle.WARNING}{KaliStyle.BOLD} Important:{KaliStyle.RESET} Restart GNOME Shell {KaliStyle.GREY}(Alt + F2, 'r'){KaliStyle.RESET} or reboot to apply all changes")

    def cleanup(self):
        print(f"\n{KaliStyle.INFO} Cleaning temporary files...")
        if os.path.exists(self.temp_dir):
            shutil.rmtree(self.temp_dir)
            print(f"{KaliStyle.SUCCESS} {KaliStyle.GREEN}Completed{KaliStyle.RESET}")
            return True
        return True

    def rollback(self):
        print(f"{KaliStyle.WARNING} Rolling back changes...")
        for action in reversed(self.actions_taken):
            if action['type'] == 'file_copy' and os.path.exists(action['dest']):
                self.run_command(['rm', action['dest']], sudo=True, quiet=True)
                print(f"{KaliStyle.SUCCESS} Deleted {action['dest']}")
            elif action['type'] == 'dir_copy' and os.path.exists(action['dest']):
                self.run_command(['rm', '-rf', action['dest']], sudo=True, quiet=True)
                print(f"{KaliStyle.SUCCESS} Deleted {action['dest']}")
            elif action['type'] == 'backup' and os.path.exists(action['backup']):
                self.run_command(['mv', action['backup'], action['original']], sudo=True, quiet=True)
                print(f"{KaliStyle.SUCCESS} Restored {action['original']} from backup")
            elif action['type'] == 'package':
                print(f"{KaliStyle.WARNING} Rolling back package {action['pkg']}...")
                self.run_command(['apt', 'remove', '-y', action['pkg']], sudo=True, quiet=True)
        print(f"{KaliStyle.SUCCESS} Changes rolled back")

    def run(self):
        if not all([self.check_os(), self.check_sudo_privileges(), self.check_required_files(), self.check_graphical_environment()]):
            return False

        os.system('clear')
        self.show_banner()

        if not self.check_gnome_requirements():
            return False
        tasks = [
            (self.install_gnome_extensions, "GNOME extensions installation"),
            (self.install_custom_extensions, "Custom extensions installation"),
            (self.verify_installation, "Installation verification"),
            (self.install_additional_packages, "Additional packages installation"),
            (self.setup_dotfiles, "Dotfiles setup"),
            (self.setup_aliases, "Aliases setup"),
            (self.install_extract_ports, "extractPorts installation"),
            (self.install_fonts, "Fonts installation"),
            (self.install_sudo_plugin, "Sudo plugin installation"),
            (self.install_terminator_config, "Terminator configuration"),
            (self.install_kitty_config, "Kitty configuration"),
            (self.configure_keyboard_shortcuts, "Keyboard shortcuts configuration"),
            (self.setup_wallpaper, "Wallpaper setup"),
            (self.setup_browser_wallpaper, "Browser wallpaper setup"),
            (self.setup_ctf_folders, "CTF folders setup"),
            (self.setup_gdm_wallpaper, "GDM wallpaper setup"),
            (self.setup_grub_images, "GRUB images setup")
        ]

        total_tasks = len(tasks)

        try:
            for i, (task, description) in enumerate(tasks, 1):
                print(f"\n{KaliStyle.GREY}{'─' * 40}{KaliStyle.RESET}")
                print(f"{KaliStyle.INFO} ({i}/{total_tasks}) Starting {description}...")
                if not task():
                    print(f"{KaliStyle.ERROR} Error in {description}")
                    self.rollback()
                    self.cleanup()
                    return False
                time.sleep(0.5)
            print()

            self.show_final_message()

            if self.needs_gdm_restart:
                print(f"{KaliStyle.WARNING} It is necessary to restart GDM to apply the changes.")
                user_input = input(f"\n\n{KaliStyle.SUDO_COLOR}[*]{KaliStyle.RESET} Do you want to restart GDM now? (Y/n): ").lower()
                if user_input == '' or user_input == 'y':
                    if not self.run_command(['systemctl', 'restart', 'gdm'], sudo=True, quiet=True):
                        print(f"{KaliStyle.ERROR} Could not restart GDM. Please restart manually with 'sudo systemctl restart gdm'")
                    else:
                        print(f"{KaliStyle.SUCCESS} GDM restarted")
                else:
                    print(f"{KaliStyle.WARNING} Please restart GDM manually with 'sudo systemctl restart gdm'")

            self.cleanup()
            logging.info("Installation completed successfully")
            return True

        except KeyboardInterrupt:
            print(f"\n{KaliStyle.WARNING} Installation interrupted")
            self.rollback()
            self.cleanup()
            return False
        except Exception as e:
            print(f"{KaliStyle.ERROR} Error: {str(e)}")
            logging.error(f"General error in run: {str(e)}")
            self.rollback()
            self.cleanup()
            return False

if __name__ == "__main__":
    installer = CombinedInstaller()
    installer.run()