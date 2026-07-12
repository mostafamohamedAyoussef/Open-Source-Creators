import json
import os
import math
from datetime import datetime, timezone

# Commercial mapping dictionary
COMMERCIAL_MAPPING = {
    "Runway": ["runway", "video-generation", "text-to-video", "video-diffusion"],
    "Higgsfield": ["higgsfield", "video-generation", "cinematic-generation"],
    "Canva": ["canva", "design-tool", "graphic-design"],
    "Adobe Premiere": ["premiere", "video-editing", "non-linear-editor"],
    "CapCut": ["capcut", "video-editing", "tiktok-automation", "shorts"],
    "Midjourney": ["midjourney", "text-to-image", "stable-diffusion", "flux"],
    "Photoshop": ["photoshop", "image-editing", "inpainting", "outpainting", "photopea"],
    "Jasper": ["jasper", "copywriting", "ai-writing"],
    "Copy.ai": ["copy.ai", "copywriting", "ai-writing"],
    "ChatGPT": ["chatgpt", "conversational-ai", "chat-ui", "open-webui"],
    "ElevenLabs": ["elevenlabs", "text-to-speech", "tts", "voice-cloning"],
    "Descript": ["descript", "video-editing", "transcription", "podcast-editing"],
    "Notion": ["notion", "knowledge-management", "productivity"],
    "Figma": ["figma", "design-tool", "ui-design", "ux-design", "penpot"]
}

def calculate_score(repo):
    stars = repo.get("stargazers_count", 0)
    score = min(math.log10(max(stars, 1)) * 1.5, 6.0) # Up to 6 points from stars
    
    # Activity score
    now = datetime.now(timezone.utc)
    updated = datetime.fromisoformat(repo.get("updated_at").replace('Z', '+00:00'))
    days_since_update = (now - updated).days
    
    if days_since_update <= 30:
        score += 2.0
    elif days_since_update <= 90:
        score += 1.5
    elif days_since_update <= 180:
        score += 1.0
    elif days_since_update <= 365:
        score += 0.5
        
    # Documentation / Description
    if repo.get("description"):
        score += 1.0
        
    # Topics/Tags presence
    if len(repo.get("topics", [])) > 0:
        score += 1.0
        
    return round(min(score, 10.0), 1)

def map_commercial_alternative(repo):
    topics = set(repo.get("topics", []))
    desc = str(repo.get("description", "")).lower()
    
    alternatives = []
    for commercial, keywords in COMMERCIAL_MAPPING.items():
        if any(kw in topics for kw in keywords) or any(kw in desc for kw in keywords):
            alternatives.append(commercial)
            
    return alternatives

def process_repos():
    data_dir = os.path.join(os.path.dirname(os.path.dirname(__file__)), "data")
    raw_path = os.path.join(data_dir, "raw_repos.json")
    if not os.path.exists(raw_path):
        print("raw_repos.json not found")
        return
        
    with open(raw_path, 'r', encoding='utf-8') as f:
        repos = json.load(f)
        
    processed = []
    for repo in repos:
        repo['score'] = calculate_score(repo)
        repo['commercial_alternatives'] = map_commercial_alternative(repo)
        
        # Tags processing
        all_tags = set(repo.get("topics", []))
        all_tags.update([cat.lower() for cat in repo.get("categories", [])])
        repo['tags'] = list(all_tags)
        
        # Derived fields
        now = datetime.now(timezone.utc)
        created = datetime.fromisoformat(repo.get("created_at").replace('Z', '+00:00'))
        age_days = (now - created).days
        
        repo['is_hidden_gem'] = (
            repo.get('stargazers_count', 0) < 5000 and 
            repo['score'] >= 7.5
        )
        
        repo['is_emerging'] = (
            age_days <= 730 and # 24 months
            repo['stargazers_count'] > 1000 and
            repo['score'] >= 8.0
        )
        
        processed.append(repo)
        
    # Sort by score then stars
    processed.sort(key=lambda x: (x['score'], x['stargazers_count']), reverse=True)
    
    out_path = os.path.join(data_dir, "processed_repos.json")
    with open(out_path, 'w', encoding='utf-8') as f:
        json.dump(processed, f, indent=2, ensure_ascii=False)
        
    print(f"Processed {len(processed)} repositories.")
    print(f"Saved to {out_path}")

if __name__ == "__main__":
    process_repos()
