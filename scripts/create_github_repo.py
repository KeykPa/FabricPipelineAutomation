#!/usr/bin/env python3
"""Create GitHub repository and push code"""

import subprocess
import sys

try:
    import requests
except ImportError:
    print("Installing requests...")
    subprocess.run([sys.executable, "-m", "pip", "install", "requests"], check=True)
    import requests

try:
    from colorama import init, Fore, Style
    init(autoreset=True)
except ImportError:
    class Fore:
        CYAN = GREEN = YELLOW = WHITE = RED = ""
    class Style:
        RESET_ALL = ""


def run_command(cmd):
    """Run shell command and return output."""
    try:
        result = subprocess.run(cmd, shell=True, capture_output=True, text=True, check=True)
        return result.stdout.strip(), True
    except subprocess.CalledProcessError as e:
        return e.stderr.strip(), False


def create_github_repo(token, repo_name, description, is_private=False):
    """Create GitHub repository using API."""
    print(f"\n{Fore.CYAN}Creating GitHub Repository{Style.RESET_ALL}\n")
    
    headers = {
        "Authorization": f"Bearer {token}",
        "Accept": "application/vnd.github+json",
        "X-GitHub-Api-Version": "2022-11-28"
    }
    
    payload = {
        "name": repo_name,
        "description": description,
        "private": is_private,
        "auto_init": False
    }
    
    try:
        response = requests.post(
            "https://api.github.com/user/repos",
            headers=headers,
            json=payload,
            timeout=30
        )
        
        if response.status_code == 201:
            repo_data = response.json()
            print(f"{Fore.GREEN}✓ Repository created successfully{Style.RESET_ALL}")
            print(f"{Fore.WHITE}  Name: {repo_data['name']}{Style.RESET_ALL}")
            print(f"{Fore.WHITE}  URL: {repo_data['html_url']}{Style.RESET_ALL}")
            print(f"{Fore.WHITE}  Clone URL: {repo_data['clone_url']}{Style.RESET_ALL}")
            return repo_data['clone_url'], True
        elif response.status_code == 422:
            error = response.json()
            if 'errors' in error and any('already exists' in str(e) for e in error.get('errors', [])):
                print(f"{Fore.YELLOW}! Repository already exists{Style.RESET_ALL}")
                # Return the expected clone URL
                clone_url = f"https://github.com/alexeikh/{repo_name}.git"
                print(f"{Fore.WHITE}  URL: {clone_url}{Style.RESET_ALL}")
                return clone_url, True
            else:
                print(f"{Fore.RED}✗ Failed to create repository: {error.get('message', 'Unknown error')}{Style.RESET_ALL}")
                return None, False
        else:
            print(f"{Fore.RED}✗ Failed: HTTP {response.status_code}{Style.RESET_ALL}")
            print(f"{Fore.RED}  {response.text}{Style.RESET_ALL}")
            return None, False
            
    except Exception as e:
        print(f"{Fore.RED}✗ Error: {e}{Style.RESET_ALL}")
        return None, False


def configure_git_remote(token, clone_url):
    """Configure git remote with token."""
    print(f"\n{Fore.CYAN}Configuring Git Remote{Style.RESET_ALL}\n")
    
    # Remove existing remote if it exists
    run_command("git remote remove origin")
    
    # Add remote with token
    token_url = clone_url.replace("https://", f"https://{token}@")
    cmd = f'git remote add origin {token_url}'
    output, success = run_command(cmd)
    
    if success or "already exists" in output.lower():
        print(f"{Fore.GREEN}✓ Remote configured{Style.RESET_ALL}")
        return True
    else:
        print(f"{Fore.RED}✗ Failed to configure remote: {output}{Style.RESET_ALL}")
        return False


def push_to_github():
    """Push code to GitHub."""
    print(f"\n{Fore.CYAN}Pushing Code to GitHub{Style.RESET_ALL}\n")
    
    cmd = "git push -u origin main"
    print(f"{Fore.WHITE}Running: {cmd}{Style.RESET_ALL}")
    
    output, success = run_command(cmd)
    
    if success:
        print(f"{Fore.GREEN}✓ Code pushed successfully{Style.RESET_ALL}")
        return True
    else:
        print(f"{Fore.RED}✗ Push failed:{Style.RESET_ALL}")
        print(output)
        return False


def main():
    """Main function."""
    # Configuration
    GITHUB_TOKEN = os.getenv("GITHUB_TOKEN", "")
    if not GITHUB_TOKEN:
        print(f"{Fore.YELLOW}GitHub token not found in environment.{Style.RESET_ALL}")
        GITHUB_TOKEN = input("Enter GitHub Personal Access Token: ").strip()
    
    REPO_NAME = "FabricPipelineAutomation"
    DESCRIPTION = "Conference attendance pipeline using Microsoft Fabric, Azure, and Power BI"
    IS_PRIVATE = False
    
    print(f"\n{Fore.CYAN}{'=' * 80}{Style.RESET_ALL}")
    print(f"{Fore.CYAN}GitHub Repository Setup{Style.RESET_ALL}")
    print(f"{Fore.CYAN}{'=' * 80}{Style.RESET_ALL}")
    
    # Step 1: Create repository
    clone_url, success = create_github_repo(GITHUB_TOKEN, REPO_NAME, DESCRIPTION, IS_PRIVATE)
    if not success or not clone_url:
        print(f"\n{Fore.RED}✗ Failed to create repository{Style.RESET_ALL}")
        return 1
    
    # Step 2: Configure git remote
    if not configure_git_remote(GITHUB_TOKEN, clone_url):
        print(f"\n{Fore.RED}✗ Failed to configure git remote{Style.RESET_ALL}")
        return 1
    
    # Step 3: Push code
    if not push_to_github():
        print(f"\n{Fore.RED}✗ Failed to push code{Style.RESET_ALL}")
        return 1
    
    # Success summary
    print(f"\n{Fore.CYAN}{'=' * 80}{Style.RESET_ALL}")
    print(f"{Fore.CYAN}Success!{Style.RESET_ALL}")
    print(f"{Fore.CYAN}{'=' * 80}{Style.RESET_ALL}\n")
    
    print(f"{Fore.GREEN}✓ Repository created and code pushed{Style.RESET_ALL}")
    print(f"\n{Fore.WHITE}Repository URL:{Style.RESET_ALL}")
    print(f"  https://github.com/alexeikh/{REPO_NAME}")
    
    print(f"\n{Fore.WHITE}Next Steps:{Style.RESET_ALL}")
    print(f"  1. Open: https://github.com/alexeikh/{REPO_NAME}")
    print(f"  2. Verify files are there")
    print(f"  3. Connect Fabric workspace to GitHub (see docs/GITHUB_SETUP.md)")
    print()
    
    return 0


if __name__ == "__main__":
    sys.exit(main())
