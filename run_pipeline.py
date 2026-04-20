"""
Run the full SML pipeline:
  1. Scrape Reddit
  2. Preprocess
  3. Analyze (LLM)
  4. Build vector store
"""
import sys
import os
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from scraper.reddit_scraper import run_scraper
from preprocessing.preprocessor import run_preprocessor
from analysis.analyzer import run_analyzer
from rag.vector_store import build_vector_store
from export_excel import run_export

if __name__ == "__main__":
    print("=" * 50)
    print("Step 1: Scraping Reddit...")
    print("=" * 50)
    run_scraper("data/raw_posts.json")

    print("\n" + "=" * 50)
    print("Step 2: Preprocessing...")
    print("=" * 50)
    run_preprocessor("data/raw_posts.json", "data/processed_posts.json")

    print("\n" + "=" * 50)
    print("Step 3: LLM Analysis...")
    print("=" * 50)
    run_analyzer("data/processed_posts.json", "data/analyzed_posts.json")

    print("\n" + "=" * 50)
    print("Step 4: Building Vector Store...")
    print("=" * 50)
    build_vector_store("data/analyzed_posts.json")

    print("\n" + "=" * 50)
    print("Step 5: Exporting Excel Report...")
    print("=" * 50)
    run_export()

    print("\n✅ Pipeline complete. Run the dashboard with:")
    print("   streamlit run dashboard/app.py")
