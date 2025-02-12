from flask import Flask, request, jsonify
import os
from dotenv import load_dotenv
import requests

load_dotenv()
app = Flask(__name__)

GITHUB_TOKEN =os.getenv("API_KEY")
REPO_OWNER = "CodeWithMrunal"
REPO_NAME = "CONFLUENCE-DEMO"

# Webhook to receive GitHub events
@app.route("/webhook", methods=["POST"])
def github_webhook():
    data = request.json

    # Check if the event is a PR creation event
    if data.get("action") in ["opened", "synchronize"]:
        pr_number = data["pull_request"]["number"]
        base_branch = data["pull_request"]["base"]["ref"]
        head_branch = data["pull_request"]["head"]["ref"]

        print(f"PR #{pr_number} detected: {head_branch} → {base_branch}")

        # Fetch diff and check for conflicts
        analyze_pr_conflicts(pr_number)

    return jsonify({"message": "Webhook received"}), 200


# Function to analyze PR conflicts
import time

def analyze_pr_conflicts(pr_number):
    url = f"https://api.github.com/repos/{REPO_OWNER}/{REPO_NAME}/pulls/{pr_number}"
    headers = {"Authorization": f"token {GITHUB_TOKEN}"}

    mergeable = None
    mergeable_state = None

    # Wait up to 15 seconds for GitHub to determine mergeability
    for i in range(7):  # Retry 7 times (up to 14 seconds)
        response = requests.get(url, headers=headers)
        pr_data = response.json()
        mergeable = pr_data.get("mergeable")
        mergeable_state = pr_data.get("mergeable_state")

        if mergeable is not None:  # GitHub finished processing
            break

        print(f"Waiting for GitHub to determine mergeability... (Attempt {i+1}/7)")
        time.sleep(2)

    print(f"GitHub API response: mergeable={mergeable}, mergeable_state={mergeable_state}")

    if mergeable is False or mergeable_state in ["dirty", "unknown"]:
        print(f"PR #{pr_number} has merge conflicts!")
        get_conflicting_files(pr_number)
    else:
        print(f"PR #{pr_number} is mergeable!")




# Function to get conflicting files
def get_conflicting_files(pr_number):
    url = f"https://api.github.com/repos/{REPO_OWNER}/{REPO_NAME}/pulls/{pr_number}/files"
    headers = {"Authorization": f"token {GITHUB_TOKEN}"}

    response = requests.get(url, headers=headers)
    files = response.json()

    conflicting_files = [
        file["filename"] for file in files if file["status"] in ["modified", "renamed", "removed"]
    ]

    if conflicting_files:
        print(f"Conflicting files: {conflicting_files}")
    else:
        print("No conflicts detected.")


if __name__ == "__main__":
    app.run(port=5000, debug=True)
