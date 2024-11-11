import os
import json
import math
import re
from pydriller import Repository
from javalang.parse import parse as javalang_parse
from datetime import datetime, timedelta
import logging
import javalang
import subprocess
from concurrent.futures import ThreadPoolExecutor

repo_list_file = "project_links.txt"
clone_dir = "cloned_repos"
output_dir = "rminer-outputs"
os.makedirs(clone_dir, exist_ok=True)
os.makedirs(output_dir, exist_ok=True)

logging.basicConfig(
    filename='logs/output.log',
    filemode='a',
    level=logging.DEBUG,
    format='%(asctime)s - %(levelname)s - %(message)s'
)


def calculate_cyclomatic_complexity(method):
    decision_points = 0
    for node in method.body:
        if isinstance(node, (javalang.tree.IfStatement,
                             javalang.tree.ForStatement,
                             javalang.tree.WhileStatement,
                             javalang.tree.SwitchStatement)):
            decision_points += 1
    return decision_points + 1

def calculate_metrics(repo_path, commit_sha, file_commits, commit, modified_file):
    metrics_data = []
    tree = javalang_parse(modified_file.source_code)
    metrics = {
        "commit hash": commit.hash,
        "file": modified_file.filename,
        "SEXP": 0, "CBO": 0, "WMC": 0, "RFC": 0, "ELOC": 0,
        "NOM": 0, "NOPM": 0, "DIT": 1, "NOC": 0, "NOF": 0,
        "NOSF": 0, "NOPF": 0, "NOSM": 0, "NOSI": 0, "HsLCOM": 0,
        "C3": 0, "ComRead": 0, "ND": 0, "NS": 0, "AGE": 0,
        "FIX": False, "NUC": 0, "CEXP": 0, "REXP": 0, "OEXP": 0, "EXP": 0
    }

    for path, node in tree:
        if isinstance(node, javalang.tree.ClassDeclaration):
            metrics["NOM"] = len([m for m in node.methods])
            metrics["NOPM"] = len([m for m in node.methods if m.modifiers == 'public'])
            metrics["NOF"] = len(node.fields)
            metrics["NOSF"] = len([f for f in node.fields if 'static' in f.modifiers])
            metrics["NOPF"] = len([f for f in node.fields if 'public' in f.modifiers])
            metrics["WMC"] = sum(calculate_cyclomatic_complexity(m) for m in node.methods if m.body)
            metrics["ELOC"] = len([line for line in modified_file.source_code.splitlines() if line.strip()])

    authors = set(c.author.name for c in file_commits)
    metrics["NDEV"] = len(authors)
    directories = {os.path.dirname(mod.filename) for mod in commit.modified_files}
    metrics["ND"] = len(directories)
    subsystems = {os.path.dirname(mod.filename).split(os.sep)[0] for mod in commit.modified_files}
    metrics["NS"] = len(subsystems)

    time_deltas = [(commit.committer_date - file_commit.committer_date).days
                   for file_commit in file_commits if file_commit.hash != commit.hash]
    metrics["AGE"] = sum(time_deltas) / len(time_deltas) if time_deltas else 0

    metrics["FIX"] = bool(re.search(r'\b[A-Za-z]+-\d+\b', commit.msg))

    file_commits_count = sum(
        1 for c in file_commits if any(mod.filename == modified_file.filename for mod in c.modified_files))
    metrics["NUC"] = file_commits_count
    metrics["CEXP"] = sum(1 for c in file_commits if c.author.name == commit.author.name)
    one_month_ago = datetime.now(commit.committer_date.tzinfo) - timedelta(days=30)
    metrics["REXP"] = len([c for c in file_commits if
                           c.author.name == commit.author.name and c.committer_date > one_month_ago])
    contributions = {author: sum(mod.added_lines for c in file_commits for mod in c.modified_files if
                                 mod.filename == modified_file.filename and c.author.name == author)
                     for author in authors}
    highest_contributor = max(contributions, key=contributions.get, default=None)
    project_total_additions = sum(
        mod.added_lines for c in Repository(repo_path).traverse_commits() for mod in c.modified_files)
    highest_contributor_additions = contributions[highest_contributor] if highest_contributor else 0
    metrics["OEXP"] = (
                                  highest_contributor_additions / project_total_additions) * 100 if project_total_additions > 0 else 0

    author_experience = [sum(1 for mod in c.modified_files if mod.filename == modified_file.filename)
                         for c in Repository(repo_path).traverse_commits() for author in authors]
    exp_product = math.prod(author_experience) if author_experience else 0
    metrics["EXP"] = exp_product ** (1 / len(author_experience)) if author_experience else 0

    metrics_data.append(metrics)
    return metrics_data

def process_repository(repo_url):
    repo_name = repo_url.split("/")[-1].replace(".git", "")
    repo_path = os.path.join(clone_dir, repo_name)
    repo_output_dir = os.path.join(output_dir, repo_name)  # Create repository-specific output directory
    os.makedirs(repo_output_dir, exist_ok=True)

    output_file = os.path.join(repo_output_dir, f"{repo_name}_refactorings.json")  # Input refactorings file path
    metrics_file = os.path.join(repo_output_dir, f"{repo_name}_metrics.json")  # Output metrics file path

    try:
        with open(output_file, "r", encoding="utf-8") as json_file:
            refactoring_data = json.load(json_file)
            metrics_results = []

            file_commits = {filename: list(Repository(repo_path).traverse_commits())
                            for filename in set(mod.filename for commit in refactoring_data.get("commits", [])
                                                for modified_file in commit.get('modified_files', []))}

            for refactoring in refactoring_data.get("commits", []):
                commit_sha = refactoring.get("sha1")
                if commit_sha:
                    try:
                        commit = next(c for c in Repository(repo_path).traverse_commits() if c.hash == commit_sha)
                    except StopIteration:
                        logging.error(f"Commit {commit_sha} not found in {repo_name}")
                        continue

                    for modified_file in commit.modified_files:
                        if modified_file.filename.endswith('.java') and modified_file.source_code:
                            try:
                                metrics_results.extend(calculate_metrics(repo_path, commit_sha,
                                                                         file_commits.get(modified_file.filename, []),
                                                                         commit, modified_file))
                            except Exception as e:
                                logging.error(
                                    f"Error calculating metrics for file {modified_file.filename} in commit {commit_sha}: {e}")

            with open(metrics_file, "w", encoding='utf-8') as metrics_file_out:
                json.dump(metrics_results, metrics_file_out, indent=4)

    except Exception as e:
        logging.error(f"Error processing {repo_name}: {e}")
        try:
            subprocess.run(['git', 'diff-tree', '4ed92aa9043ac803615443afe5b908dfa48174df',
                            'd683906ad137944d9294d17f8289024fc63b84e5', '-r', '--abbrev=40', '--full-index', '-M', '-p',
                            '--no-ext-diff', '--no-color'], cwd=repo_path, check=True)
        except subprocess.CalledProcessError as ex:
            logging.error(f"Git diff-tree command failed for {repo_name} with error: {ex}")
        try:
            subprocess.run(['git', 'cat-file', '--batch-check'], cwd=repo_path, check=True)
        except subprocess.CalledProcessError as ex:
            logging.error(f"Git cat-file command failed for {repo_name} with error: {ex}")


with open(repo_list_file, "r") as file:
    repo_urls = [line.strip() for line in file if line.strip()]

with ThreadPoolExecutor() as executor:
    executor.map(process_repository, repo_urls)

print("Metrics data has been saved.")
