import os
import sys
import json
from pathlib import Path
from argparse import ArgumentParser

from openai import OpenAI
import praw
import requests
from bs4 import BeautifulSoup
from dotenv import load_dotenv
from pydantic import BaseModel, ValidationError, Field
from tqdm import tqdm

# Load environment variables
load_dotenv()

# Configuration
REDDIT_CLIENT_ID = os.getenv("REDDIT_CLIENT_ID")
REDDIT_CLIENT_SECRET = os.getenv("REDDIT_CLIENT_SECRET")
REDDIT_USER_AGENT = os.getenv("REDDIT_USER_AGENT")
OPENAI_API_KEY = os.getenv("OPENAI_API_KEY")

# Validate keys
if not all([REDDIT_CLIENT_ID, REDDIT_CLIENT_SECRET, REDDIT_USER_AGENT, OPENAI_API_KEY]):
    raise RuntimeError("Missing one or more API keys in .env")

# Initialize Reddit client
try:
    reddit = praw.Reddit(
        client_id=REDDIT_CLIENT_ID,
        client_secret=REDDIT_CLIENT_SECRET,
        user_agent=REDDIT_USER_AGENT
    )
    use_praw = True
except Exception:
    use_praw = False

# Event-driven emitter
class EventEmitter:
    def __init__(self):
        self._events = {}

    def on(self, event: str, handler):
        self._events.setdefault(event, []).append(handler)

    def emit(self, event: str, *args, **kwargs):
        for handler in self._events.get(event, []):
            handler(*args, **kwargs)

# Pydantic models
class Trait(BaseModel):
    description: str
    evidence: list[str]

class Persona(BaseModel):
    username: str
    name: str | None = None
    age: str | None = None
    occupation: str | None = None
    status: str | None = None
    location: str | None = None
    tier: str | None = None
    archetype: str | None = None
    behaviour: list[str]
    frustrations: list[str]
    motivations: dict[str, int]
    goals: list[str]
    personality: dict[str, int]
    citations: dict[str, list[str]] = Field(default_factory=dict)

class PersonaGenerator(EventEmitter):
    def scrape(self, username: str) -> list[str]:
        texts: list[str] = []
        if use_praw:
            user = reddit.redditor(username)
            for post in tqdm(user.submissions.new(limit=100), desc="Scraping Posts"):
                texts.append(post.title + "\n" + (post.selftext or ""))
            for comment in tqdm(user.comments.new(limit=100), desc="Scraping Comments"):
                texts.append(comment.body)
        else:
            base = f"https://www.reddit.com/user/{username}"
            headers = {"User-Agent": REDDIT_USER_AGENT}
            for section in ["submitted", "comments"]:
                resp = requests.get(f"{base}/{section}/", headers=headers)
                soup = BeautifulSoup(resp.text, "html.parser")
                for elt in soup.select(".md p"):
                    texts.append(elt.get_text())
        self.emit('scrape_complete', texts)
        return texts

    def generate(self, username: str, snippets: list[str]) -> Persona:
        client= OpenAI(api_key=OPENAI_API_KEY)
        snippets = snippets[:50]
        prompt = (
            "Analyze the following Reddit user content and output a JSON with the following keys:"
            " name, age, occupation, status (married/single), location, tier, archetype,"
            " behaviour (list, also include any habits too), frustrations (list), motivations (dict of metric 0-10),"
            " goals (list), personality (dict of metric 0-10), citations (dict mapping each section to list of source URLs)."
            " Format the JSON exactly.\nContent:\n" + "---\n".join(snippets)
        )
        try:
            resp = client.chat.completions.create(
                model="gpt-4",
                messages=[
                    {"role": "system", "content": "You are an expert at user research and persona building."},
                    {"role": "user", "content": prompt}
                ],
                temperature=0.7
            )
            data = json.loads(resp.choices[0].message.content)
            persona = Persona(username=username, **data)
            self.emit('persona_generated', persona)
            return persona
        except (json.JSONDecodeError, ValidationError) as e:
            print("❌ Error parsing persona JSON:", e)
            sys.exit(1)

    def save(self, persona: Persona, out_dir: Path) -> Path:
        out_dir.mkdir(exist_ok=True)
        txt_path = out_dir / f"{persona.username}_persona.txt"
        with open(txt_path, "w", encoding="utf-8") as f:
            f.write(f"User Persona for {persona.username}\n")
            f.write("="*40 + "\n")
            # Base info
            for field in ["name","age","occupation","status","location","tier","archetype"]:
                val = getattr(persona, field)
                if val:
                    f.write(f"{field.capitalize()}: {val}\n")
            f.write("\n")
            # Sections
            def write_section(title, items):
                f.write(f"{title.upper()}:\n")
                if isinstance(items, dict):
                    for k, v in items.items():
                        f.write(f"- {k}: {v}\n")
                else:
                    for itm in items:
                        f.write(f"- {itm}\n")
                # Citations
                cites = persona.citations.get(title.lower(), [])
                for url in cites:
                    f.write(f"    (Source: {url})\n")
                f.write("\n")
            write_section("Behaviour & Habits", persona.behaviour)
            write_section("Frustrations", persona.frustrations)
            write_section("Motivations", persona.motivations)
            write_section("Goals & Needs", persona.goals)
            write_section("Personality", persona.personality)
        json_path = out_dir / f"{persona.username}_persona.json"
        with open(json_path, "w", encoding="utf-8") as jf:
            json.dump(persona.model_dump(), jf, indent=2)
        self.emit('save_complete', txt_path)
        return txt_path

# CLI entry point

def main():
    parser = ArgumentParser(description="Reddit Persona Generator CLI")
    parser.add_argument('profile', help='Reddit username or full profile URL')
    parser.add_argument('--output', '-o', default='output', help='Output directory')
    args = parser.parse_args()

    username = args.profile.rstrip('/').split('/')[-1]
    gen = PersonaGenerator()

    gen.on('scrape_complete', lambda s: print(f"✅ Scraped {len(s)} snippets."))
    gen.on('persona_generated', lambda p: print(f"✅ Generated persona for {p.username}"))
    gen.on('save_complete', lambda path: print(f"✅ Saved persona at {path}"))

    snippets = gen.scrape(username)
    persona = gen.generate(username, snippets)
    gen.save(persona, Path(args.output))

if __name__ == '__main__':
    main()
