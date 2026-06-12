import { useState, useEffect } from "react"
import Diagram from "./Diagram"

const API = "http://127.0.0.1:8000"

// Answer language. "auto" = reply in whatever language the student typed/spoke.
// Any other choice FORCES the tutor to answer in that language. The `speech`
// code is also used for the microphone.
const LANGUAGES = [
    { code: "auto", label: "🌐 Auto (match my language)", speech: "en-IN" },
    { code: "en", label: "English", speech: "en-IN" },
    { code: "hi", label: "हिंदी / Hindi", speech: "hi-IN" },
    { code: "ta", label: "தமிழ் / Tamil", speech: "ta-IN" },
    { code: "te", label: "తెలుగు / Telugu", speech: "te-IN" },
    { code: "kn", label: "ಕನ್ನಡ / Kannada", speech: "kn-IN" },
    { code: "ml", label: "മലയാളം / Malayalam", speech: "ml-IN" },
    { code: "mr", label: "मराठी / Marathi", speech: "mr-IN" },
    { code: "bn", label: "বাংলা / Bengali", speech: "bn-IN" },
    { code: "gu", label: "ગુજરાતી / Gujarati", speech: "gu-IN" },
    { code: "pa", label: "ਪੰਜਾਬੀ / Punjabi", speech: "pa-IN" },
]

const STORAGE_KEY = "ruralmind_progress"

const emptyProgress = {
    streak: 0,
    lastActive: "",          // YYYY-MM-DD
    totalQuestions: 0,
    bestScore: 0,
    topics: [],              // [{topic, date}]
    revision: [],            // [{topic, nextReview, stage}]
    badges: [],              // [badge id]
}

const today = () => new Date().toISOString().slice(0, 10)
const addDays = (d, n) => {
    const dt = new Date(d)
    dt.setDate(dt.getDate() + n)
    return dt.toISOString().slice(0, 10)
}

const BADGES = [
    { id: "first", label: "🌱 First Question", test: p => p.totalQuestions >= 1 },
    { id: "curious5", label: "🔎 Curious (5)", test: p => p.totalQuestions >= 5 },
    { id: "curious20", label: "📚 Bookworm (20)", test: p => p.totalQuestions >= 20 },
    { id: "streak3", label: "🔥 3-Day Streak", test: p => p.streak >= 3 },
    { id: "streak7", label: "⚡ 7-Day Streak", test: p => p.streak >= 7 },
    { id: "quiz100", label: "🏆 Quiz Master", test: p => p.bestScore >= 100 },
]

export default function App() {

    const [question, setQuestion] = useState("")
    const [messages, setMessages] = useState([])
    const [loading, setLoading] = useState(false)
    const [mode, setMode] = useState("student")
    const [history, setHistory] = useState([])
    const [score, setScore] = useState(0)

    // New: language / grade / subject / view
    const [language, setLanguage] = useState("auto")
    const [grade, setGrade] = useState("")
    const [subject, setSubject] = useState("")
    const [view, setView] = useState("chat")   // chat | revise | progress

    // Persistent progress (streaks, badges, revision...)
    const [progress, setProgress] = useState(emptyProgress)

    // ---- load / save progress ----
    useEffect(() => {
        try {
            const saved = localStorage.getItem(STORAGE_KEY)
            if (saved) setProgress({ ...emptyProgress, ...JSON.parse(saved) })
        } catch { /* ignore */ }
    }, [])

    const persist = (next) => {
        setProgress(next)
        try { localStorage.setItem(STORAGE_KEY, JSON.stringify(next)) } catch { /* ignore */ }
    }

    // Update streak / counters / revision / badges when a new question is asked.
    const recordActivity = (topic) => {
        setProgress(prev => {
            const t = today()
            let streak = prev.streak
            if (prev.lastActive === t) {
                // already counted today
            } else if (prev.lastActive === addDays(t, -1)) {
                streak = prev.streak + 1
            } else {
                streak = 1
            }

            const topics = [{ topic, date: t }, ...prev.topics].slice(0, 100)

            // spaced repetition: schedule first review tomorrow
            const revision = [
                { topic, nextReview: addDays(t, 1), stage: 0 },
                ...prev.revision.filter(r => r.topic !== topic),
            ].slice(0, 100)

            const draft = {
                ...prev,
                streak,
                lastActive: t,
                totalQuestions: prev.totalQuestions + 1,
                topics,
                revision,
            }
            draft.badges = BADGES.filter(b => b.test(draft)).map(b => b.id)
            try { localStorage.setItem(STORAGE_KEY, JSON.stringify(draft)) } catch { /* ignore */ }
            return draft
        })
    }

    const bumpScore = (newScore) => {
        setScore(newScore)
        setProgress(prev => {
            if (newScore <= prev.bestScore) return prev
            const draft = { ...prev, bestScore: newScore }
            draft.badges = BADGES.filter(b => b.test(draft)).map(b => b.id)
            try { localStorage.setItem(STORAGE_KEY, JSON.stringify(draft)) } catch { /* ignore */ }
            return draft
        })
    }

    // Move a revised topic to the next spaced-repetition stage.
    const markRevised = (topic) => {
        const intervals = [1, 3, 7, 14, 30]
        persist({
            ...progress,
            revision: progress.revision.map(r => {
                if (r.topic !== topic) return r
                const stage = Math.min(r.stage + 1, intervals.length - 1)
                return { topic, stage, nextReview: addDays(today(), intervals[stage]) }
            }),
        })
    }

    // recent conversation to send to the backend (for follow-ups)
    const conversationContext = () =>
        messages
            .filter(m => m.type === "user" || m.type === "ai")
            .slice(-6)
            .map(m => ({ role: m.type, text: m.text }))

    const buildAskUrl = (text, overrideMode) => {
        const params = new URLSearchParams({
            question: text,
            mode: overrideMode || mode,
            grade,
            subject,
            reply: language,   // "auto" = match my language, else force it
            history: JSON.stringify(conversationContext()),
        })
        return `${API}/ask?${params.toString()}`
    }

    // ---- speech input (now language-aware) ----
    const speak = () => {
        if (!("webkitSpeechRecognition" in window)) {
            alert("Voice input is not supported in this browser. Try Chrome.")
            return
        }
        const recognition = new window.webkitSpeechRecognition()
        const lang = LANGUAGES.find(l => l.code === language)
        recognition.lang = lang ? lang.speech : "en-IN"
        recognition.start()
        recognition.onresult = (e) => setQuestion(e.results[0][0].transcript)
    }

    // ---- photo / textbook OCR ----
    const handlePhoto = async (e) => {
        const file = e.target.files[0]
        if (!file) return
        setLoading(true)
        try {
            const fd = new FormData()
            fd.append("file", file)
            const res = await fetch(`${API}/ocr`, { method: "POST", body: fd })
            const data = await res.json()
            if (data.text && data.text.trim()) {
                setQuestion(data.text.trim())
            } else {
                alert("Could not read the image. Make sure Tesseract is installed on the server.")
            }
        } catch {
            alert("OCR failed. Is the server running?")
        }
        setLoading(false)
        e.target.value = ""
    }

    const pushAi = (data) =>
        setMessages(m => [...m, { type: "ai", text: data.answer, audio: data.audio }])

    const askAI = async () => {
        if (!question.trim()) return
        const currentQuestion = question
        setQuestion("")
        setMessages(m => [...m, { type: "user", text: currentQuestion }])
        setHistory(h => [...h, currentQuestion])
        recordActivity(currentQuestion.slice(0, 60))
        setLoading(true)
        const res = await fetch(buildAskUrl(currentQuestion))
        const data = await res.json()
        pushAi(data)
        setLoading(false)
    }

    const reAsk = async (text, overrideMode) => {
        setLoading(true)
        const res = await fetch(buildAskUrl(text, overrideMode))
        const data = await res.json()
        pushAi(data)
        setLoading(false)
    }

    const explainSimpler = (text) => reAsk(text, "kid")
    const explainDetailed = (text) => reAsk(text, "detailed")
    const guideMe = (text) => reAsk(text, "guide")

    const translateEnglish = async (text) => {
        setLoading(true)
        const res = await fetch(`${API}/translate?text=${encodeURIComponent(text)}&target=en`)
        const data = await res.json()
        pushAi(data)
        setLoading(false)
    }

    const generateQuiz = async (text) => {
        const res = await fetch(`${API}/quiz?question=${encodeURIComponent(text)}&reply=${language}`)
        const data = await res.json()
        const quiz = data.quiz
        setMessages(m => [...m, {
            type: "quiz", question: quiz.question, options: quiz.options, answer: quiz.answer,
        }])
    }

    const generateDiagram = async (text) => {
        const res = await fetch(`${API}/diagram?question=${encodeURIComponent(text)}`)
        const data = await res.json()
        setMessages(m => [...m, {
            type: "diagram", image: data.image, topic: data.topic,
            nodes: data.nodes, links: data.links,
        }])
    }

    // ---- printable notes / worksheet ----
    const exportNotes = async (text) => {
        let questions = []
        let topic = text.slice(0, 40)
        try {
            const res = await fetch(`${API}/worksheet?question=${encodeURIComponent(text)}`)
            const data = await res.json()
            questions = data.questions || []
            topic = data.topic || topic
        } catch { /* offline -> notes only */ }

        const w = window.open("", "_blank")
        if (!w) return
        const qHtml = questions.map((q, i) => `<li>${q}</li>`).join("")
        w.document.write(`
            <html><head><title>RuralMind Notes</title>
            <style>
              body{font-family:system-ui,Arial,sans-serif;padding:32px;color:#111;line-height:1.5}
              h1{color:#15803d;margin:0 0 4px}
              h2{color:#15803d;margin-top:28px}
              .meta{color:#666;font-size:13px;margin-bottom:18px}
              .notes{font-size:16px;white-space:pre-wrap}
              ol{font-size:16px} li{margin:8px 0}
            </style></head>
            <body>
              <h1>🌳 RuralMind — Notes</h1>
              <div class="meta">${topic}${grade ? " · Class " + grade : ""}${subject ? " · " + subject : ""}</div>
              <div class="notes">${text.replace(/</g, "&lt;")}</div>
              <h2>Practice Questions</h2>
              <ol>${qHtml}</ol>
            </body></html>`)
        w.document.close()
        w.focus()
        setTimeout(() => w.print(), 400)
    }

    const dueRevision = progress.revision.filter(r => r.nextReview <= today())
    const earnedBadges = BADGES.filter(b => progress.badges.includes(b.id))

    return (
        <div className="app">

            <div className="sidebar">
                <h2>🌳 RuralMind</h2>

                <div className="nav-tabs">
                    <button className={view === "chat" ? "tab active" : "tab"} onClick={() => setView("chat")}>Chat</button>
                    <button className={view === "revise" ? "tab active" : "tab"} onClick={() => setView("revise")}>
                        Revise{dueRevision.length ? ` (${dueRevision.length})` : ""}
                    </button>
                    <button className={view === "progress" ? "tab active" : "tab"} onClick={() => setView("progress")}>Progress</button>
                </div>

                <div className="streak-box">🔥 {progress.streak} day streak</div>

                <div className="chat-history">Recent Questions</div>
                {history.map((h, i) => (
                    <p key={i} className="chat-history">• {h.slice(0, 30)}</p>
                ))}
            </div>

            <div className="chat-wrapper">
                <div className="chat-container">

                    {/* ===================== CHAT VIEW ===================== */}
                    {view === "chat" && (
                        <>
                            <div className="chat-header">AI Tutor — ask in any language</div>

                            <div className="progress">
                                <div className="progress-inner" style={{ width: `${score}%` }}></div>
                            </div>

                            <div className="messages">
                                {messages.map((m, i) => {

                                    if (m.type === "diagram") {
                                        if (m.image) {
                                            return (
                                                <div key={i} className="ai" style={{ marginTop: "10px" }}>
                                                    {m.topic && <p style={{ marginBottom: "6px", fontWeight: "600" }}>{m.topic} — diagram</p>}
                                                    <img src={m.image} alt={m.topic || "diagram"}
                                                        style={{ maxWidth: "100%", borderRadius: "12px", background: "#fff" }} />
                                                </div>
                                            )
                                        }
                                        return (
                                            <div key={i} style={{ width: "100%", height: "500px", marginTop: "10px" }}>
                                                <Diagram nodes={m.nodes} links={m.links} />
                                            </div>
                                        )
                                    }

                                    if (m.type === "quiz") {
                                        return (
                                            <div key={i} className="quiz">
                                                <p className="font-semibold mb-2">{m.question}</p>
                                                {m.options.map((opt, index) => (
                                                    <label key={index} className="block mt-2">
                                                        <input type="radio" name={`quiz-${i}`}
                                                            onChange={() => {
                                                                if (opt === m.answer) {
                                                                    alert("Correct!")
                                                                    bumpScore(Math.min(score + 20, 100))
                                                                } else {
                                                                    alert("Incorrect")
                                                                }
                                                            }} />
                                                        <span className="ml-2">{opt}</span>
                                                    </label>
                                                ))}
                                            </div>
                                        )
                                    }

                                    return (
                                        <div key={i} className={m.type === "user" ? "user" : "ai"}>
                                            <p>{m.text}</p>
                                            {m.audio && <audio controls src={m.audio} />}
                                            {m.type === "ai" && (
                                                <div className="flex gap-2 mt-2" style={{ flexWrap: "wrap" }}>
                                                    <button onClick={() => explainSimpler(m.text)}>Simpler</button>
                                                    <button onClick={() => explainDetailed(m.text)}>Detailed</button>
                                                    <button onClick={() => guideMe(m.text)}>Guide me</button>
                                                    <button onClick={() => translateEnglish(m.text)}>English</button>
                                                    <button onClick={() => generateQuiz(m.text)}>Quiz</button>
                                                    <button onClick={() => generateDiagram(m.text)}>Diagram</button>
                                                    <button onClick={() => exportNotes(m.text)}>Save Notes</button>
                                                </div>
                                            )}
                                        </div>
                                    )
                                })}
                                {loading && <p>AI tutor is typing...</p>}
                            </div>

                            <div className="picker-bar">
                                <select value={language} onChange={e => setLanguage(e.target.value)} title="Answer language (also sets the mic)">
                                    {LANGUAGES.map(l => <option key={l.code} value={l.code}>{l.label}</option>)}
                                </select>
                                <select value={grade} onChange={e => setGrade(e.target.value)} title="Class">
                                    <option value="">Class</option>
                                    {[5, 6, 7, 8, 9, 10].map(g => <option key={g} value={g}>Class {g}</option>)}
                                </select>
                                <select value={subject} onChange={e => setSubject(e.target.value)} title="Subject">
                                    <option value="">Subject</option>
                                    {["Science", "Maths", "Social Science", "English", "EVS"].map(s => <option key={s} value={s}>{s}</option>)}
                                </select>
                                <select value={mode} onChange={e => setMode(e.target.value)} title="Answer style">
                                    <option value="kid">Kid</option>
                                    <option value="student">Student</option>
                                    <option value="detailed">Detailed</option>
                                    <option value="exam">Exam</option>
                                    <option value="guide">Guide me</option>
                                </select>
                            </div>

                            <div className="input-bar">
                                <input value={question}
                                    onChange={e => setQuestion(e.target.value)}
                                    onKeyDown={e => { if (e.key === "Enter") askAI() }}
                                    placeholder="Ask your question in any language..." />
                                <label className="icon-btn" title="Upload a photo of a question">
                                    📷
                                    <input type="file" accept="image/*" onChange={handlePhoto} style={{ display: "none" }} />
                                </label>
                                <button onClick={speak} title="Speak">🎤</button>
                                <button onClick={askAI}>Send</button>
                            </div>
                        </>
                    )}

                    {/* ===================== REVISE VIEW ===================== */}
                    {view === "revise" && (
                        <div className="panel">
                            <div className="chat-header">Revision — spaced repetition</div>
                            {dueRevision.length === 0 && <p style={{ padding: 16 }}>Nothing due right now. Great job! 🎉 Come back tomorrow.</p>}
                            {dueRevision.map((r, i) => (
                                <div key={i} className="ai" style={{ marginTop: 10 }}>
                                    <p><b>{r.topic}</b></p>
                                    <div className="flex gap-2 mt-2" style={{ flexWrap: "wrap" }}>
                                        <button onClick={() => { setView("chat"); reAsk(r.topic, "student") }}>Review now</button>
                                        <button onClick={() => generateQuiz(r.topic)}>Quiz me</button>
                                        <button onClick={() => markRevised(r.topic)}>I remember this ✓</button>
                                    </div>
                                </div>
                            ))}
                        </div>
                    )}

                    {/* ===================== PROGRESS / DASHBOARD VIEW ===================== */}
                    {view === "progress" && (
                        <div className="panel">
                            <div className="chat-header">Progress Dashboard</div>
                            <div className="stat-grid">
                                <div className="stat"><b>{progress.streak}</b><span>🔥 Day streak</span></div>
                                <div className="stat"><b>{progress.totalQuestions}</b><span>❓ Questions asked</span></div>
                                <div className="stat"><b>{progress.bestScore}</b><span>🏆 Best quiz score</span></div>
                                <div className="stat"><b>{dueRevision.length}</b><span>📌 Due to revise</span></div>
                            </div>

                            <h3 style={{ marginTop: 20 }}>Badges</h3>
                            <div className="badges">
                                {earnedBadges.length === 0 && <span style={{ opacity: .7 }}>Ask questions to earn badges!</span>}
                                {earnedBadges.map(b => <span key={b.id} className="badge">{b.label}</span>)}
                            </div>

                            <h3 style={{ marginTop: 20 }}>Topics studied</h3>
                            <div style={{ maxHeight: 220, overflow: "auto" }}>
                                {progress.topics.length === 0 && <span style={{ opacity: .7 }}>No topics yet.</span>}
                                {progress.topics.map((t, i) => (
                                    <p key={i} style={{ margin: "4px 0" }}>• {t.topic} <span style={{ opacity: .5, fontSize: 12 }}>({t.date})</span></p>
                                ))}
                            </div>
                        </div>
                    )}

                </div>
            </div>
        </div>
    )
}
