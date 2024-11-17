import os
import json
import matplotlib.pyplot as plt
import seaborn as sns
import pandas as pd

# Define output directory for visualizations
visualizations_dir = "visualizations"
os.makedirs(visualizations_dir, exist_ok=True)

# Define the metrics to plot
metrics_to_plot = [
    'SEXP', 'CBO', 'WMC', 'RFC', 'ELOC', 'NOM', 'NOPM', 'DIT', 'NOC', 'NOF', 'NOSF',
    'NOPF', 'NOSM', 'NOSI', 'HsLCOM', 'C3', 'ComRead', 'ND', 'NS', 'AGE', 'FIX', 'NUC',
    'CEXP', 'REXP', 'OEXP', 'EXP'
]

def plot_metrics_evolution(metrics_file, repo_name):
    # Load metrics data
    with open(metrics_file, "r", encoding='utf-8') as file:
        metrics_data = json.load(file)

    # Convert metrics data to DataFrame for easier manipulation
    df = pd.DataFrame(metrics_data)

    # Ensure 'commit hash' is a string for better plotting
    df['commit hash'] = df['commit hash'].astype(str)

    # Sort data by the order of commits, if not already ordered (commits are usually ordered in time)
    df.sort_values(by='commit hash', ascending=True, inplace=True)

    # Remove rows with NaN values in relevant columns
    df.dropna(subset=['commit hash'] + metrics_to_plot, inplace=True)

    # Create a folder for each repository under the visualizations directory
    repo_visualizations_dir = os.path.join(visualizations_dir, repo_name)
    os.makedirs(repo_visualizations_dir, exist_ok=True)

    # Plot for each metric
    for metric in metrics_to_plot:
        plt.figure(figsize=(10, 6))

        # Plot the metric's evolution over the commit order (index-based)
        sns.lineplot(data=df, x=df.index, y=metric, marker='o', label=metric)

        # Customize the plot
        plt.title(f"Evolution of {metric} for {repo_name}")
        plt.xlabel('Commit Order')
        plt.ylabel(f'{metric} Value')
        plt.xticks(rotation=45)
        plt.tight_layout()

        # Save the plot as an image in the repository's folder
        plot_filename = os.path.join(repo_visualizations_dir, f"{repo_name}_{metric}_evolution.png")
        plt.savefig(plot_filename)
        plt.close()

    print(f"Visualizations for {repo_name} saved to {repo_visualizations_dir}")

# Iterate through repositories and generate visualizations
with open("project_links4.txt", "r") as file:
    repo_urls = [line.strip() for line in file if line.strip()]

for repo_url in repo_urls:
    repo_name = repo_url.split("/")[-1].replace(".git", "")
    metrics_file = os.path.join("rminer-outputs", f"{repo_name}_metrics.json")

    try:
        if os.path.exists(metrics_file):
            plot_metrics_evolution(metrics_file, repo_name)
        else:
            print(f"Metrics file for {repo_name} not found.")
    except Exception as e:
        print(f"Error processing {repo_name}: {e}")

print("Visualization process completed.")
