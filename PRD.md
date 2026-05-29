# 📄 PRODUCT REQUIREMENTS DOCUMENT (PRD)

## Chronicles Production v4.1

---

## 1. PRODUCT OVERVIEW

**Chronicles Production** is an AI-native film studio. Users provide a seed idea, select a culture (10 options), timeline (10 options), and theme (10 options). The system generates a complete 1-1.5 minute short film with AI-generated video, images, narration, music, and a Netflix-style viewing experience.

**Tagline**: *1,000 worlds. Infinite stories. One click.*

---

## 2. PROBLEM STATEMENT

Creating short films requires: writers, concept artists, cinematographers, editors, sound designers, and weeks of work. For $0. Chronicles Production automates the entire film production pipeline using AI agent swarms — from story conception to final MP4 render.

---

## 3. TARGET USERS

| Persona | Need | Use Case |
|---------|------|----------|
| **Writer/Creator** | Visualize their story ideas | Generate a 1-min film from a seed idea to pitch or share |
| **Educator** | Culturally-authentic historical narratives | Show students what Bronze Age Egypt looked and felt like |
| **AI Developer** | Study multi-agent film production | Fork the codebase, study agent swarm patterns |
| **Casual User** | Cool AI-generated films | "Make me a Viking betrayal story set in the AI Hegemony" |

---

## 4. USER STORIES

### Core Flow
- As a user, I want to type a seed idea, pick culture/timeline/theme, and get a complete short film
- As a user, I want to see progress as my film is being generated
- As a user, I want to watch my film in a Netflix-style viewer with chapters and character galleries
- As a user, I want to browse all my generated films in a library
- As a user, I want to share my film with a link

### Power User
- As a developer, I want to see the agent lineage ("Behind the Scenes") to understand how my film was made
- As a creator, I want to toggle narration on/off
- As a creator, I want to jump to specific scenes/chapters

---

## 5. FUNCTIONAL REQUIREMENTS

### FR1: Film Generation
- User provides: seed_idea (10-200 chars), culture, timeline, theme
- System generates: complete MP4 film (1-1.5 min, 1080p)
- Progress streamed via SSE
- Idempotent: same request returns cached film
- Free tier: max 10 generations/day

### FR2: Story Generation
- 600-900 word narrative in literary prose style
- Culturally-authentic characters with signature items
- Scene breakdown (6-12 scenes)
- Stereotype detection and flagging

### FR3: Visual Bible
- Color palette per culture×timeline×theme
- Character bibles (appearance, costume, signature items)
- Location descriptions with materials and lighting
- Camera language (angles, movement, focal length)

### FR4: Image Generation
- 4-6 character portraits (different poses, emotional states)
- 6-10 scene setting keyframes
- Deterministic seeding (same inputs = same images)
- Images serve as reference for video generation

### FR5: Video Generation
- 8-12 video clips (5-8 seconds each)
- Character consistency via reference images + signature items
- Per-scene camera movement and lighting
- Quality control validation per clip
- Degrades gracefully: failed clips → static image + Ken Burns

### FR6: Post-Production
- Video clip concatenation with transitions
- Narration audio (Amazon Polly, SSML prosody, configurable)
- Background music (Suno/Udio, per emotional beat)
- Ambient sound effects per scene
- Color grading (consistent LUT)
- Title card + credits overlay
- MP4 encoding (H.264, 1080p, AAC audio)

### FR7: Netflix-Style Viewer
- Cinematic title card entry animation
- Chapter/scene selector (click to jump to scene)
- Interactive timeline scrubber
- Character gallery with portraits and bios
- Story text panel (scrolls in sync with video)
- Narration on/off toggle
- Music on/off toggle
- Fullscreen cinema mode
- Agent lineage "Behind the Scenes" panel
- Share/copy link

### FR8: Library
- Grid view of completed films
- Thumbnail, title, duration, culture/timeline/theme tags
- Search and filter
- Sort by date

### FR9: Configuration
- Culture: 15 curated options (see DEEP_DIVE_PLAN.md for full list)
- Timeline: 15 options spanning paleolithic through interplanetary frontier
- Theme: 15 options across core, love, power, psychological, and identity categories
- Narration: on/off
- Video duration target: configurable
- Force-blending: automatic counterfactual bridge for distant culture×timeline combos

---

## 6. NON-FUNCTIONAL REQUIREMENTS

### NFR1: Performance
- Film generation: < 3 minutes end-to-end
- Story generation: < 40 seconds
- Image generation: < 30 seconds (parallel)
- Video generation: < 60 seconds (parallel)
- Post-production: < 30 seconds
- Cache hit (same story): < 2 seconds (return existing film)

### NFR2: Reliability
- Graceful degradation on ANY API failure
- No single point of failure in pipeline
- Retry with exponential backoff (max 2)
- Agent timeout (30s default)

### NFR3: Cost (Free Tier)
- LLM costs: $0.00 (free tier APIs)
- Image costs: $0.00 (Pollinations free)
- Video costs: $0.00 (free tiers)
- Audio costs: $0.00 (Polly free tier)
- Infrastructure: $0.00 (Render free + Supabase free)

### NFR4: Determinism
- Same story_hash → same output, always
- Deterministic seeding throughout pipeline
- Cached results never change

### NFR5: Cultural Safety
- Stereotype trap injection into Planner
- Post-generation pattern scan
- Flagged content never cached
- Human-readable flagging for review

### NFR6: Observability
- Structured JSON logging (structlog)
- Agent lineage tracing (every agent invocation)
- OpenTelemetry spans for pipeline phases
- Prometheus metrics (generation count, latency, cache hit rate)

### NFR7: Security
- No hardcoded secrets
- Environment variable configuration
- Input sanitization (prompt injection guard)
- CORS restricted to configured origins
- Rate limiting per IP

---

## 7. CONSTRAINTS

| Constraint | Value | Reason |
|-----------|-------|--------|
| Max story words | 900 | LLM context window + video scene count |
| Max scenes | 12 | Video API rate limits + assembly complexity |
| Max video duration | 96s (12 × 8s) | Free tier API limits |
| Max concurrent LLM calls | 8 | OpenRouter free tier rate limits |
| Max concurrent video calls | 4 | Video API free tier rate limits |
| Free tier generations/day | 10 | Prevent abuse |
| Max seed_idea length | 200 chars | Prompt budget |

---

## 8. SUCCESS METRICS

| Metric | Target | Measurement |
|--------|--------|-------------|
| Film generation time | < 3 min | Prometheus histogram |
| Cache hit rate | > 30% | Redis stats |
| Video QC pass rate | > 80% | Agent lineage table |
| Character consistency | > 90% signature items visible | Video QC agent |
| Stereotype-free rate | > 95% | Scan pass rate |
| User satisfaction | TBD | Post-film feedback |
| Cost per film | $0.00 | Agent lineage cost tracking |

---

## 9. OUT OF SCOPE (v4)

- User authentication (use Supabase Auth later)
- Paid tiers (free only for MVP)
- Real-time collaborative editing
- Multi-language support (English only initially)
- Mobile apps (web only)
- Custom culture/timeline/theme creation by users
- Live-action video generation (AI-generated only)
- 4K output (1080p only)
- Subtitle generation
- Social features (comments, likes)

---

## 10. FUTURE ROADMAP

| Version | Feature | Effort |
|---------|---------|--------|
| v4.1 | User auth + profiles | Medium |
| v4.2 | Paid tiers (more generations, longer films) | Medium |
| v4.3 | Custom culture/timeline creation | Hard |
| v4.4 | Multi-language stories | Medium |
| v5.0 | Interactive films (choose your own adventure) | Hard |
| v5.1 | Voice cloning for narration | Medium |
| v5.2 | 4K output | Medium |
| v6.0 | Real-time multi-agent debugging dashboard | Hard |
