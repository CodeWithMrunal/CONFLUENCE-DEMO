import requests
import os
import chromadb
from sentence_transformers import SentenceTransformer
from dotenv import load_dotenv
load_dotenv()

# GitHub repo details
GITHUB_TOKEN = os.getenv("API_KEY")
REPO_OWNER = "CodeWithMrunal"
REPO_NAME = "CONFLUENCE-DEMO"

# Load Sentence Transformer Model
model = SentenceTransformer("all-MiniLM-L6-v2")

# Initialize ChromaDB client (data will persist in "conflict_db" folder)
chroma_client = chromadb.PersistentClient(path="conflict_db")
collection = chroma_client.get_or_create_collection(name="conflicts")

# -------------------------------
# 📌 Fetch Merged PRs from GitHub
# -------------------------------
def get_merged_prs():
    url = f"https://api.github.com/repos/{REPO_OWNER}/{REPO_NAME}/pulls?state=closed&per_page=50"
    headers = {"Authorization": f"token {GITHUB_TOKEN}"}

    response = requests.get(url, headers=headers)

    # ✅ Check if response is valid JSON
    try:
        prs = response.json()
    except requests.exceptions.JSONDecodeError:
        print("❌ ERROR: GitHub API response is not valid JSON!")
        print("🔍 Response:", response.text)  # Debugging
        return []

    # ✅ Check if response contains an error message
    if isinstance(prs, dict) and "message" in prs:
        print(f"❌ ERROR: GitHub API responded with an error: {prs['message']}")
        return []

    merged_prs = []

    for pr in prs:
        if isinstance(pr, dict) and pr.get("merged_at"):  # Ensure it's a dictionary
            merged_prs.append({
                "pr_number": pr["number"],
                "title": pr["title"],
                "body": pr["body"],  # PR description
                "merged_at": pr["merged_at"],
                "merge_commit": pr["merge_commit_sha"]
            })

    print(f"✅ Fetched {len(merged_prs)} merged PRs from GitHub!")
    return merged_prs


# -------------------------------
# 📌 Get File Changes for Each PR
# -------------------------------
def get_pr_diff(pr_number):
    url = f"https://api.github.com/repos/{REPO_OWNER}/{REPO_NAME}/pulls/{pr_number}/files"
    headers = {"Authorization": f"token {GITHUB_TOKEN}"}

    response = requests.get(url, headers=headers)
    files = response.json()

    file_changes = []
    
    for file in files:
        file_changes.append({
            "filename": file["filename"],
            "status": file["status"],  # modified, added, removed
            "patch": file.get("patch", ""),  # Code diff
        })

    return file_changes

# -------------------------------
# 📌 Store Conflict Resolutions in ChromaDB
# -------------------------------
def add_to_chroma():
    merged_prs = get_merged_prs()  # Get past PRs

    for pr in merged_prs:
        for change in get_pr_diff(pr["pr_number"]):
            text = f"File: {change['filename']}\nDiff: {change['patch']}"
            embedding = model.encode(text).tolist()  # Convert to vector
            
            # Store in ChromaDB
            collection.add(embeddings=[embedding], ids=[str(pr["pr_number"])])

    print(f"✅ Added {len(merged_prs)} merged PRs to ChromaDB!")

# -------------------------------
# 📌 Search for Similar Conflicts in ChromaDB
# -------------------------------
def search_conflicts(query_text):
    query_embedding = model.encode(query_text).tolist()
    results = collection.query(query_embeddings=[query_embedding], n_results=3)
    
    if results["ids"]:
        print("🔍 Found similar past conflicts!")
        for i, match_id in enumerate(results["ids"][0]):
            print(f"{i+1}. PR #{match_id}")
        return results["ids"][0]  # Return matching PR numbers
    
    print("❌ No similar conflicts found.")
    return []

# -------------------------------
# 📌 Run Initial Data Ingestion
# -------------------------------
if __name__ == "__main__":
    add_to_chroma()  # Store past conflicts
