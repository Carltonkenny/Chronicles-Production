#!/usr/bin/env python3
"""
Initialize Chronicles Story Engine SQLite Database

Usage:
    python init_db.py

This creates the chronicles.db file with all tables ready for content insertion.
Run this once before writing any fallback content.
"""

import sqlite3
from pathlib import Path

# Database file location
DB_PATH = Path(__file__).parent / "chronicles.db"

def init_database():
    """Create database and all tables."""
    
    print(f"[INIT] Initializing database at: {DB_PATH}")
    
    # Read schema SQL
    schema_path = Path(__file__).parent / "schema.sql"
    
    if not schema_path.exists():
        print(f"❌ Error: schema.sql not found at {schema_path}")
        return False
    
    # Connect to database (creates file if it doesn't exist)
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    
    # Read and execute schema
    with open(schema_path, 'r', encoding='utf-8') as f:
        schema_sql = f.read()
    
    cursor.executescript(schema_sql)
    
    # Verify tables were created
    cursor.execute("""
        SELECT name FROM sqlite_master 
        WHERE type='table' 
        ORDER BY name
    """)
    
    tables = cursor.fetchall()
    
    print(f"[OK] Database created successfully!")
    print(f"\n[TABLES] Tables created:")
    for table in tables:
        print(f"   - {table[0]}")
    
    # Show content stats
    cursor.execute("SELECT * FROM content_stats")
    stats = cursor.fetchall()
    
    print(f"\n[CONTENT] Content status:")
    print(f"\n[NEXT STEPS]")
    print(f"   1. Open docs/CONTENT_WRITING_TEMPLATE.md")
    print(f"   2. Write your first fallback entry")
    print(f"   3. Insert using SQL INSERT or DB Browser for SQLite")
    print(f"   4. Run: python test_content.py (to verify insertion)")
    
    conn.commit()
    conn.close()
    
    return True


def show_existing_content():
    """Display what content already exists in the database."""
    
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    
    print("\n[EXISTING CONTENT]")
    
    # Cultures
    cursor.execute("SELECT id, name FROM cultures ORDER BY id")
    cultures = cursor.fetchall()
    print(f"\n   Cultures ({len(cultures)}):")
    for c in cultures:
        print(f"      - {c[0]} ({c[1]})")
    
    # Timelines
    cursor.execute("SELECT id, name FROM timelines ORDER BY id")
    timelines = cursor.fetchall()
    print(f"\n   Timelines ({len(timelines)}):")
    for t in timelines:
        print(f"      - {t[0]} ({t[1]})")
    
    # Themes
    cursor.execute("SELECT id, name FROM themes ORDER BY id")
    themes = cursor.fetchall()
    print(f"\n   Themes ({len(themes)}):")
    for th in themes:
        print(f"      - {th[0]} ({th[1]})")
    
    # Story bibles
    cursor.execute("SELECT COUNT(*) FROM story_bibles")
    count = cursor.fetchone()[0]
    print(f"\n   Story Bibles: {count} entries")
    
    conn.close()


if __name__ == "__main__":
    import sys
    
    if len(sys.argv) > 1 and sys.argv[1] == "--show":
        # Just show existing content
        if DB_PATH.exists():
            show_existing_content()
        else:
            print("[ERROR] Database not found. Run 'python init_db.py' first.")
    else:
        # Initialize database
        success = init_database()
        
        if success and DB_PATH.exists():
            show_existing_content()
