"""Helix Education Center V2 — Real Interactive Learning System.

Complete flow:
1. Type any topic/question → Search authoritative web sources
2. Display ADHD-friendly interactive lesson with citations & source links
3. Generate quiz from source content (LLM)
4. Evaluate answers with LLM against topic + source → Verdict + Score
5. Save → Records lesson + metacognitive memory as log events
6. All events persisted to event store
"""

from __future__ import annotations

import json
import uuid
from http.server import BaseHTTPRequestHandler, HTTPServer
from urllib.parse import parse_qs, urlparse

from cognitive_agent.agent_client import OllamaAgentClient
from cognitive_engine.cognitive_service import CognitiveService
from content_engine import ContentService
from delivery_engine import FeedbackService
from grounding_engine.grounding_client import WebGroundingClient
from grounding_engine.grounding_service import GroundingService
from learning_service import LearningService
from quiz_engine import QuizService
from state_core.event_models import (
    JourneyEntryRecordedEvent,
)
from state_core.event_store import EventStore, SealedAnswerKeyStore, StoreConfig
from state_core.llm_evaluation import LLMEvaluationService
from state_core.scoring_engine import AnswerKey

# ═══════════════════════════════════════════════════════════════════════
# CONFIGURATION
# ═══════════════════════════════════════════════════════════════════════

OLLAMA_MODEL = "lfm2.5:8b"  # Change to your model
OLLAMA_NUM_CTX = 8192
GROUNDING_MAX_CHUNKS = 6
QUIZ_ITEMS_PER_TOPIC = 5

# ADHD-friendly UI constants
CHUNK_MAX_CHARS = 800
PROGRESS_BAR_WIDTH = 100


# ═══════════════════════════════════════════════════════════════════════
# HTML TEMPLATE — ADHD-Friendly, Interactive, Clean
# ═══════════════════════════════════════════════════════════════════════

_HTML = """<!DOCTYPE html>
<html lang="en">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>{title} — Helix Education V2</title>
<style>
:root {{
  --primary: #2563eb;
  --primary-hover: #1d4ed8;
  --success: #16a34a;
  --success-hover: #15803d;
  --warning: #d97706;
  --warning-hover: #b45309;
  --danger: #dc2626;
  --danger-hover: #b91c1c;
  --bg: #f8fafc;
  --card: #ffffff;
  --text: #1e293b;
  --muted: #64748b;
  --border: #e2e8f0;
  --focus: #dbeafe;
  --accent: #8b5cf6;
}}
* {{ box-sizing: border-box; margin: 0; padding: 0; }}
body {{
  font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, system-ui, sans-serif;
  background: var(--bg);
  color: var(--text);
  line-height: 1.7;
  font-size: 1rem;
}}
.container {{ max-width: 900px; margin: 0 auto; padding: 1.5rem; }}

/* Header & Navigation */
.header {{
  display: flex; justify-content: space-between; align-items: center;
  margin-bottom: 1.5rem; padding-bottom: 1rem; border-bottom: 2px solid var(--border);
}}
.header h1 {{ color: var(--primary); font-size: 1.5rem; font-weight: 700; }}
.nav {{ display: flex; gap: 0.5rem; flex-wrap: wrap; }}
.nav a {{
  color: var(--primary); text-decoration: none; font-weight: 500;
  padding: 0.4rem 0.8rem; border-radius: 6px; font-size: 0.85rem;
  transition: background 0.15s;
}}
.nav a:hover {{ background: var(--focus); }}
.nav a.active {{ background: var(--primary); color: white; }}

/* Cards */
.card {{
  background: var(--card); border-radius: 12px; padding: 1.5rem;
  margin-bottom: 1rem; box-shadow: 0 1px 3px rgba(0,0,0,0.05);
  border: 1px solid var(--border);
}}
.card h2 {{ color: var(--text); font-size: 1.25rem; margin-bottom: 0.75rem; }}
.card h3 {{ color: var(--text); font-size: 1rem; margin: 1rem 0 0.5rem; }}

/* Forms */
label {{ display: block; margin-top: 0.75rem; font-weight: 600; color: var(--muted); font-size: 0.9rem; }}
input[type="text"], input[type="search"], textarea {{
  width: 100%; padding: 0.75rem; border: 2px solid var(--border);
  border-radius: 8px; margin-top: 0.3rem; font-size: 1rem; font-family: inherit;
  transition: border-color 0.15s, box-shadow 0.15s;
}}
input:focus, textarea:focus {{
  outline: none; border-color: var(--primary); box-shadow: 0 0 0 3px var(--focus);
}}
textarea {{ min-height: 120px; resize: vertical; }}

/* Buttons */
.btn {{
  display: inline-flex; align-items: center; gap: 0.5rem;
  background: var(--primary); color: white; border: none;
  padding: 0.75rem 1.5rem; border-radius: 8px; font-size: 0.95rem;
  font-weight: 600; cursor: pointer; text-decoration: none;
  transition: background 0.15s, transform 0.05s;
}}
.btn:hover {{ background: var(--primary-hover); }}
.btn:active {{ transform: scale(0.98); }}
.btn:disabled {{ background: var(--muted); cursor: not-allowed; }}
.btn-success {{ background: var(--success); }}
.btn-success:hover {{ background: var(--success-hover); }}
.btn-warning {{ background: var(--warning); }}
.btn-warning:hover {{ background: var(--warning-hover); }}
.btn-danger {{ background: var(--danger); }}
.btn-danger:hover {{ background: var(--danger-hover); }}
.btn-outline {{ background: transparent; color: var(--primary); border: 2px solid var(--primary); }}
.btn-outline:hover {{ background: var(--focus); }}
.btn-sm {{ padding: 0.5rem 1rem; font-size: 0.85rem; }}
.ml-1 {{ margin-left: 0.5rem; }}

/* Messages */
.msg {{
  padding: 1rem 1.25rem; border-radius: 8px; margin: 1rem 0;
  font-size: 0.95rem; border-left: 4px solid;
}}
.msg.ok {{ background: #f0fdf4; color: #166534; border-color: var(--success); }}
.msg.warn {{ background: #fffbeb; color: #92400e; border-color: var(--warning); }}
.msg.err {{ background: #fef2f2; color: #991b1b; border-color: var(--danger); }}
.msg.info {{ background: #eff6ff; color: #1e40af; border-color: var(--primary); }}

/* Progress Bar */
.progress-bar {{
  height: 8px; background: var(--border); border-radius: 4px; overflow: hidden; margin: 0.5rem 0;
}}
.progress-fill {{
  height: 100%; background: linear-gradient(90deg, var(--primary), var(--accent));
  border-radius: 4px; transition: width 0.3s ease;
}}
.progress-text {{ font-size: 0.8rem; color: var(--muted); text-align: right; }}

/* Lesson Content — ADHD Chunked */
.lesson-section {{
  background: var(--card); border: 1px solid var(--border);
  border-radius: 10px; padding: 1.25rem; margin-bottom: 1rem;
  transition: box-shadow 0.2s;
}}
.lesson-section:hover {{ box-shadow: 0 4px 12px rgba(0,0,0,0.08); }}
.lesson-section h3 {{
  display: flex; align-items: center; gap: 0.5rem;
  color: var(--primary); margin-bottom: 0.75rem; font-size: 1.1rem;
}}
.section-number {{ color: var(--muted); font-weight: 500; }}
.section-body {{ white-space: pre-wrap; font-size: 1rem; line-height: 1.8; }}
.section-body p {{ margin-bottom: 0.75rem; }}
.section-body code {{
  background: #f1f5f9; padding: 0.15rem 0.4rem; border-radius: 4px;
  font-family: "JetBrains Mono", "Fira Code", monospace; font-size: 0.9em;
}}
.section-body pre {{
  background: #1e293b; color: #e2e8f0; padding: 1rem; border-radius: 8px;
  overflow-x: auto; margin: 0.75rem 0; font-size: 0.85rem;
}}
.section-body pre code {{ background: transparent; padding: 0; }}
.citations {{ margin-top: 1rem; padding-top: 1rem; border-top: 1px solid var(--border); }}
.citation {{ font-size: 0.85rem; color: var(--muted); margin-bottom: 0.3rem; }}
.citation a {{ color: var(--primary); text-decoration: none; }}
.citation a:hover {{ text-decoration: underline; }}

/* Quiz */
.quiz-item {{
  background: var(--card); border: 1px solid var(--border);
  border-radius: 10px; padding: 1.25rem; margin-bottom: 1rem;
}}
.quiz-item h4 {{ color: var(--text); margin-bottom: 0.75rem; font-size: 1rem; }}
.quiz-meta {{ display: flex; gap: 1rem; font-size: 0.8rem; color: var(--muted); margin-bottom: 0.75rem; }}
.quiz-meta span {{ background: var(--bg); padding: 0.2rem 0.5rem; border-radius: 4px; }}
.quiz-answer textarea {{ min-height: 100px; }}

/* Verdict */
.verdict {{
  background: var(--card); border: 2px solid; border-radius: 12px;
  padding: 1.5rem; margin: 1.5rem 0;
}}
.verdict.pass {{ border-color: var(--success); background: #f0fdf4; }}
.verdict.fail {{ border-color: var(--danger); background: #fef2f2; }}
.verdict.partial {{ border-color: var(--warning); background: #fffbeb; }}
.verdict h3 {{ display: flex; align-items: center; gap: 0.5rem; margin-bottom: 1rem; }}
.verdict-score {{ font-size: 2rem; font-weight: 700; }}
.verdict.pass .verdict-score {{ color: var(--success); }}
.verdict.fail .verdict-score {{ color: var(--danger); }}
.verdict.partial .verdict-score {{ color: var(--warning); }}
.verdict-details {{ font-size: 0.95rem; line-height: 1.8; }}
.verdict-details strong {{ color: var(--text); }}

/* Source Links */
.source-link {{
  display: inline-flex; align-items: center; gap: 0.4rem;
  padding: 0.5rem 0.75rem; background: var(--bg);
  border: 1px solid var(--border); border-radius: 6px;
  margin: 0.25rem; font-size: 0.85rem; color: var(--primary);
  text-decoration: none; transition: all 0.15s;
}}
.source-link:hover {{ background: var(--focus); border-color: var(--primary); }}

/* Focus Mode Overlay */
.focus-overlay {{
  position: fixed; inset: 0; background: rgba(0,0,0,0.5);
  z-index: 1000; display: none; align-items: center; justify-content: center;
}}
.focus-overlay.active {{ display: flex; }}
.focus-modal {{
  background: var(--card); border-radius: 16px; padding: 2rem;
  max-width: 600px; width: 90%; max-height: 80vh; overflow-y: auto;
  box-shadow: 0 20px 40px rgba(0,0,0,0.2);
}}

/* Loading Spinner */
.spinner {{
  display: inline-block; width: 20px; height: 20px;
  border: 3px solid var(--border); border-top-color: var(--primary);
  border-radius: 50%; animation: spin 0.8s linear infinite;
}}
@keyframes spin {{ to {{ transform: rotate(360deg); }} }}
.loading {{ display: flex; align-items: center; justify-content: center; gap: 0.75rem; padding: 2rem; }}

/* Stats Row */
.stat-row {{ display: flex; flex-wrap: wrap; gap: 1rem; margin: 0.5rem 0; }}
.stat {{ text-align: center; min-width: 100px; flex: 1; }}
.stat-val {{ font-size: 1.5rem; font-weight: 700; color: var(--primary); }}
.stat-lbl {{ font-size: 0.7rem; color: var(--muted); text-transform: uppercase; letter-spacing: 0.05em; }}

/* Tags */
.tag {{ font-size: 0.7rem; padding: 0.2rem 0.5rem; border-radius: 9999px; font-weight: 600; }}
.tag-new {{ background: #e0e7ff; color: #3730a3; }}
.tag-active {{ background: #fef3c7; color: #92400e; }}
.tag-passed {{ background: #dcfce7; color: #166534; }}
.tag-generating {{ background: #fce7f3; color: #be185d; animation: pulse 1.5s infinite; }}
@keyframes pulse {{ 0%,100% {{ opacity: 1; }} 50% {{ opacity: 0.6; }} }}

/* Responsive */
@media (max-width: 640px) {{
  .container {{ padding: 1rem; }}
  .card {{ padding: 1rem; }}
  .header {{ flex-direction: column; gap: 1rem; align-items: flex-start; }}
  .nav {{ width: 100%; }}
  .btn {{ width: 100%; justify-content: center; }}
}}
</style>
</head>
<body>
<div class="container">
<header class="header">
  <h1>🧠 Helix Education V2</h1>
  <nav class="nav">
    <a href="/" class="{nav_home}">Dashboard</a>
    <a href="/learn" class="{nav_learn}">Learn</a>
    <a href="/profile" class="{nav_profile}">Profile</a>
    <a href="/map" class="{nav_map}">Cognitive Map</a>
    <a href="/history" class="{nav_history}">History</a>
  </nav>
</header>
{content}
</div>

<!-- Focus Mode Modal -->
<div class="focus-overlay" id="focusOverlay">
  <div class="focus-modal">
    <h2 style="margin-bottom:1rem">🎯 Focus Mode</h2>
    <div id="focusContent"></div>
    <button class="btn btn-outline" style="margin-top:1rem;width:100%" onclick="closeFocus()">Exit Focus Mode</button>
  </div>
</div>

<script>
// Focus Mode
function openFocus(html) {{
  document.getElementById('focusContent').innerHTML = html;
  document.getElementById('focusOverlay').classList.add('active');
  document.body.style.overflow = 'hidden';
}}
function closeFocus() {{
  document.getElementById('focusOverlay').classList.remove('active');
  document.body.style.overflow = '';
}}
function toggleFocus() {{
  const overlay = document.getElementById('focusOverlay');
  if (overlay.classList.contains('active')) {{
    closeFocus();
  }} else {{
    openFocus('<p style="color:var(--muted)">Click "Focus This Section" on any lesson section above to enter focus mode.</p>');
  }}
}}

// Keyboard shortcuts
document.addEventListener('keydown', (e) => {{
  if (e.key === 'Escape') closeFocus();
  if (e.key === 'f' && e.ctrlKey) {{ e.preventDefault(); toggleFocus(); }}
}});

// Auto-focus first input
document.addEventListener('DOMContentLoaded', () => {{
  const firstInput = document.querySelector('input[type="text"], input[type="search"], textarea');
  if (firstInput) firstInput.focus();
}});

// Smooth scroll for anchor links
document.querySelectorAll('a[href^="#"]').forEach(a => {{
  a.addEventListener('click', e => {{
    const target = document.querySelector(a.getAttribute('href'));
    if (target) {{ e.preventDefault(); target.scrollIntoView({{behavior:'smooth'}}); }}
  }});
}});

// Copy citation to clipboard
document.addEventListener('click', e => {{
  if (e.target.closest('.copy-citation')) {{
    e.preventDefault();
    const text = e.target.closest('.copy-citation').dataset.citation;
    navigator.clipboard.writeText(text);
    const btn = e.target.closest('.copy-citation');
    const orig = btn.textContent;
    btn.textContent = '✅ Copied!';
    setTimeout(() => btn.textContent = orig, 1500);
  }}
}});
</script>
</body>
</html>"""


# ═══════════════════════════════════════════════════════════════════════
# HELPER CLASSES
# ═══════════════════════════════════════════════════════════════════════


class SessionState:
    """In-memory session state for the web flow."""

    def __init__(self):
        self.topic: str | None = None
        self.grounding_chunks: list[dict] = []
        self.lesson_sections: list[dict] = []
        self.quiz_items: list[dict] = []
        self.current_quiz_index: int = 0
        self.quiz_answers: list[dict] = []
        self.session_id: str = str(uuid.uuid4())
        self.learning_session_id: str | None = None


# Global session store (in production, use proper session management)
SESSIONS: dict[str, SessionState] = {}


# ═══════════════════════════════════════════════════════════════════════
# REQUEST HANDLER
# ═══════════════════════════════════════════════════════════════════════


class _Handler(BaseHTTPRequestHandler):
    # Services (initialized in main())
    _l: LearningService = None
    _c: ContentService = None
    _q: QuizService = None
    _f: FeedbackService = None
    _cog: CognitiveService = None
    _grounding: GroundingService = None
    # Session cookie deferred from _get_session() to _send()
    _pending_cookie: str | None = None

    def _send(self, body: str, status: int = 200, content_type: str = "text/html; charset=utf-8"):
        self.send_response(status)
        self.send_header("Content-Type", content_type)
        if self._pending_cookie:
            self.send_header("Set-Cookie", self._pending_cookie)
            self._pending_cookie = None
        self.end_headers()
        self.wfile.write(body.encode("utf-8"))

    def _page(self, title: str, content: str, active_nav: str = ""):
        nav_classes = {k: "" for k in ["nav_home", "nav_learn", "nav_profile", "nav_map", "nav_history"]}
        if active_nav:
            nav_classes[f"nav_{active_nav}"] = "active"
        html = _HTML.format(title=title, content=content, **nav_classes)
        self._send(html)

    def _json(self, data: dict, status: int = 200):
        self._send(json.dumps(data), status, "application/json")

    def _get_session(self) -> SessionState:
        # Simple session via cookie or create new
        cookie = self.headers.get("Cookie", "")
        session_id = None
        for part in cookie.split(";"):
            if "session_id=" in part:
                session_id = part.split("=")[1].strip()
                break
        if not session_id or session_id not in SESSIONS:
            session_id = str(uuid.uuid4())
            SESSIONS[session_id] = SessionState()
        session = SESSIONS[session_id]
        # Defer cookie to _send() to avoid sending header before send_response()
        self._pending_cookie = f"session_id={session_id}; Path=/; HttpOnly; SameSite=Lax"
        return session

    def do_GET(self):
        parsed = urlparse(self.path)
        path = parsed.path.rstrip("/") or "/"
        params = parse_qs(parsed.query)

        try:
            if path == "/":
                self._page("Dashboard", self._dashboard(), "home")
            elif path == "/learn":
                self._page("Learn", self._learn(params), "learn")
            elif path == "/quiz":
                self._page("Quiz", self._quiz(params), "learn")
            elif path == "/evaluate":
                self._page("Evaluation", self._evaluate(params), "learn")
            elif path == "/save":
                self._page("Saved", self._save(params), "learn")
            elif path == "/profile":
                self._page("Profile", self._profile(), "profile")
            elif path == "/map":
                self._page("Cognitive Map", self._map(), "map")
            elif path == "/history":
                self._page("History", self._history(), "history")
            elif path == "/api/search":
                self._api_search(params)
            elif path == "/api/generate-lesson":
                self._api_generate_lesson(params)
            elif path == "/api/generate-quiz":
                self._api_generate_quiz(params)
            elif path == "/api/evaluate-answer":
                self._api_evaluate_answer(params)
            elif path == "/api/save-session":
                self._api_save_session(params)
            else:
                self._send("<h1>404</h1><p>Page not found</p>", 404)
        except Exception as e:
            self._page("Error", f'<div class="msg err"><b>Error:</b> {e}</div><a href="/" class="btn">← Dashboard</a>')

    def do_POST(self):
        length = int(self.headers.get("Content-Length", 0))
        raw = self.rfile.read(length).decode("utf-8")
        params = parse_qs(raw)
        parsed = urlparse(self.path)
        path = parsed.path.rstrip("/") or "/"

        try:
            if path == "/api/search":
                self._api_search(params)
            elif path == "/api/generate-lesson":
                self._api_generate_lesson(params)
            elif path == "/api/generate-quiz":
                self._api_generate_quiz(params)
            elif path == "/api/evaluate-answer":
                self._api_evaluate_answer(params)
            elif path == "/api/save-session":
                self._api_save_session(params)
            elif path == "/save":
                self._page("Saved", self._save(params), "learn")
            else:
                self._send("<h1>404</h1>", 404)
        except Exception as e:
            self._json({"error": str(e)}, 500)

    # ══════════════════════════════════════════════════════════════════════
    # PAGES
    # ══════════════════════════════════════════════════════════════════════

    def _dashboard(self) -> str:
        km = self._cog.build_knowledge_map()
        pending = self._cog.get_pending_recommendations()
        insights = self._cog.get_metacognitive_insights()

        insight_html = ""
        for ins in insights[-3:]:
            insight_html += (
                f'<div class="msg info"><b>{ins.title}</b><br>{ins.description}<br><i>{ins.recommendation}</i></div>'
            )

        return f"""
<div class="card">
  <div class="stat-row">
    <div class="stat"><div class="stat-val">{km.topics_studied_count}</div><div class="stat-lbl">Topics Studied</div></div>
    <div class="stat"><div class="stat-val">{km.total_quizzes_taken}</div><div class="stat-lbl">Quizzes Taken</div></div>
    <div class="stat"><div class="stat-val">{km.average_quiz_score:.0%}</div><div class="stat-lbl">Avg Score</div></div>
    <div class="stat"><div class="stat-val" style="color:{"var(--success)" if km.overall_level == "expert" else "var(--warning)" if km.overall_level == "intermediate" else "var(--muted)"}">{km.overall_level.title()}</div><div class="stat-lbl">Level</div></div>
    <div class="stat"><div class="stat-val">{len(pending)}</div><div class="stat-lbl">Pending Recs</div></div>
  </div>
</div>
{insight_html}
<div class="card">
  <h2>🚀 Start Learning</h2>
  <p style="color:var(--muted);margin-bottom:1rem">Type any topic, question, or concept you want to learn. We'll search authoritative sources, generate an interactive lesson, and create a quiz evaluated by AI.</p>
  <form id="searchForm" onsubmit="event.preventDefault(); searchTopic()">
    <input type="search" id="topicInput" name="topic" placeholder="e.g., Python async/await, React hooks, Kubernetes pods, SQL joins..." required style="font-size:1.1rem;padding:1rem">
    <button type="submit" class="btn btn-success" style="width:100%;margin-top:1rem;font-size:1.1rem;padding:1rem">Search & Generate Lesson</button>
  </form>
  <div id="searchResult"></div>
</div>

<script>
async function searchTopic() {{
  const input = document.getElementById('topicInput');
  const btn = document.querySelector('#searchForm button');
  const resultDiv = document.getElementById('searchResult');
  const topic = input.value.trim();
  if (!topic) return;

  btn.disabled = true;
  btn.innerHTML = '<span class="spinner"></span> Searching authoritative sources...';
  resultDiv.innerHTML = '';

  try {{
    const resp = await fetch('/api/search', {{
      method: 'POST',
      headers: {{'Content-Type': 'application/x-www-form-urlencoded'}},
      body: 'topic=' + encodeURIComponent(topic)
    }});
    const data = await resp.json();
    if (data.error) throw new Error(data.error);

    // Redirect to learn page with topic
    window.location.href = '/learn?topic=' + encodeURIComponent(topic);
  }} catch (e) {{
    resultDiv.innerHTML = '<div class="msg err"><b>Error:</b> ' + e.message + '</div>';
    btn.disabled = false;
    btn.textContent = 'Search & Generate Lesson';
  }}
}}
</script>"""

    def _learn(self, params: dict) -> str:
        topic = (params.get("topic") or [""])[0]
        session = self._get_session()

        if not topic:
            return '<div class="card"><h2>Learn</h2><p>No topic specified. <a href="/" class="btn">← Back to Dashboard</a></p></div>'

        # Check if we already have grounding for this topic
        if session.topic != topic or not session.grounding_chunks:
            # Need to fetch grounding and generate lesson
            return f"""
<div class="card">
  <h2>🔍 Preparing: {topic}</h2>
  <div class="loading">
    <span class="spinner"></span>
    <span>Searching authoritative sources & generating lesson...</span>
  </div>
</div>
<script>
  fetch('/api/generate-lesson', {{
    method: 'POST',
    headers: {{'Content-Type': 'application/x-www-form-urlencoded'}},
    body: 'topic=' + encodeURIComponent('{topic}')
  }}).then(r => r.json()).then(data => {{
    if (data.error) {{
      document.body.innerHTML = '<div class="msg err"><b>Error:</b> ' + data.error + '</div><a href="/" class="btn">← Dashboard</a>';
    }} else {{
      window.location.reload();
    }}
  }});
</script>"""

        # Display the lesson
        return self._render_lesson(session)

    def _render_lesson(self, session: SessionState) -> str:
        sections_html = ""
        for i, sec in enumerate(session.lesson_sections):
            citations_html = ""
            if sec.get("citations"):
                citations_html = '<div class="citations"><strong>📚 Sources:</strong>'
                for cit in sec["citations"]:
                    citations_html += f'<div class="citation"><a href="{cit["url"]}" target="_blank" rel="noopener">🔗 {cit["title"]}</a> <button class="copy-citation" data-citation="{cit["url"]}" style="margin-left:0.5rem;padding:0.1rem 0.4rem;background:var(--bg);border:1px solid var(--border);border-radius:4px;font-size:0.7rem;cursor:pointer">Copy</button></div>'
                citations_html += "</div>"

            sections_html += f"""
<div class="lesson-section" id="section-{i}">
  <h3><span class="section-number">Section {i + 1}</span> {sec["title"]}</h3>
  <div class="section-body">{sec["body"]}</div>
  {citations_html}
  <button class="btn btn-sm" onclick="openFocus(document.getElementById('section-{i}').outerHTML)">🎯 Focus This Section</button>
</div>"""

        quiz_link = ""
        if session.quiz_items:
            quiz_link = (
                '<a href="/quiz?topic='
                + session.topic
                + '" class="btn btn-success" style="margin-top:1rem">📝 Take Quiz ('
                + str(len(session.quiz_items))
                + " questions)</a>"
            )
        else:
            quiz_link = '<button class="btn btn-warning" onclick="generateQuiz(event)">📝 Generate Quiz</button>'

        return f"""
<div class="card" style="margin-bottom:1.5rem">
  <h2>{session.topic}</h2>
  <div style="display:flex;gap:1rem;flex-wrap:wrap;margin-top:0.5rem">
    <span class="tag tag-passed">✅ Lesson Ready</span>
    <span class="tag tag-new">{len(session.lesson_sections)} Sections</span>
    <span class="tag tag-new">{len(session.grounding_chunks)} Sources</span>
  </div>
</div>
{sections_html}
<div class="card" style="text-align:center">{quiz_link}</div>

<script>
function generateQuiz(evt) {{
  const btn = evt.target;
  btn.disabled = true;
  btn.innerHTML = '<span class="spinner"></span> Generating quiz with AI...';
  fetch('/api/generate-quiz', {{
    method: 'POST',
    headers: {{'Content-Type': 'application/x-www-form-urlencoded'}},
    body: 'topic=' + encodeURIComponent('{session.topic}')
  }}).then(r => r.json()).then(data => {{
    if (data.error) {{
      alert(data.error);
      btn.disabled = false;
      btn.textContent = 'Generate Quiz';
    }} else {{
      window.location.href = '/quiz?topic=' + encodeURIComponent('{session.topic}');
    }}
  }});
}}
</script>"""

    def _quiz(self, params: dict) -> str:
        topic = (params.get("topic") or [""])[0]
        session = self._get_session()

        if not topic or session.topic != topic or not session.quiz_items:
            return f'<div class="card"><h2>Quiz</h2><p>No quiz available. <a href="/learn?topic={topic}" class="btn">← Generate Lesson First</a></p></div>'

        # Check if quiz is complete
        if session.current_quiz_index >= len(session.quiz_items):
            return self._render_quiz_complete(session)

        # Show current question
        item = session.quiz_items[session.current_quiz_index]
        progress = int((session.current_quiz_index / len(session.quiz_items)) * 100)

        return f"""
<div class="card" style="margin-bottom:1.5rem">
  <h2>📝 Quiz: {topic}</h2>
  <div class="progress-bar"><div class="progress-fill" style="width:{progress}%"></div></div>
  <div class="progress-text">Question {session.current_quiz_index + 1} of {len(session.quiz_items)}</div>
</div>

<div class="quiz-item">
  <div class="quiz-meta">
    <span>{item.get("type", "conceptual").title()}</span>
    <span>{item.get("difficulty", "medium").title()}</span>
  </div>
  <h4>{item["question"]}</h4>
  <form id="answerForm" onsubmit="event.preventDefault(); submitAnswer()">
    <div class="quiz-answer">
      <label for="answer">Your Answer:</label>
      <textarea id="answer" name="answer" placeholder="Type your answer here... Explain in your own words." required></textarea>
    </div>
    <button type="submit" class="btn btn-success" style="width:100%;margin-top:1rem">Submit Answer</button>
  </form>
</div>

<script>
async function submitAnswer() {{
  const answer = document.getElementById('answer').value.trim();
  if (!answer) return;
  const btn = document.querySelector('#answerForm button');
  btn.disabled = true;
  btn.innerHTML = '<span class="spinner"></span> Evaluating with AI...';

  // Escape single quotes for JS string safety
  var _topic = {json.dumps(topic)};
  var _question = {json.dumps(item["question"])};
  var _index = {json.dumps(session.current_quiz_index)};
  const resp = await fetch('/api/evaluate-answer', {{
    method: 'POST',
    headers: {{'Content-Type': 'application/x-www-form-urlencoded'}},
    body: 'topic=' + encodeURIComponent(_topic) + '&question=' + encodeURIComponent(_question) + '&answer=' + encodeURIComponent(answer) + '&index=' + encodeURIComponent(_index)
  }});
  const data = await resp.json();
  if (data.error) throw new Error(data.error);
  window.location.href = '/evaluate?topic=' + encodeURIComponent(_topic) + '&index=' + encodeURIComponent(_index);
  }} catch (e) {{
    alert(e.message);
    btn.disabled = false;
    btn.textContent = 'Submit Answer';
  }}
</script>"""

    def _render_quiz_complete(self, session: SessionState) -> str:
        # Calculate final score
        total = len(session.quiz_answers)
        passed = sum(1 for a in session.quiz_answers if a.get("passed"))
        avg_score = sum(a.get("score", 0) for a in session.quiz_answers) / total if total > 0 else 0

        verdict_class = "pass" if avg_score >= 0.7 else "fail" if avg_score < 0.5 else "partial"
        verdict_label = "PASS" if avg_score >= 0.7 else "FAIL" if avg_score < 0.5 else "PARTIAL"

        return f"""
<div class="card">
  <h2>🎉 Quiz Complete!</h2>
  <div class="verdict {verdict_class}">
    <h3><span class="verdict-score">{avg_score:.0%}</span> — {verdict_label}</h3>
    <div class="verdict-details">
      <strong>Questions:</strong> {total} | <strong>Passed:</strong> {passed} | <strong>Average Score:</strong> {avg_score:.0%}
    </div>
  </div>
  <div class="card" style="text-align:center;margin-top:1rem">
    <form action="/save" method="post">
      <input type="hidden" name="topic" value="{session.topic}">
      <button type="submit" class="btn btn-success" style="font-size:1.1rem;padding:1rem 2rem">💾 Save Session (Lesson + Metacognitive Memory)</button>
    </form>
    <a href="/learn?topic={session.topic}" class="btn btn-outline ml-1" style="margin-top:0.5rem">← Review Lesson</a>
    <a href="/" class="btn ml-1" style="margin-top:0.5rem">← Dashboard</a>
  </div>"""

    def _evaluate(self, params: dict) -> str:
        topic = (params.get("topic") or [""])[0]
        index = int((params.get("index") or ["0"])[0])
        session = self._get_session()

        if not topic or session.topic != topic or index >= len(session.quiz_answers):
            return (
                '<div class="card"><h2>Evaluation</h2><p>No evaluation data. <a href="/quiz?topic='
                + topic
                + '" class="btn">← Back to Quiz</a></p></div>'
            )

        answer_data = session.quiz_answers[index]
        item = session.quiz_items[index]

        verdict = answer_data.get("verdict", "FAIL")
        verdict_class = "pass" if verdict == "PASS" else "fail" if verdict == "FAIL" else "partial"

        strengths_html = "".join(f"<li>{s}</li>" for s in answer_data.get("strengths", []))
        gaps_html = "".join(f"<li>{g}</li>" for g in answer_data.get("gaps", []))
        covered_html = "".join(
            f"<span class='tag tag-passed'>{c}</span> " for c in answer_data.get("key_concepts_covered", [])
        )
        missed_html = "".join(
            f"<span class='tag tag-active'>{c}</span> " for c in answer_data.get("key_concepts_missed", [])
        )

        next_btn = ""
        if index + 1 < len(session.quiz_items):
            next_btn = f'<a href="/quiz?topic={topic}" class="btn btn-success">Next Question →</a>'
        else:
            next_btn = f'<a href="/save?topic={topic}" class="btn btn-success">💾 Save Session</a>'

        return f"""
<div class="card" style="margin-bottom:1.5rem">
  <h2>📊 Evaluation: Question {index + 1}</h2>
  <p style="color:var(--muted)"><strong>Q:</strong> {item["question"]}</p>
</div>

<div class="verdict {verdict_class}">
  <h3><span class="verdict-score">{answer_data.get("score", 0):.0%}</span> — {verdict}</h3>
  <div class="verdict-details">
    <strong>Feedback:</strong> {answer_data.get("feedback", "")}
  </div>
</div>

<div class="card">
  <h3>✅ Strengths</h3>
  <ul>{strengths_html or "<li>None identified</li>"}</ul>
</div>

<div class="card">
  <h3>📉 Gaps</h3>
  <ul>{gaps_html or "<li>None identified</li>"}</ul>
</div>

<div class="card">
  <h3>🎯 Key Concepts</h3>
  <p><strong>Covered:</strong> {covered_html or "<em>None</em>"}</p>
  <p><strong>Missed:</strong> {missed_html or "<em>None</em>"}</p>
</div>

<div class="card" style="text-align:center">
  {next_btn}
  <a href="/learn?topic={topic}" class="btn btn-outline ml-1">← Review Lesson</a>
</div>"""

    def _save(self, params: dict) -> str:
        topic = (params.get("topic") or [""])[0]
        session = self._get_session()

        if not topic or session.topic != topic:
            return '<div class="card"><h2>Save</h2><p>No session to save. <a href="/" class="btn">← Dashboard</a></p></div>'

        # Actually save to event store
        try:
            self._persist_session(session)
            session.quiz_answers = []  # Clear after save
            session.current_quiz_index = 0
            return f"""
<div class="card">
  <h2>✅ Session Saved!</h2>
  <div class="msg ok">
    <b>Successfully persisted to event store:</b>
    <ul style="margin-top:0.5rem;margin-left:1.5rem">
      <li>TopicStartedEvent for "{topic}"</li>
      <li>{len(session.lesson_sections)} LessonSectionCommittedEvents</li>
      <li>QuizCreatedEvent + {len(session.quiz_items)} QuizItemCreatedEvents</li>
      <li>{len(session.quiz_answers)} AnswerScoredEvents + JourneyEntryRecordedEvents</li>
      <li>Metacognitive insights recorded</li>
    </ul>
  </div>
  <div class="card" style="text-align:center;margin-top:1rem">
    <a href="/learn?topic={topic}" class="btn">← Review Lesson</a>
    <a href="/quiz?topic={topic}" class="btn btn-outline ml-1">🔁 Retake Quiz</a>
    <a href="/" class="btn ml-1">← Dashboard</a>
  </div>
</div>"""
        except Exception as e:
            return f'<div class="card"><h2>Save Failed</h2><div class="msg err"><b>Error:</b> {e}</div><a href="/quiz?topic={topic}" class="btn">← Back</a></div>'

    def _profile(self) -> str:
        km = self._cog.build_knowledge_map()
        profile = self._l.get_learner_profile()

        traits = (
            "".join(f"<tr><td>{k}</td><td>{v}</td></tr>" for k, v in profile.approved_traits.items())
            or "<tr><td colspan='2'>(none)</td></tr>"
        )
        topics = ", ".join(sorted(profile.topics_studied)) or "(none)"

        return f"""
<div class="card">
  <div class="stat-row">
    <div class="stat"><div class="stat-val">{len(profile.topics_studied)}</div><div class="stat-lbl">Topics</div></div>
    <div class="stat"><div class="stat-val">{km.total_quizzes_taken}</div><div class="stat-lbl">Quizzes</div></div>
    <div class="stat"><div class="stat-val">{km.average_quiz_score:.0%}</div><div class="stat-lbl">Avg Score</div></div>
    <div class="stat"><div class="stat-val">{km.overall_level.title()}</div><div class="stat-lbl">Level</div></div>
    <div class="stat"><div class="stat-val">{len(profile.pending_deltas)}</div><div class="stat-lbl">Pending</div></div>
  </div>
</div>
<div class="card"><h2>Cognitive Traits</h2><table style="width:100%"><tr><th>Trait</th><th>Value</th></tr>{traits}</table></div>
<div class="card"><h2>Topics Studied</h2><p>{topics}</p></div>"""

    def _map(self) -> str:
        km = self._cog.build_knowledge_map()
        topics_html = ""
        for topic, nodes in km.topics.items():
            nodes_html = ""
            for node in nodes:
                bar = "🟩" * int(node.understanding_level * 10) + "⬜" * (10 - int(node.understanding_level * 10))
                nodes_html += f"<tr><td>{node.concept}</td><td>{bar}</td><td>{node.understanding_level:.0%}</td><td>{node.times_encountered}</td></tr>"
            topics_html += f'<div class="card"><h3>{topic}</h3><table style="width:100%"><tr><th>Concept</th><th>Understanding</th><th>Level</th><th>Encounters</th></tr>{nodes_html}</table></div>'

        weak = (
            "".join(f'<span class="tag tag-active">{w}</span> ' for w in km.weak_areas[:5])
            or "<span class='tag tag-passed'>None</span>"
        )
        strong = (
            "".join(f'<span class="tag tag-passed">{s}</span> ' for s in km.strong_areas[:5])
            or "<span class='tag tag-new'>None</span>"
        )

        return f"""
<div class="card">
  <div class="stat-row">
    <div class="stat"><div class="stat-val">{km.topics_studied_count}</div><div class="stat-lbl">Topics</div></div>
    <div class="stat"><div class="stat-val" style="color:{"var(--success)" if km.overall_level == "expert" else "var(--warning)" if km.overall_level == "intermediate" else "var(--muted)"}">{km.overall_level.title()}</div><div class="stat-lbl">Level</div></div>
    <div class="stat"><div class="stat-val">{km.average_quiz_score:.0%}</div><div class="stat-lbl">Avg Score</div></div>
  </div>
  <p><strong>Weak areas:</strong> {weak}</p>
  <p><strong>Strong areas:</strong> {strong}</p>
</div>
{topics_html}"""

    def _history(self) -> str:
        journey = self._cog.get_journey()
        if not journey:
            return '<div class="card"><h2>History</h2><p>No activity yet. <a href="/learn" class="btn">Start Learning!</a></p></div>'

        rows = ""
        for entry in journey[-50:]:
            icon = {
                "session_started": "📖",
                "section_read": "📄",
                "dig_deeper": "🔍",
                "quiz_completed": "📝",
                "recommendation_approved": "✅",
                "recommendation_rejected": "❌",
            }.get(entry.entry_type, "•")
            score = f" ({entry.score:.0%})" if entry.score is not None else ""
            rows += f"<tr><td style='font-size:0.8rem'>{entry.timestamp[:19]}</td><td>{icon}</td><td>{entry.entry_type}</td><td>{entry.topic}</td><td style='font-size:0.85rem'>{entry.detail}{score}</td></tr>"

        return f"""
<div class="card"><h2>Full Timeline ({len(journey)} entries)</h2>
<div style="max-height:500px;overflow-y:auto">
<table style="width:100%"><tr><th>Time</th><th></th><th>Type</th><th>Topic</th><th>Detail</th></tr>{rows}</table>
</div></div>"""

    # ═══════════════════════════════════════════════════════════════════════
    # API ENDPOINTS
    # ═══════════════════════════════════════════════════════════════════════

    def _api_search(self, params: dict):
        topic = (params.get("topic") or [""])[0]
        if not topic:
            self._json({"error": "Topic required"}, 400)
            return

        try:
            result = self._grounding.get_grounding(topic, max_chunks=GROUNDING_MAX_CHUNKS)
            chunks = [
                {
                    "title": c.source_title,
                    "url": c.source_url,
                    "content": c.content,
                }
                for c in result.chunks
            ]
            self._json({"topic": topic, "chunks": chunks, "count": len(chunks)})
        except Exception as e:
            self._json({"error": str(e)}, 500)

    def _api_generate_lesson(self, params: dict):
        topic = (params.get("topic") or [""])[0]
        if not topic:
            self._json({"error": "Topic required"}, 400)
            return

        session = self._get_session()

        try:
            # Get grounding
            result = self._grounding.get_grounding(topic, max_chunks=GROUNDING_MAX_CHUNKS)
            chunks = [{"title": c.source_title, "url": c.source_url, "content": c.content} for c in result.chunks]

            # Generate lesson sections from chunks using LLM
            sections = self._generate_lesson_sections(topic, chunks)

            # Store in session
            session.topic = topic
            session.grounding_chunks = chunks
            session.lesson_sections = sections

            # Start learning session in cognitive engine
            session.learning_session_id = self._cog.start_session(topic)

            # Record section reads
            for sec in sections:
                self._cog.record_section_read(session.learning_session_id, sec["section_id"])

            self._json({"success": True, "sections": len(sections), "sources": len(chunks)})
        except Exception as e:
            self._json({"error": str(e)}, 500)

    def _generate_lesson_sections(self, topic: str, chunks: list[dict]) -> list[dict]:
        """Generate lesson sections from grounding chunks using LLM."""
        client = OllamaAgentClient(OLLAMA_MODEL, OLLAMA_NUM_CTX)

        sources_text = "\n\n".join(
            f"[Source {i + 1}: {c['title']} ({c['url']})]\n{c['content'][:2000]}" for i, c in enumerate(chunks)
        )

        prompt = f"""You are an expert educator creating an interactive lesson from authoritative sources.

TOPIC: {topic}

SOURCE MATERIAL:
{sources_text}

Create a structured lesson with 3-5 sections. Each section should:
1. Have a clear, engaging title
2. Cover a distinct subtopic
3. Be written in an ADHD-friendly style: short paragraphs, clear headings, code examples where relevant, analogies
4. Include the source citations inline as [Source N]

RESPOND WITH VALID JSON ONLY:
{{
  "sections": [
    {{
      "section_id": "sec-001",
      "title": "Section Title",
      "body": "Section content with [Source 1] citations...",
      "citations": [{{"title": "Source Title", "url": "https://..."}}]
    }},
    ...
  ]
}}"""

        try:
            response = client.generate_raw(prompt)
            start = response.find("{")
            end = response.rfind("}") + 1
            if start >= 0 and end > start:
                data = json.loads(response[start:end])
                return data.get("sections", [])
        except Exception:
            pass

        # Fallback: simple sections from chunks
        sections = []
        for i, chunk in enumerate(chunks[:4]):
            sections.append(
                {
                    "section_id": f"sec-{i + 1:03d}",
                    "title": f"Understanding {topic} — Part {i + 1}",
                    "body": chunk["content"][:CHUNK_MAX_CHARS] + "...",
                    "citations": [{"title": chunk["title"], "url": chunk["url"]}],
                }
            )
        return sections

    def _api_generate_quiz(self, params: dict):
        topic = (params.get("topic") or [""])[0]
        session = self._get_session()

        if not topic or session.topic != topic or not session.grounding_chunks:
            self._json({"error": "No lesson generated for this topic"}, 400)
            return

        try:
            # Generate quiz items
            items = self._quiz_gen.generate(topic, session.grounding_chunks)

            # Create quiz in quiz engine
            quiz_id = f"quiz-{topic.lower().replace(' ', '-')}-{uuid.uuid4().hex[:8]}"
            self._q.create_quiz(topic, quiz_id, title=f"Quiz: {topic}")

            quiz_items = []
            for i, item in enumerate(items):
                item_id = f"{quiz_id}-item-{i + 1}"
                # Create answer key from expected keywords
                answer_key = AnswerKey(
                    required_keywords=item.get("expected_keywords", []),
                    forbidden_keywords=[],
                    min_length_chars=20,
                )
                self._q.add_item(
                    quiz_id,
                    item_id,
                    item["question"],
                    item.get("type", "conceptual"),
                    item.get("difficulty", "medium"),
                    answer_key,
                    required_keywords=item.get("expected_keywords", []),
                )
                quiz_items.append(
                    {
                        "quiz_item_id": item_id,
                        "question": item["question"],
                        "type": item.get("type", "conceptual"),
                        "difficulty": item.get("difficulty", "medium"),
                        "expected_keywords": item.get("expected_keywords", []),
                        "expected_answer_outline": item.get("expected_answer_outline", ""),
                    }
                )

            session.quiz_items = quiz_items
            session.current_quiz_index = 0
            session.quiz_answers = []

            self._json({"success": True, "quiz_id": quiz_id, "items": len(quiz_items)})
        except Exception as e:
            self._json({"error": str(e)}, 500)

    def _api_evaluate_answer(self, params: dict):
        topic = (params.get("topic") or [""])[0]
        question = (params.get("question") or [""])[0]
        answer = (params.get("answer") or [""])[0]
        index = int((params.get("index") or ["0"])[0])
        session = self._get_session()

        if not topic or session.topic != topic or index >= len(session.quiz_items):
            self._json({"error": "Invalid session or question"}, 400)
            return

        item = session.quiz_items[index]
        quiz_item_id = item["quiz_item_id"]

        # Prepare source context from grounding chunks
        source_context = "\n\n".join(
            f"[Source {i + 1}: {c.get('title', '')} ({c.get('url', '')})]\n{c.get('content', '')[:1500]}"
            for i, c in enumerate(session.grounding_chunks)
        )

        # Evaluate with LLM Evaluation Service
        eval_result = self._llm_eval.evaluate_answer(
            quiz_item_id=quiz_item_id,
            raw_answer=answer,
            question=question,
            source_context=source_context,
            attempt_number=1,
        )

        # Convert to dict for JSON response
        eval_dict = {
            "score": eval_result.score,
            "passed": eval_result.passed,
            "verdict": "PASS" if eval_result.passed else "FAIL",
            "feedback": eval_result.reasoning,
            "strengths": eval_result.next_steps if eval_result.passed else [],
            "gaps": eval_result.misconceptions,
            "key_concepts_covered": [],
            "key_concepts_missed": eval_result.misconceptions,
            "evaluation_method": eval_result.evaluation_method,
            "confidence": eval_result.confidence,
        }

        # Store answer
        session.quiz_answers.append(
            {
                "index": index,
                "question": question,
                "answer": answer,
                **eval_dict,
            }
        )
        session.current_quiz_index = index + 1

        # Record in cognitive engine
        if session.learning_session_id:
            self._cog.record_quiz_result(
                session.learning_session_id,
                eval_result.score,
                eval_result.passed,
            )

        self._json({"success": True, "evaluation": eval_dict})

    def _api_save_session(self, params: dict):
        topic = (params.get("topic") or [""])[0]
        session = self._get_session()

        if not topic or session.topic != topic:
            self._json({"error": "No session to save"}, 400)
            return

        try:
            self._persist_session(session)
            self._json({"success": True, "message": "Session saved to event store"})
        except Exception as e:
            self._json({"error": str(e)}, 500)

    def _persist_session(self, session: SessionState):
        """Persist entire learning session to event store."""
        topic = session.topic

        # 1. Ensure topic is started
        self._l.start_topic(topic)

        # 2. Commit lesson sections
        for sec in session.lesson_sections:
            self._l.commit_lesson_section(
                topic=topic,
                section_id=sec["section_id"],
                title=sec["title"],
                body=sec["body"],
                source_citations=[c["url"] for c in sec.get("citations", [])],
                lesson_title=topic,
            )

        # 3. Quiz and items already created via quiz engine (events already appended)
        # But we need to record the quiz session completion
        if session.learning_session_id:
            # Record journey entry for session completion
            event = JourneyEntryRecordedEvent.create(
                session_id=session.learning_session_id,
                entry_type="session_completed",
                topic=topic,
                detail=f"Completed lesson and quiz on {topic}. Avg score: {sum(a.get('score', 0) for a in session.quiz_answers) / len(session.quiz_answers):.0%}"
                if session.quiz_answers
                else f"Completed lesson on {topic}",
            )
            self._l._event_store.append(event)

        # 4. Trigger metacognitive insights generation
        self._cog.get_recommendations()
        self._cog.get_metacognitive_insights()


# ═══════════════════════════════════════════════════════════════════════
# MAIN ENTRY POINT
# ═══════════════════════════════════════════════════════════════════════


def main(host: str = "0.0.0.0", port: int = 8080):
    print("🚀 Starting Helix Education Center V2...")
    print(f"   Model: {OLLAMA_MODEL}")
    print("   Grounding: Web search (authoritative sources)")
    print("   Quiz: LLM-generated from sources")
    print("   Evaluation: LLM semantic evaluation with reasoning")

    # Initialize services
    store = EventStore(StoreConfig(path="helix_events.jsonl"))
    ks = SealedAnswerKeyStore()
    llm_eval = LLMEvaluationService(agent_client=OllamaAgentClient(model_name=OLLAMA_MODEL), key_store=ks)
    l = LearningService(store, ks, llm_evaluation=llm_eval)
    c = ContentService(l)
    q = QuizService(l)
    f = FeedbackService(l)
    cog = CognitiveService(l)

    # Grounding: real web search
    grounding_client = WebGroundingClient(timeout_seconds=20)
    grounding = GroundingService(grounding_client, cache_ttl_seconds=3600)

    # Bind to handler
    _Handler._l = l
    _Handler._c = c
    _Handler._q = q
    _Handler._f = f
    _Handler._cog = cog
    _Handler._grounding = grounding
    _Handler._llm_eval = llm_eval

    topics = c.list_topics()
    print(f"   Topics in store: {len(topics)}")
    print(f"   Server: http://localhost:{port}")
    print("   Ready!")

    server = HTTPServer((host, port), _Handler)
    try:
        server.serve_forever()
    except KeyboardInterrupt:
        print("\n👋 Shutting down...")
        server.server_close()


if __name__ == "__main__":
    main()
