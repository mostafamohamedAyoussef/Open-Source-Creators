import os
import time
import requests
import json
from datetime import datetime
from dotenv import load_dotenv

# Load environment variables from ~/.env if it exists (for local testing)
env_path = os.path.expanduser('~/.env')
if os.path.exists(env_path):
    load_dotenv(env_path, override=True)

GITHUB_TOKEN = os.getenv('GITHUB_TOKEN')
if not GITHUB_TOKEN:
    print("Error: GITHUB_TOKEN is missing. Please provide it via environment variable.")
    exit(1)

HEADERS = {
    'Authorization': f'token {GITHUB_TOKEN}',
    'Accept': 'application/vnd.github.v3+json'
}

# Define the massive search list
SEARCH_QUERIES = {
    "AI Image Generation": [
        "topic:text-to-image", "topic:image-generation", "topic:stable-diffusion",
        "topic:stable-diffusion-ui", "topic:controlnet", "topic:image-restoration",
        "topic:image-inpainting", "topic:background-removal", "topic:upscaling",
        "topic:style-transfer"
    ],
    "AI Video Generation": [
        "topic:text-to-video", "topic:video-generation", "topic:video-diffusion",
        "topic:frame-interpolation", "topic:lip-sync", "topic:talking-head",
        "topic:virtual-human"
    ],
    "Video Editing": [
        "topic:video-editing", "topic:non-linear-editor", "topic:motion-graphics",
        "topic:color-grading", "topic:rotoscoping", "topic:subtitle-generator"
    ],
    "AI Writing": [
        "topic:ai-writing", "topic:text-generation", "topic:copywriting",
        "topic:summarization", "topic:paraphrasing", "topic:grammar-checker"
    ],
    "Marketing Automation": [
        "topic:marketing-automation", "topic:social-media-automation",
        "topic:seo", "topic:newsletter-generator", "topic:landing-page-builder"
    ],
    "Design Tools": [
        "topic:design-tool", "topic:whiteboard", "topic:presentation-generator",
        "topic:infographic", "topic:vector-graphics"
    ],
    "Audio": [
        "topic:text-to-speech", "topic:tts", "topic:voice-cloning",
        "topic:music-generation", "topic:speech-enhancement", "topic:audio-editing",
        "topic:noise-reduction"
    ],
    "Content Automation": [
        "topic:workflow-automation", "topic:ai-agent", "topic:multi-agent-system",
        "topic:n8n", "topic:langchain"
    ],
    "Research": [
        "topic:web-scraping", "topic:retrieval-augmented-generation", "topic:rag",
        "topic:semantic-search", "topic:knowledge-base", "topic:vector-database"
    ],
    "3D Content": [
        "topic:text-to-3d", "topic:gaussian-splatting", "topic:nerf",
        "topic:mesh-generation", "topic:blender-addon"
    ],
    "Creative Coding": [
        "topic:generative-art", "topic:creative-coding", "topic:procedural-generation",
        "topic:shader"
    ],
    "Productivity": [
        "topic:knowledge-management", "topic:markdown-publishing",
        "topic:meeting-summarization"
    ]
}

def search_github(query, sort="stars", order="desc", limit=100):
    all_items = []
    page = 1
    
    while True:
        url = f"https://api.github.com/search/repositories?q={query}&sort={sort}&order={order}&per_page=100&page={page}"
        print(f"Fetching: {query} (page {page})")
        
        response = requests.get(url, headers=HEADERS)
        
        if response.status_code == 403:
            reset_time = int(response.headers.get('X-RateLimit-Reset', 0))
            sleep_time = max(reset_time - time.time(), 0) + 1
            print(f"Rate limited. Sleeping for {sleep_time} seconds...")
            time.sleep(sleep_time)
            continue
            
        if response.status_code != 200:
            print(f"Error {response.status_code}: {response.text}")
            break
            
        data = response.json()
        items = data.get('items', [])
        all_items.extend(items)
        
        if len(items) < 100 or len(all_items) >= limit:
            break
            
        page += 1
        time.sleep(2) # be nice to the API
        
    return all_items[:limit]

def main():
    collected_repos = {}
    
    for category, queries in SEARCH_QUERIES.items():
        print(f"--- Processing Category: {category} ---")
        for query in queries:
            items = search_github(f"{query} stars:>10", limit=150)
            
            for item in items:
                repo_id = item['id']
                if repo_id not in collected_repos:
                    collected_repos[repo_id] = {
                        "name": item['name'],
                        "full_name": item['full_name'],
                        "html_url": item['html_url'],
                        "description": item['description'],
                        "stargazers_count": item['stargazers_count'],
                        "forks_count": item['forks_count'],
                        "language": item['language'],
                        "updated_at": item['updated_at'],
                        "created_at": item['created_at'],
                        "license": item['license']['name'] if item.get('license') else "None",
                        "topics": item['topics'],
                        "categories": [category]
                    }
                else:
                    if category not in collected_repos[repo_id]["categories"]:
                        collected_repos[repo_id]["categories"].append(category)
                        
    # Save the raw data
    data_dir = os.path.join(os.path.dirname(os.path.dirname(__file__)), "data")
    os.makedirs(data_dir, exist_ok=True)
    output_path = os.path.join(data_dir, "raw_repos.json")
    with open(output_path, 'w', encoding='utf-8') as f:
        json.dump(list(collected_repos.values()), f, indent=2, ensure_ascii=False)
        
    print(f"Successfully collected {len(collected_repos)} unique repositories.")
    print(f"Saved to {output_path}")

if __name__ == "__main__":
    main()
