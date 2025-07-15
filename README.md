# 🧠 Reddit Persona Generator
A Python tool to generate structured user personas by analyzing a Reddit user's public activity using OpenAI's GPT-4.

## 🚀 Overview
This script:
1. Accepts a Reddit profile URL or username.
2. Scrapes the user's latest posts and comments (via Reddit API).
3. Uses GPT-4 to build a structured user persona with behavior, motivations, frustrations, personality, and more.
4. Saves the output as a readable .txt and structured .json file.

## 📦 Features
- 🔍 Fetches up to 100 posts and 100 comments using PRAW or fallback web scraping
- 🧠 Uses OpenAI GPT-4 to infer:

  - Name, Age, Location, Occupation, Status
  - Behavior & Habits
  - Frustrations
  - Motivations (0–10 scale)
  - Goals & Needs
  - Personality traits (0–10 scale)
  - Citations (source comments/posts for each section)

- 💾 Outputs both .txt and .json formats

## 🔧 Tech Stack
- Python
- PRAW (Reddit API)
- OpenAI GPT-4
- BeautifulSoup (fallback scraping)
- python-dotenv
- pydantic
- tqdm

## 🛠️ Setup
1. Clone this repo:
```
git clone https://github.com/your-username/reddit-persona-generator.git
cd reddit-persona-generator
```
3. Install dependencies
`pip install -r requirements.txt`
4. Configure .env
Create a .env file in the root directory with:
```
REDDIT_CLIENT_ID=your_reddit_client_id
REDDIT_CLIENT_SECRET=your_reddit_client_secret
REDDIT_USER_AGENT=your_app_name/0.1 by your_username
OPENAI_API_KEY=your_openai_api_key
```

## ▶️ Usage
Run the script from terminal:
`python main.py <reddit_username_or_url>`

Examples
```
python main.py kojied
python main.py https://www.reddit.com/user/Hungry-Move-6603/
python main.py kojied --output personas/
```

## 📁 Output Structure
Each run will generate:
```
output/
├── kojied_persona.txt     # Human-readable format
├── kojied_persona.json    # Machine-readable structured JSON
```

## 📌 Notes
- Only the latest 50 snippets are sent to OpenAI to stay within token limits.
- Traits are merged into Behaviour & Habits
- LLM is instructed to cite sources from scraped posts/comments per section.
