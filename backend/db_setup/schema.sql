-- Chronicles Story Engine - SQLite Database Schema
-- Run once to create all tables for fallback content storage
-- Usage: sqlite3 chronicles.db < schema.sql

-- Enable foreign keys
PRAGMA foreign_keys = ON;

-- ============================================================================
-- CULTURES TABLE (30 entries)
-- Stores civilization intelligence: fallback text, stereotype traps, redirects
-- ============================================================================
CREATE TABLE IF NOT EXISTS cultures (
    id TEXT PRIMARY KEY,           -- slug: "roman", "aztec", "soviet_union"
    name TEXT NOT NULL,            -- display name: "Roman Empire"
    description TEXT,              -- enum comment: stereotype risks, redirect suggestions, era dates
    fallback_text TEXT,            -- 4 paragraphs, 350-500 words (HUMAN-WRITTEN)
    traps TEXT,                    -- JSON array: ["gladiators", "human sacrifice", "horned helmets"]
    redirects TEXT,                -- JSON array: ["focus on merchant class", "show legal system"]
    created_at TEXT DEFAULT CURRENT_TIMESTAMP,
    updated_at TEXT DEFAULT CURRENT_TIMESTAMP
);

-- ============================================================================
-- TIMELINES TABLE (30 entries)
-- Stores timeline intelligence: period context, POV traps, story conditions
-- ============================================================================
CREATE TABLE IF NOT EXISTS timelines (
    id TEXT PRIMARY KEY,           -- slug: "medieval", "ai_hegemony", "entropy_wars"
    name TEXT NOT NULL,            -- display name: "High Medieval"
    description TEXT,              -- era dates, what this period was globally
    fallback_text TEXT,            -- 4 paragraphs, 300-450 words (HUMAN-WRITTEN)
    era_dates TEXT,                -- "500–1450 CE" or "2080–2120 CE"
    created_at TEXT DEFAULT CURRENT_TIMESTAMP,
    updated_at TEXT DEFAULT CURRENT_TIMESTAMP
);

-- ============================================================================
-- THEMES TABLE (34 entries)
-- Stores theme intelligence: structural demands, craft notes, risks
-- ============================================================================
CREATE TABLE IF NOT EXISTS themes (
    id TEXT PRIMARY KEY,           -- slug: "betrayal", "hubris", "survival"
    name TEXT NOT NULL,            -- display name: "Betrayal"
    description TEXT,              -- what this theme structurally demands, climax requirements
    craft_notes TEXT,              -- 3 paragraphs, 200-300 words (HUMAN-WRITTEN)
    created_at TEXT DEFAULT CURRENT_TIMESTAMP,
    updated_at TEXT DEFAULT CURRENT_TIMESTAMP
);

-- ============================================================================
-- STORY BIBLES TABLE (auto-populated by generation)
-- Persistent record of every generated story with full provenance
-- ============================================================================
CREATE TABLE IF NOT EXISTS story_bibles (
    hash TEXT PRIMARY KEY,         -- SHA-256 of culture|timeline|theme|seed_idea
    culture_id TEXT NOT NULL,
    timeline_id TEXT NOT NULL,
    theme_id TEXT NOT NULL,
    seed_idea TEXT NOT NULL,
    blueprint_json TEXT,           -- full Planner output (auto-filled after Planner completes)
    story_json TEXT,               -- full Writer output (auto-filled after Writer completes)
    context_pkg_json TEXT,         -- what both agents received (auto-filled, for provenance)
    stereotypes_flagged TEXT,      -- JSON array of flagged phrases (auto-filled)
    word_count INTEGER,            -- story word count (auto-filled)
    images_json TEXT,              -- image URLs from image_agent (auto-filled)
    audio_hash TEXT,               -- audio file reference from audio task (auto-filled)
    created_at TEXT DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (culture_id) REFERENCES cultures(id),
    FOREIGN KEY (timeline_id) REFERENCES timelines(id),
    FOREIGN KEY (theme_id) REFERENCES themes(id)
);

-- ============================================================================
-- INDEXES (for fast lookups by agents)
-- ============================================================================
CREATE INDEX IF NOT EXISTS idx_story_bibles_culture ON story_bibles(culture_id);
CREATE INDEX IF NOT EXISTS idx_story_bibles_timeline ON story_bibles(timeline_id);
CREATE INDEX IF NOT EXISTS idx_story_bibles_theme ON story_bibles(theme_id);
CREATE INDEX IF NOT EXISTS idx_story_bibles_hash ON story_bibles(hash);

-- ============================================================================
-- VIEWS (for debugging and inspection)
-- ============================================================================

-- View: Count entries per table
CREATE VIEW IF NOT EXISTS content_stats AS
SELECT 
    'cultures' AS table_name, 
    COUNT(*) AS entry_count 
FROM cultures
UNION ALL
SELECT 'timelines', COUNT(*) FROM timelines
UNION ALL
SELECT 'themes', COUNT(*) FROM themes
UNION ALL
SELECT 'story_bibles', COUNT(*) FROM story_bibles;

-- View: Stories with stereotypes flagged (for quality audit)
CREATE VIEW IF NOT EXISTS flagged_stories AS
SELECT 
    hash,
    culture_id,
    timeline_id,
    theme_id,
    stereotypes_flagged,
    created_at
FROM story_bibles
WHERE stereotypes_flagged IS NOT NULL 
  AND stereotypes_flagged != '[]'
ORDER BY created_at DESC;

-- ============================================================================
-- TRIGGERS (auto-update timestamps)
-- ============================================================================

CREATE TRIGGER IF NOT EXISTS update_cultures_timestamp 
AFTER UPDATE ON cultures
BEGIN
    UPDATE cultures SET updated_at = CURRENT_TIMESTAMP WHERE id = NEW.id;
END;

CREATE TRIGGER IF NOT EXISTS update_timelines_timestamp 
AFTER UPDATE ON timelines
BEGIN
    UPDATE timelines SET updated_at = CURRENT_TIMESTAMP WHERE id = NEW.id;
END;

CREATE TRIGGER IF NOT EXISTS update_themes_timestamp 
AFTER UPDATE ON themes
BEGIN
    UPDATE themes SET updated_at = CURRENT_TIMESTAMP WHERE id = NEW.id;
END;

-- ============================================================================
-- INITIAL DATA (existing fallback content from tools.py)
-- These are placeholders - replace with your full rewritten content
-- ============================================================================

-- Example culture entry (Viking - abbreviated, replace with full 4 paragraphs)
INSERT OR REPLACE INTO cultures (id, name, description, fallback_text, traps, redirects)
VALUES (
    'viking',
    'Viking Age Scandinavia',
    '~793–1,100 CE. Stereotype risk: horned helmets and pure raider image. Redirect: trader networks, settler communities, skald poets, thing assembly democratic system, women''s legal property rights.',
    'The Vikings (793–1,100 CE) were not just raiders with horned helmets (which they never wore). They operated trade networks reaching Baghdad, with Arabic coins found in Scandinavian graves. Settler communities in Iceland and Greenland developed sophisticated legal systems — the Icelandic Althing was one of the world''s oldest parliaments. Skald poets composed complex verse celebrating both warfare and diplomacy. Women could own property, initiate divorce, and run farms while men were away. The dominant stereotype to avoid is the pure raider image that ignores traders, settlers, and poets. Instead, focus on the thing assembly democratic system where free men voted on laws, women managing estates and legal disputes, merchants trading furs and amber for silk and silver, and the gradual Christianization that transformed Norse cosmology. This was a culture where reputation mattered more than wealth, where poetry was as valued as battle prowess, and where women held legal rights unknown in contemporary Christian Europe.',
    '["horned helmets", "pure raider", "barbarian tribe", "rape and pillage"]',
    '["focus on trade networks reaching Baghdad", "show thing assembly democratic system", "women''s legal property rights", "skald poets", "settler communities in Iceland/Greenland"]'
);

-- Note: Add remaining 21 existing cultures from tools.py FALLBACK_CONTEXT here
-- Then add 8 new cultures (Soviet Union, Nazi Germany, Mongol Empire, etc.)

-- Note: Add 30 timelines (10 historical + 10 modern/future + 10 cosmic)

-- Note: Add 34 themes with craft notes

-- ============================================================================
-- END OF SCHEMA
-- ============================================================================
