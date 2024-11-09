import subprocess
import os
import json
from pydriller import Repository

refminer_path = "/home/user1/grp404/RM-fat.jar"
repo_list_file = "project_links2.txt"
clone_dir = "cloned_repos"
output_dir = "rminer-outputs"
os.makedirs(clone_dir, exist_ok=True)

subprocess.run(["git", "config", "--global", "http.postBuffer", "5242880000"])

# Read repository links
with open(repo_list_file, "r") as file:
    repo_urls = [line.strip() for line in file if line.strip()]

for repo_url in repo_urls:
    repo_name = repo_url.split("/")[-1].replace(".git", "")
    repo_path = os.path.join(clone_dir, repo_name)

    repo_output_dir = os.path.join(output_dir, repo_name)
    os.makedirs(repo_output_dir, exist_ok=True)

    output_file = os.path.join(repo_output_dir, f"{repo_name}_refactorings.json")
    commit_message_file = os.path.join(repo_output_dir, f"{repo_name}_commit_messages.json")
    diff_output_file = os.path.join(repo_output_dir, f"{repo_name}_commit_diffs.json")

    if not os.path.exists(repo_path):
        result = subprocess.run(["git", "clone", repo_url, repo_path])
        if result.returncode != 0:
            print(f"Error cloning {repo_name}: {result.stderr}")
            continue

    command = ["java", "-jar", refminer_path, "-a", repo_path, "-json", output_file]
    subprocess.run(command)

    try:
        with open(output_file, "r", encoding="utf-8") as json_file:
            refactoring_data = json.load(json_file)
            commit_messages = []
            diffs = []

            commit_shas = [refactoring.get("sha1") for refactoring in refactoring_data.get("commits", [])]

            commit_message_cmd = ["git", "-C", repo_path, "log", "--format=%H %B"] + commit_shas
            commit_message_result = subprocess.run(commit_message_cmd, capture_output=True, text=True, encoding='utf-8')

            if commit_message_result.returncode == 0:
                commit_messages_dict = {}
                for line in commit_message_result.stdout.strip().split("\n"):
                    parts = line.split(" ", 1)
                    if len(parts) == 2:
                        sha, message = parts
                        commit_messages_dict[sha] = message.strip()
                    else:
                        print(f"Skipping malformed line: {line}")

                for commit_sha in commit_shas:

                    commit_messages.append({
                        "commit hash": commit_sha,
                        "commit message": commit_messages_dict.get(commit_sha, "Unknown commit message"),
                    })

                    # Fetch diff data using Repository
                    for commit in Repository(repo_path).traverse_commits():
                        if commit.hash == commit_sha:
                            for modified_file in commit.modified_files:
                                diff_data = {
                                    "commit hash": commit.hash,
                                    "previous commit hash": commit.parents[0] if commit.parents else None,
                                    "diff stats": {
                                        "file_path": modified_file.filename,
                                        "additions": modified_file.added_lines,
                                        "deletions": modified_file.deleted_lines
                                    },
                                    "diff content": modified_file.diff
                                }
                                diffs.append(diff_data)
                            break

            # Save commit messages to JSON file
            with open(commit_message_file, "w", encoding='utf-8') as cm_file:
                json.dump(commit_messages, cm_file, indent=4)

            # Save diff data to JSON file
            with open(diff_output_file, "w", encoding='utf-8') as diff_file:
                json.dump(diffs, diff_file, indent=4)

    except Exception as e:
        print(f"Error processing {repo_name}: {e}")

print("Refactoring, commit message, and commit diff data have been saved.")
