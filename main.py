"""
Daily entry point. Run this once a day (via cron / GitHub Actions / Task
Scheduler) to collect new NHL news and optionally generate a curated digest.

Usage:
    python main.py
"""

from datetime import datetime

import db
import curate
import generate_page
from collector import collect_new_articles


def main():
    print(f"=== NHL news collection run: {datetime.now().isoformat()} ===")

    db.init_db()

    with db.get_conn() as conn:
        new_count = collect_new_articles(conn, db.insert_article)

        if curate.is_available():
            today_articles = db.get_articles_since(
                conn, datetime.now().strftime("%Y-%m-%d 00:00:00")
            )
            if today_articles:
                print(f"  Generating digest from {len(today_articles)} article(s)...")
                digest_text = curate.build_digest(today_articles)
                if digest_text:
                    db.save_digest(
                        conn, curate.todays_date_str(), digest_text, len(today_articles)
                    )
                    print("  Digest saved.\n")
                    print("--- Today's digest ---")
                    print(digest_text)
            else:
                print("  No new articles today -- skipping digest.")
        else:
            print("  ANTHROPIC_API_KEY not set -- skipping curated digest "
                  "(raw articles were still collected).")

    print(f"=== Done. {new_count} new article(s) added. ===")

    generate_page.generate()


if __name__ == "__main__":
    main()