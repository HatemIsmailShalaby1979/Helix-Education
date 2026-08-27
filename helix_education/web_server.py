"""Full cognitive learning web UI -- dashboard, interactive lessons, quiz, profile, map, HITL."""

from http.server import BaseHTTPRequestHandler, HTTPServer
from urllib.parse import parse_qs, urlparse

from api_layer.routes import Router
from cognitive_engine.cognitive_service import CognitiveService
from content_engine import ContentService
from delivery_engine import FeedbackService
from learning_service import LearningService
from quiz_engine import QuizService
from state_core.event_store import EventStore, SealedAnswerKeyStore, StoreConfig

from .curriculum import topic_data, topic_names

_HTML = """<!DOCTYPE html>
<html lang="en">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>{title} -- Helix Education</title>
<style>
*{{box-sizing:border-box;margin:0;padding:0}}
body{{font-family:-apple-system,system-ui,sans-serif;background:#f1f5f9;color:#1e293b;padding:1.5rem;line-height:1.6}}
.container{{max-width:1000px;margin:0 auto}}
h1{{color:#2563eb;font-size:1.5rem}}
h2{{color:#334155;margin:1rem 0 0.5rem;font-size:1.2rem}}
h3{{color:#475569;margin:0.75rem 0 0.25rem}}
.nav{{margin-bottom:1rem;padding:0.5rem 0;border-bottom:2px solid #e2e8f0;display:flex;flex-wrap:wrap;gap:0.5rem}}
.nav a{{color:#2563eb;text-decoration:none;font-weight:500;font-size:0.9rem;padding:0.25rem 0.5rem;border-radius:4px}}
.nav a:hover{{background:#eff6ff}}
.card{{background:#fff;border-radius:8px;padding:1.25rem;margin-bottom:0.75rem;box-shadow:0 1px 2px rgba(0,0,0,0.06)}}
label{{display:block;margin-top:0.5rem;font-weight:600;color:#475569;font-size:0.9rem}}
input,textarea{{width:100%;padding:0.5rem;border:1px solid #cbd5e1;border-radius:6px;margin-top:0.2rem;font-size:0.9rem;font-family:inherit}}
textarea{{min-height:80px}}
button,.btn{{display:inline-block;background:#2563eb;color:#fff;border:none;padding:0.5rem 1.2rem;border-radius:6px;font-size:0.9rem;cursor:pointer;margin-top:0.5rem;text-decoration:none}}
button:hover,.btn:hover{{background:#1d4ed8}}
.btn-sm{{padding:0.3rem 0.8rem;font-size:0.8rem}}
.btn-green{{background:#16a34a}}.btn-green:hover{{background:#15803d}}
.btn-amber{{background:#d97706}}.btn-amber:hover{{background:#b45309}}
.btn-outline{{background:transparent;color:#2563eb;border:2px solid #2563eb}}
.btn-outline:hover{{background:#eff6ff}}
.msg{{padding:0.6rem 1rem;border-radius:6px;margin:0.5rem 0;font-size:0.9rem}}
.msg.ok{{background:#dcfce7;color:#166534;border:1px solid #bbf7d0}}
.msg.warn{{background:#fef3c7;color:#92400e;border:1px solid #fde68a}}
.msg.err{{background:#fee2e2;color:#991b1b;border:1px solid #fecaca}}
.msg.info{{background:#e0f2fe;color:#075985;border:1px solid #bae6fd}}
pre, .code{{background:#f1f5f9;padding:0.5rem;border-radius:4px;overflow-x:auto;font-size:0.85rem;white-space:pre-wrap}}
.stat-row{{display:flex;flex-wrap:wrap;gap:1rem;margin:0.5rem 0}}
.stat{{text-align:center;min-width:80px}}
.stat-val{{font-size:1.3rem;font-weight:700;color:#2563eb}}
.stat-lbl{{font-size:0.7rem;color:#64748b;text-transform:uppercase}}
.grid{{display:grid;grid-template-columns:repeat(auto-fill,minmax(220px,1fr));gap:0.75rem;margin:0.5rem 0}}
.tc{{border:1px solid #e2e8f0;border-radius:6px;padding:0.75rem;cursor:pointer;text-decoration:none;color:inherit;display:block}}
.tc:hover{{border-color:#2563eb}}
.tag{{font-size:0.75rem;padding:0.15rem 0.4rem;border-radius:4px;display:inline-block}}
.tg-new{{background:#f1f5f9;color:#64748b}}
.tg-active{{background:#fef3c7;color:#92400e}}
.tg-passed{{background:#dcfce7;color:#166534}}
.tg-rec{{background:#e0f2fe;color:#075985}}
table{{width:100%;border-collapse:collapse;font-size:0.9rem}}
th,td{{text-align:left;padding:0.4rem 0.5rem;border-bottom:1px solid #e2e8f0}}
.section-body{{white-space:pre-wrap;font-size:0.9rem}}
.ml-1{{margin-left:0.5rem}}
.mt-1{{margin-top:0.5rem}}
</style>
</head>
<body>
<div class="container">
<div style="display:flex;justify-content:space-between;align-items:center">
<h1>Helix Education Center</h1>
<div class="nav">
<a href="/">Dashboard</a><a href="/learn">Learn</a><a href="/profile">Profile</a>
<a href="/map">Cognitive Map</a><a href="/recommend">Recommendations</a><a href="/history">History</a>
</div></div>
{content}
</div>
</body>
</html>"""


class _Handler(BaseHTTPRequestHandler):
    _l: LearningService = None
    _c: ContentService = None
    _q: QuizService = None
    _f: FeedbackService = None
    _r: Router = None
    _cog: CognitiveService = None
    _dig_sessions: dict[str, str] = {}

    def _s(self, body: str, status: int = 200):
        self.send_response(status)
        self.send_header("Content-Type", "text/html; charset=utf-8")
        self.end_headers()
        self.wfile.write(body.encode("utf-8"))

    def _page(self, title: str, content: str):
        self._s(_HTML.format(title=title, content=content))

    def _flash(self, cls: str, text: str):
        return f'<div class="msg {cls}">{text}</div>'

    # -- GET ------------------------------------------------------

    def do_GET(self):
        parsed = urlparse(self.path)
        path = parsed.path.rstrip("/") or "/"
        params = parse_qs(parsed.query)
        try:
            if path == "/":
                self._page("Dashboard", self._dashboard())
            elif path == "/learn":
                topic = (params.get("topic") or [""])[0]
                dig_section = (params.get("dig") or [""])[0]
                self._page("Learn", self._learn(topic, dig_section))
            elif path == "/quiz":
                topic = (params.get("topic") or [""])[0]
                self._page(f"Quiz -- {topic}", self._quiz(topic))
            elif path == "/profile":
                self._page("Profile", self._profile())
            elif path == "/map":
                self._page("Cognitive Map", self._map())
            elif path == "/recommend":
                action = (params.get("action") or [""])[0]
                rid = (params.get("rid") or [""])[0]
                self._page("Recommendations", self._recommend(action, rid))
            elif path == "/history":
                self._page("History", self._history())
            else:
                self._s("<h1>404</h1>", 404)
        except Exception as e:
            self._page("Error", self._flash("err", str(e)))

    def do_POST(self):
        length = int(self.headers.get("Content-Length", 0))
        raw = self.rfile.read(length).decode("utf-8")
        params = parse_qs(raw)
        parsed = urlparse(self.path)
        path = parsed.path.rstrip("/") or "/"
        try:
            if path == "/start-topic":
                res = self._post_start(params)
            elif path == "/submit-quiz":
                res = self._post_quiz(params)
            elif path == "/dig-deeper":
                res = self._flash("ok", "")
            elif path == "/approve-rec":
                res = self._post_approve(params)
            else:
                self._s("<h1>404</h1>", 404)
                return
        except Exception as e:
            res = self._flash("err", str(e))
        self._page("Result", f'<a href="/" class="btn">&larr; Dashboard</a>{res}')

    # -- PAGES ----------------------------------------------------

    def _dashboard(self):
        km = self._cog.build_knowledge_map()
        pending = self._cog.get_pending_recommendations()
        insights = self._cog.get_metacognitive_insights()
        names = topic_names()

        tc = ""
        for name in names:
            state = self._l.get_topic_state(name)
            td = topic_data(name)
            prereqs = td.get("prerequisites", [])
            prereq_ok = all(self._l.get_topic_state(p).is_passed for p in prereqs)
            if state.is_passed:
                cls = "tg-passed"
                lbl = "PASSED"
            elif state.attempts_total > 0:
                cls = "tg-active"
                lbl = "Active"
            elif prereq_ok:
                cls = "tg-new"
                lbl = "Ready"
            else:
                cls = "tg-new"
                lbl = "🔒"
            tc += f'<a href="/learn?topic={name}" class="tc"><div style="display:flex;justify-content:space-between"><b>{name}</b><span class="tag {cls}">{lbl}</span></div><div style="font-size:0.8rem;color:#64748b">{state.current_level}</div></a>'

        insight_html = ""
        for ins in insights[-3:]:
            insight_html += (
                f'<div class="msg info"><b>{ins.title}</b><br>{ins.description}<br><i>{ins.recommendation}</i></div>'
            )

        return f"""
<div class="card">
<div class="stat-row">
<div class="stat"><div class="stat-val">{km.topics_studied_count}</div><div class="stat-lbl">Topics</div></div>
<div class="stat"><div class="stat-val">{km.total_quizzes_taken}</div><div class="stat-lbl">Quizzes</div></div>
<div class="stat"><div class="stat-val">{km.average_quiz_score:.0%}</div><div class="stat-lbl">Avg Score</div></div>
<div class="stat"><div class="stat-val" style="color:{"#16a34a" if km.overall_level == "expert" else "#d97706" if km.overall_level == "intermediate" else "#64748b"}">{km.overall_level}</div><div class="stat-lbl">Level</div></div>
<div class="stat"><div class="stat-val">{len(pending)}</div><div class="stat-lbl">Pending Recs</div></div>
</div>
</div>
{insight_html}
<div class="card"><h2>Topics</h2><div class="grid">{tc}</div></div>"""

    def _learn(self, topic: str, dig_section: str):
        names = topic_names()
        if not topic:
            tc = "".join(f'<a href="/learn?topic={n}" class="tc"><b>{n}</b></a>' for n in names)
            return f'<div class="card"><h2>Pick a Topic</h2><div class="grid">{tc}</div></div>'

        lesson = self._c.get_lesson(topic)
        td = topic_data(topic)
        if not lesson or not lesson.sections:
            return self._flash("err", f"No content for '{topic}'.") + self._learn("", "")

        state = self._l.get_topic_state(topic)
        sid = self._cog.start_session(topic)
        self._dig_sessions[topic] = sid

        sections = ""
        for sec in lesson.sections:
            self._cog.record_section_read(sid, sec.section_id)
            dig_url = f"/learn?topic={topic}&dig={sec.section_id}"
            dd_link = f'<a href="{dig_url}" class="btn btn-sm btn-outline">Dig Deeper</a>'
            extra = ""
            if dig_section == sec.section_id:
                self._cog.record_dig_deeper(sid)
                extra = '<div class="msg info" style="margin-top:0.5rem"><b>Deeper dive requested</b><div class="section-body mt-1">Ask the AI tutor to generate advanced content for this section.</div></div>'
            sections += f'<div class="card"><h3>{sec.title}</h3><div class="section-body">{sec.body}</div>{dd_link}{extra}</div>'

        quiz_link = f'<a href="/quiz?topic={topic}" class="btn btn-green">Take Quiz on {topic}</a>'
        status = (
            '<span class="tag tg-passed">PASSED</span>'
            if state.is_passed
            else ('<span class="tag tg-active">In Progress</span>' if state.attempts_total > 0 else "")
        )

        return f"""
<div class="card"><h2>{lesson.title}</h2>{status}<p style="color:#64748b;font-size:0.85rem">{len(lesson.sections)} section(s) &middot; {state.current_level}</p></div>
{sections}
<div class="card" style="text-align:center">{quiz_link}</div>"""

    def _quiz(self, topic: str):
        quizzes = self._q.list_quizzes_for_topic(topic)
        if not quizzes:
            return (
                self._flash("err", f"No quiz for '{topic}'.")
                + f'<a href="/learn?topic={topic}" class="btn">Back to Lesson</a>'
            )
        q = quizzes[0]
        items = ""
        for item in q.items:
            items += f'<div class="card"><p><b>{item.question}</b> <span style="color:#64748b;font-size:0.85rem">({item.difficulty})</span></p><label>Your answer:</label><textarea name="{item.quiz_item_id}" rows="2"></textarea></div>'
        return f"""
<form method="post" action="/submit-quiz">
<input type="hidden" name="topic" value="{topic}">
<input type="hidden" name="quiz_id" value="{q.quiz_id}">
{items}
<button type="submit">Submit All Answers</button>
<a href="/learn?topic={topic}" class="btn btn-outline ml-1">Review Lesson</a>
</form>"""

    def _profile(self):
        km = self._cog.build_knowledge_map()
        profile = self._r.handle_get_profile()
        journey = self._cog.get_journey()
        insights = self._cog.get_metacognitive_insights()

        traits = (
            "".join(f"<tr><td>{k}</td><td>{v}</td></tr>" for k, v in profile.approved_traits.items())
            if profile.approved_traits
            else "<tr><td colspan='2'>(none)</td></tr>"
        )
        topics = ", ".join(sorted(profile.topics_studied)) if profile.topics_studied else "(none)"
        ji = "".join(
            f"<tr><td style='font-size:0.8rem'>{e.timestamp[:19]}</td><td>{e.entry_type}</td><td>{e.topic}</td><td style='font-size:0.85rem'>{e.detail}</td></tr>"
            for e in journey[-15:]
        )
        ins = "".join(
            f'<div class="msg info"><b>{i.title}</b><br>{i.description}<br><i>{i.recommendation}</i></div>'
            for i in insights
        )

        return f"""
<div class="card">
<div class="stat-row">
<div class="stat"><div class="stat-val">{len(profile.topics_studied)}</div><div class="stat-lbl">Topics</div></div>
<div class="stat"><div class="stat-val">{km.total_quizzes_taken}</div><div class="stat-lbl">Quizzes</div></div>
<div class="stat"><div class="stat-val">{km.average_quiz_score:.0%}</div><div class="stat-lbl">Avg Score</div></div>
<div class="stat"><div class="stat-val">{km.overall_level}</div><div class="stat-lbl">Level</div></div>
<div class="stat"><div class="stat-val">{profile.pending_delta_count}</div><div class="stat-lbl">Pending</div></div>
</div>
</div>
{ins}
<div class="card"><h2>Cognitive Traits</h2><table><tr><th>Trait</th><th>Value</th></tr>{traits}</table></div>
<div class="card"><h2>Topics Studied</h2><p>{topics}</p></div>
<div class="card"><h2>Recent Journey ({len(journey)} entries)</h2><div style="max-height:300px;overflow-y:auto"><table><tr><th>Time</th><th>Type</th><th>Topic</th><th>Detail</th></tr>{ji}</table></div></div>"""

    def _map(self):
        km = self._cog.build_knowledge_map()
        topics_html = ""
        for topic, nodes in km.topics.items():
            nodes_html = ""
            for node in nodes:
                bar = "🟩" * int(node.understanding_level * 10) + "⬜" * (10 - int(node.understanding_level * 10))
                nodes_html += f"<tr><td>{node.concept}</td><td>{bar}</td><td>{node.understanding_level:.0%}</td><td>{node.times_encountered}</td></tr>"
            topics_html += f'<div class="card"><h3>{topic}</h3><table><tr><th>Concept</th><th>Understanding</th><th>Level</th><th>Encounters</th></tr>{nodes_html}</table></div>'

        weak = (
            "".join(f'<span class="tag tg-active ml-1">{w}</span>' for w in km.weak_areas[:5])
            if km.weak_areas
            else "<span class='tag tg-passed'>None</span>"
        )
        strong = (
            "".join(f'<span class="tag tg-passed ml-1">{s}</span>' for s in km.strong_areas[:5])
            if km.strong_areas
            else "<span class='tag tg-new'>None</span>"
        )

        return f"""
<div class="card">
<div class="stat-row">
<div class="stat"><div class="stat-val">{km.topics_studied_count}</div><div class="stat-lbl">Topics</div></div>
<div class="stat"><div class="stat-val" style="color:{"#16a34a" if km.overall_level == "expert" else "#d97706" if km.overall_level == "intermediate" else "#64748b"}">{km.overall_level}</div><div class="stat-lbl">Level</div></div>
<div class="stat"><div class="stat-val">{km.average_quiz_score:.0%}</div><div class="stat-lbl">Avg Score</div></div>
</div>
<p><b>Weak areas:</b> {weak}</p>
<p><b>Strong areas:</b> {strong}</p>
</div>
{topics_html}"""

    def _recommend(self, action: str, rid: str):
        if action == "approve" and rid:
            self._cog.approve_recommendation(rid)
            return self._flash("ok", "Recommendation approved. Cognitive memory updated.") + self._recommend("", "")
        if action == "reject" and rid:
            self._cog.reject_recommendation(rid)
            return self._flash("warn", "Recommendation rejected.") + self._recommend("", "")

        pending = self._cog.get_pending_recommendations()
        approved = self._cog.get_approved_recommendations()

        pend_html = ""
        for rec in pending:
            pend_html += f"""
<div class="card">
<div class="tag {"tg-active" if rec.priority == "high" else "tg-new"}">{rec.priority.upper()}</div>
<p><b>{rec.concept}</b> ({rec.topic})</p>
<p style="font-size:0.85rem;color:#64748b">Reason: {rec.reason}</p>
<p style="font-size:0.85rem;color:#64748b">Action: {rec.suggested_action}</p>
<p style="font-size:0.8rem;color:#94a3b8">Evidence: {rec.evidence}</p>
<a href="/recommend?action=approve&rid={rec.recommendation_id}" class="btn btn-sm btn-green">Approve</a>
<a href="/recommend?action=reject&rid={rec.recommendation_id}" class="btn btn-sm btn-outline ml-1">Reject</a>
</div>"""
        if not pending:
            pend_html = '<div class="card"><p>No pending recommendations. Take a quiz to generate insights.</p></div>'

        app_html = (
            "".join(
                f'<div class="card"><p>✅ <b>{rec.concept}</b> -- {rec.suggested_action} <span style="color:#64748b;font-size:0.8rem">({rec.timestamp[:19]})</span></p></div>'
                for rec in approved[-5:]
            )
            if approved
            else ""
        )

        return f"""
<div class="card"><h2>Human-in-the-Loop Approval</h2><p style="color:#64748b;font-size:0.85rem">Review cognitive recommendations. Approving feeds the cognitive memory.</p></div>
<h2>Pending ({len(pending)})</h2>{pend_html}
{"<h2>Recently Approved</h2>" + app_html if app_html else ""}"""

    def _history(self):
        journey = self._cog.get_journey()
        if not journey:
            return (
                '<div class="card"><h2>History</h2><p>No activity yet. <a href="/learn">Start learning!</a></p></div>'
            )

        names = topic_names()
        topic_summary = ""
        for name in names:
            state = self._l.get_topic_state(name)
            topic_entries = [e for e in journey if e.topic == name]
            quiz_entries = [e for e in topic_entries if e.entry_type == "quiz_completed"]
            topic_summary += f"<tr><td>{name}</td><td>{state.current_level}</td><td>{'PASSED' if state.is_passed else 'Active' if state.attempts_total > 0 else 'New'}</td><td>{state.attempts_total}</td><td>{len(quiz_entries)}</td></tr>"

        rows = ""
        for entry in journey:
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
<div class="card"><h2>Progress Summary</h2>
<table><tr><th>Topic</th><th>Level</th><th>Status</th><th>Attempts</th><th>Quizzes</th></tr>{topic_summary}</table></div>
<div class="card"><h2>Full Timeline ({len(journey)} entries)</h2><div style="max-height:500px;overflow-y:auto"><table><tr><th>Time</th><th></th><th>Type</th><th>Topic</th><th>Detail</th></tr>{rows}</table></div></div>"""

    # -- POST -----------------------------------------------------

    def _post_start(self, params):
        topic = (params.get("topic") or [""])[0]
        if not topic:
            return self._flash("err", "Topic name required.")
        level = (params.get("level") or [""])[0] or "beginner"
        from api_layer.api_models import StartTopicRequest

        self._r.handle_start_topic(
            StartTopicRequest(topic=topic, requested_level=level if level != "beginner" else None)
        )
        return (
            self._flash("ok", f"Topic '{topic}' started!")
            + f'<a href="/learn?topic={topic}" class="btn">Start Learning</a>'
        )

    def _post_quiz(self, params):
        topic = (params.get("topic") or [""])[0]
        quiz_id = (params.get("quiz_id") or [""])[0]
        if not topic or not quiz_id:
            return self._flash("err", "Missing topic or quiz.")

        quiz = self._q.get_quiz(quiz_id)
        if not quiz:
            return self._flash("err", "Quiz not found.")

        sid = self._dig_sessions.get(topic) or self._cog.start_session(topic)
        session_qid = self._q.start_session(quiz_id)
        results = []
        for item in quiz.items:
            answer = (params.get(item.quiz_item_id) or [""])[0].strip()
            if not answer:
                continue
            sr = self._q.answer_item(session_qid, item.quiz_item_id, answer)
            results.append(sr)

        self._q.complete_session(session_qid)
        summary = self._q.get_session_summary(session_qid)
        if not summary:
            return self._flash("err", "No answers submitted.")

        self._cog.record_quiz_result(sid, summary["average_score"], summary["pass_rate"] >= 0.6)
        self._cog.get_recommendations()  # auto-generate recommendations

        fb = ""
        for sr in results:
            icon = "✅" if sr.passed else "❌"
            fb += f'<div style="padding:0.4rem 0;border-bottom:1px solid #e2e8f0">{icon} <b>{sr.question}</b> -- Score: {sr.raw_score:.0%}</div>'

        return f"""
<div class="msg {"ok" if summary["pass_rate"] >= 0.6 else "warn"}">
<b>{"Passed!" if summary["pass_rate"] >= 0.6 else "Needs improvement"}</b>
Score: {summary["passed_count"]}/{summary["total_items"]} correct ({summary["average_score"]:.0%})
</div>
{fb}
<div style="margin-top:0.75rem">
<a href="/learn?topic={topic}" class="btn">Review Lesson</a>
<a href="/quiz?topic={topic}" class="btn btn-outline ml-1">Retry</a>
<a href="/recommend" class="btn btn-amber ml-1">View Recommendations</a>
</div>"""

    def _post_approve(self, params):
        rid = (params.get("rid") or [""])[0]
        action = (params.get("action") or [""])[0]
        if rid and action == "approve":
            self._cog.approve_recommendation(rid)
        elif rid and action == "reject":
            self._cog.reject_recommendation(rid)
        self.send_response(302)
        self.send_header("Location", "/recommend")
        self.end_headers()


def main(host: str = "0.0.0.0", port: int = 8080):
    store = EventStore(StoreConfig(path="helix_events.jsonl"))
    ks = SealedAnswerKeyStore()
    l = LearningService(store, ks)
    c = ContentService(l)
    q = QuizService(l)
    f = FeedbackService(l)
    r = Router(l, f)
    cog = CognitiveService(l)

    _Handler._l = l
    _Handler._c = c
    _Handler._q = q
    _Handler._f = f
    _Handler._r = r
    _Handler._cog = cog

    topics = c.list_topics()
    print(f"Helix Education Center -- http://localhost:{port}")
    print(f"Topics: {len(topics)}  |  Cognitive engine active  |  HITL approval ready")
    server = HTTPServer((host, port), _Handler)
    try:
        server.serve_forever()
    except KeyboardInterrupt:
        server.server_close()


if __name__ == "__main__":
    main()
