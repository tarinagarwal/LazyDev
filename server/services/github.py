import httpx
import subprocess
import os
import shutil
import tempfile
from config import get_settings

settings = get_settings()


async def repo_exists(repo_name: str) -> bool:
    """Check if repository exists on GitHub"""
    async with httpx.AsyncClient() as client:
        response = await client.get(
            f"https://api.github.com/repos/{repo_name}",
            headers={
                "Authorization": f"token {settings.github_token}",
                "Accept": "application/vnd.github.v3+json"
            }
        )
        return response.status_code == 200


async def create_repo(repo_name: str) -> bool:
    """Create a new repository on GitHub"""
    # Extract just the repo name (not username/repo)
    just_repo = repo_name.split("/")[-1]
    
    async with httpx.AsyncClient() as client:
        response = await client.post(
            "https://api.github.com/user/repos",
            headers={
                "Authorization": f"token {settings.github_token}",
                "Accept": "application/vnd.github.v3+json"
            },
            json={
                "name": just_repo,
                "private": False,
                "auto_init": False
            }
        )
        return response.status_code == 201


def run_git_command(args: list, cwd: str) -> tuple:
    """Run a git command and return (success, output)"""
    try:
        result = subprocess.run(
            ["git"] + args,
            cwd=cwd,
            capture_output=True,
            text=True,
            timeout=120
        )
        if result.returncode == 0:
            return True, result.stdout
        return False, result.stderr
    except subprocess.TimeoutExpired:
        return False, "Command timed out"
    except Exception as e:
        return False, str(e)


def setup_git_repo(work_dir: str, repo_name: str) -> tuple:
    """Initialize and configure git repo"""
    
    success, output = run_git_command(["init"], work_dir)
    if not success:
        return False, f"Failed to init: {output}"
    
  
    run_git_command(["config", "user.email", f"{settings.github_username}@users.noreply.github.com"], work_dir)
    run_git_command(["config", "user.name", settings.github_username], work_dir)
    
   
    remote_url = f"https://{settings.github_username}:{settings.github_token}@github.com/{repo_name}.git"
    success, output = run_git_command(["remote", "add", "origin", remote_url], work_dir)
    if not success and "already exists" not in output:
        return False, f"Failed to add remote: {output}"
    
    return True, "Git repo configured"


def commit_files(work_dir: str, files: list, message: str) -> tuple:
    """Stage and commit specific files"""
  
    existing_files = []
    for f in files:
        file_path = os.path.join(work_dir, f)
        if os.path.exists(file_path):
            existing_files.append(f)
    
    if not existing_files:
        return False, "No files found to commit"
    
  
    for f in existing_files:
        success, output = run_git_command(["add", f], work_dir)
        if not success:
            return False, f"Failed to stage {f}: {output}"
    
    # Commit
    success, output = run_git_command(["commit", "-m", message], work_dir)
    if not success:
        return False, f"Failed to commit: {output}"
    
    return True, f"Committed {len(existing_files)} files"


def push_to_remote(work_dir: str, branch: str = "main") -> tuple:
    """Push commits to remote with full edge case handling"""
    
    # Set git config to avoid interactive prompts
    run_git_command(["config", "pull.rebase", "true"], work_dir)
    run_git_command(["config", "rebase.autoStash", "true"], work_dir)
    
    # Fetch remote
    run_git_command(["fetch", "origin"], work_dir)
    
    # Check if remote branch exists
    remote_exists, _ = run_git_command(["rev-parse", "--verify", f"origin/{branch}"], work_dir)
    
    if remote_exists:
        # Remote branch exists - need to sync
        # First, try simple rebase
        success, output = run_git_command(["rebase", f"origin/{branch}"], work_dir)
        
        if not success:
            # Rebase failed - abort and try merge
            run_git_command(["rebase", "--abort"], work_dir)
            
            # Try merge with auto-commit
            success, output = run_git_command(["merge", f"origin/{branch}", "--no-edit", "-X", "theirs"], work_dir)
            
            if not success:
                # Merge also failed - force reset and cherry-pick our commit
                run_git_command(["merge", "--abort"], work_dir)
                
                # Get our commit hash
                _, our_commit = run_git_command(["rev-parse", "HEAD"], work_dir)
                our_commit = our_commit.strip() if our_commit else ""
                
                # Reset to remote and cherry-pick
                run_git_command(["reset", "--hard", f"origin/{branch}"], work_dir)
                
                if our_commit:
                    success, output = run_git_command(["cherry-pick", our_commit], work_dir)
                    if not success:
                        # Cherry-pick failed - accept all changes
                        run_git_command(["cherry-pick", "--abort"], work_dir)
                        # Just force our version
                        run_git_command(["reset", "--hard", our_commit], work_dir)
    
    # Ensure we're on the right branch
    run_git_command(["branch", "-M", branch], work_dir)
    
    # Push with force-with-lease (safer than force)
    success, output = run_git_command(["push", "-u", "origin", branch, "--force-with-lease"], work_dir)
    if success:
        return True, output
    
    # If force-with-lease fails, try regular push
    success, output = run_git_command(["push", "-u", "origin", branch], work_dir)
    if success:
        return True, output
    
    # Last resort - force push (user's own repo anyway)
    success, output = run_git_command(["push", "-u", "origin", branch, "--force"], work_dir)
    if success:
        return True, output
    
    return False, output
