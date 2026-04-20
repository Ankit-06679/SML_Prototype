import os
import json
import sys
from openai import OpenAI
from dotenv import load_dotenv
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from config import OPENROUTER_MODEL, OPENROUTER_BASE_URL

load_dotenv()

client = OpenAI(
    api_key=os.getenv("OPENROUTER_API_KEY"),
    base_url=OPENROUTER_BASE_URL,
)

ANALYSIS_PROMPT = """You are a pharmaceutical social media analyst specializing in asthma biologics (especially Mepolizumab/Nucala).

Analyze the following Reddit post and return a JSON object with these fields:
- sentiment: one of "Positive", "Negative", "Neutral"
- sentiment_score: float between -1.0 (very negative) and 1.0 (very positive)
- emotion: one of "Hope", "Frustration", "Fear", "Satisfaction", "Confusion", "Neutral"
- stakeholder: one of "Patients", "Physicians", "Pharmacists", "Caregivers", "Payers", "Patient Advocacy Groups"
- themes: list of relevant themes from [Patient Journey, Treatment Efficacy, Safety, Cost/Access, Biosimilar Perception, Biologic Perception, Quality of Life, Adherence, Disease Management, Insurance/Reimbursement, Administration, Biomarkers]
- drugs_mentioned: list of drug names mentioned
- key_entities: list of important named entities (conditions, drugs, procedures, organizations)
- summary: 1-2 sentence summary of the post's main point
- quote: most representative verbatim quote (max 50 words) from the text

Text:
\"\"\"
{text}
\"\"\"

Return ONLY valid JSON, no explanation."""

def analyze_post(text: str) -> dict:
    try:
        response = client.chat.completions.create(
            model=OPENROUTER_MODEL,
            messages=[
                {"role": "user", "content": ANALYSIS_PROMPT.format(text=text[:3000])}
            ],
            temperature=0.1,
            response_format={"type": "json_object"},
        )
        result = json.loads(response.choices[0].message.content)
        return result
    except Exception as e:
        print(f"  [WARN] Analysis failed: {e}")
        return {
            "sentiment": "Neutral",
            "sentiment_score": 0.0,
            "emotion": "Neutral",
            "stakeholder": "Patients",
            "themes": [],
            "drugs_mentioned": [],
            "key_entities": [],
            "summary": "",
            "quote": "",
        }

def run_analyzer(
    input_path: str = "data/processed_posts.json",
    output_path: str = "data/analyzed_posts.json"
):
    with open(input_path, "r", encoding="utf-8") as f:
        posts = json.load(f)

    analyzed = []
    for i, post in enumerate(posts):
        print(f"Analyzing {i+1}/{len(posts)}: {post['id']}...")
        analysis = analyze_post(post["raw_text"])
        analyzed.append({**post, **analysis})

    with open(output_path, "w", encoding="utf-8") as f:
        json.dump(analyzed, f, indent=2, ensure_ascii=False)

    print(f"\nAnalysis complete. {len(analyzed)} posts -> {output_path}")
    return analyzed

if __name__ == "__main__":
    run_analyzer()
