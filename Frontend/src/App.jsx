import { useState } from "react"
import Diagram from "./Diagram"

export default function App(){

    const [question,setQuestion] = useState("")
    const [messages,setMessages] = useState([])
    const [loading,setLoading] = useState(false)
    const [mode,setMode] = useState("student")
    const [history,setHistory] = useState([])
    const [score,setScore] = useState(0)

    const speak = ()=>{
        const recognition = new webkitSpeechRecognition()
        recognition.lang="en-IN"
        recognition.start()

        recognition.onresult=(e)=>{
            setQuestion(e.results[0][0].transcript)
        }
    }

    const explainSimpler = async(text)=>{
        setLoading(true)

        const res = await fetch(
            `http://127.0.0.1:8000/ask?question=${encodeURIComponent(text)}&mode=kid`
        )

        const data = await res.json()

        setMessages(m=>[
            ...m,
            {
                type:"ai",
                text:data.answer,
                audio:data.audio
            }
        ])

        setLoading(false)
    }

    const generateQuiz = async(text)=>{
        const res = await fetch(
            `http://127.0.0.1:8000/quiz?question=${encodeURIComponent(text)}`
        )

        const data = await res.json()
        const quiz = data.quiz

        setMessages(m=>[
            ...m,
            {
                type:"quiz",
                question:quiz.question,
                options:quiz.options,
                answer:quiz.answer
            }
        ])
    }

    const generateDiagram = async(text)=>{
        const res = await fetch(
            `http://127.0.0.1:8000/diagram?question=${encodeURIComponent(text)}`
        )

        const data = await res.json()

        setMessages(m=>[
            ...m,
            {
                type:"diagram",
                nodes:data.nodes,
                links:data.links
            }
        ])
    }

    const askAI = async()=>{
        if(!question.trim()) return

        const currentQuestion = question
        setQuestion("")

        setMessages(m=>[
            ...m,
            {type:"user",text:currentQuestion}
        ])

        setHistory(h=>[...h,currentQuestion])
        setLoading(true)

        const res = await fetch(
            `http://127.0.0.1:8000/ask?question=${encodeURIComponent(currentQuestion)}&mode=${mode}`
        )

        const data = await res.json()

        setMessages(m=>[
            ...m,
            {
                type:"ai",
                text:data.answer,
                audio:data.audio
            }
        ])

        setLoading(false)
    }

    return(
        <div className="app">

            <div className="sidebar">
                <h2>RuralMind</h2>
                <div className="chat-history">Recent Questions</div>

                {history.map((h,i)=>(
                    <p key={i} className="chat-history">
                        • {h.slice(0,30)}
                    </p>
                ))}
            </div>

            <div className="chat-wrapper">
                <div className="chat-container">

                    <div className="chat-header">
                        AI Science Tutor
                    </div>

                    <div className="progress">
                        <div
                            className="progress-inner"
                            style={{width:`${score}%`}}
                        ></div>
                    </div>

                    <div className="messages">

                        {messages.map((m,i)=>{

                            if(m.type==="diagram"){
                                return(
                                    <div
                                        key={i}
                                        style={{
                                            width:"100%",
                                            height:"500px",
                                            marginTop:"10px"
                                        }}
                                    >
                                        <Diagram nodes={m.nodes} links={m.links}/>
                                    </div>
                                )
                            }

                            if(m.type==="quiz"){
                                return(
                                    <div key={i} className="quiz">
                                        <p className="font-semibold mb-2">
                                            {m.question}
                                        </p>

                                        {m.options.map((opt,index)=>(
                                            <label key={index} className="block mt-2">
                                                <input
                                                    type="radio"
                                                    name={`quiz-${i}`}
                                                    onChange={()=>{
                                                        if(opt===m.answer){
                                                            alert("Correct!")
                                                            setScore(s=>Math.min(s+20,100))
                                                        }else{
                                                            alert("Incorrect")
                                                        }
                                                    }}
                                                />
                                                <span className="ml-2">{opt}</span>
                                            </label>
                                        ))}
                                    </div>
                                )
                            }

                            return(
                                <div key={i} className={m.type==="user"?"user":"ai"}>
                                    <p>{m.text}</p>

                                    {m.audio && (
                                        <audio controls src={m.audio}/>
                                    )}

                                    {m.type==="ai" && (
                                        <div className="flex gap-2 mt-2">
                                            <button onClick={()=>explainSimpler(m.text)}>Simpler</button>
                                            <button onClick={()=>generateQuiz(m.text)}>Quiz</button>
                                            <button onClick={()=>generateDiagram(m.text)}>Diagram</button>
                                        </div>
                                    )}
                                </div>
                            )
                        })}

                        {loading && <p>AI tutor is typing...</p>}
                    </div>

                    <div className="input-bar">
                        <select
                            value={mode}
                            onChange={(e)=>setMode(e.target.value)}
                            className="text-black"
                        >
                            <option value="kid">Kid</option>
                            <option value="student">Student</option>
                            <option value="exam">Exam</option>
                        </select>

                        <input
                            value={question}
                            onChange={(e)=>setQuestion(e.target.value)}
                            onKeyDown={(e)=>{ if(e.key==="Enter") askAI() }}
                            placeholder="Ask your question..."
                        />

                        <button onClick={speak}>🎤</button>
                        <button onClick={askAI}>Send</button>
                    </div>

                </div>
            </div>
        </div>
    )
}