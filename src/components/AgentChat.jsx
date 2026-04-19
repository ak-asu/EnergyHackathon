import { useState, useRef, useEffect } from 'react'
import { useAgent } from '../hooks/useAgent'
import MarkdownRenderer from './MarkdownRenderer'

const BRIEFING_PROMPT =
  'Give me a current market briefing: (1) current regime state and what it means for BTM economics, ' +
  '(2) the strongest siting opportunity right now and why, (3) the top risk to watch.'

function CitationChip({ text }) {
  const isCoord = /^-?\d+\.\d+,-?\d+\.\d+/.test(text)
  const isNode = /^(HB_|PALO|SP15|NP15)/.test(text)
  const cls = isCoord ? 'citation-chip--green' : isNode ? 'citation-chip--orange' : 'citation-chip--blue'
  return <span className={`citation-chip ${cls}`}>{text}</span>
}

function Message({ role, text, citations }) {
  return (
    <div className={`chat-message chat-message--${role}`}>
      <div className="chat-bubble">
        {role === 'assistant'
          ? <MarkdownRenderer>{text}</MarkdownRenderer>
          : text}
      </div>
      {citations && citations.length > 0 && (
        <div className="chat-citations">
          {citations.map((c, i) => <CitationChip key={i} text={c} />)}
        </div>
      )}
    </div>
  )
}

export default function AgentChat({ context }) {
  const [input, setInput] = useState('')
  const [history, setHistory] = useState([])
  const { tokens, citations, status, ask, reset } = useAgent()
  const endRef = useRef(null)

  useEffect(() => {
    endRef.current?.scrollIntoView({ behavior: 'smooth' })
  }, [tokens, history])

  const submit = (text) => {
    const q = (text || input).trim()
    if (!q || status === 'loading' || status === 'streaming') return
    const contextWithHistory = {
      ...context,
      history: history.slice(-6).map(m => ({ role: m.role, content: m.text })),
    }
    setHistory(h => [...h, { role: 'user', text: q }])
    setInput('')
    reset()
    ask(q, contextWithHistory)
  }

  const clearChat = () => {
    reset()
    setHistory([])
    setInput('')
  }

  const onKey = e => { if (e.key === 'Enter' && !e.shiftKey) { e.preventDefault(); submit() } }

  useEffect(() => {
    if (status === 'done' && tokens) {
      setHistory(h => [...h, { role: 'assistant', text: tokens, citations }])
      reset()
    }
  }, [status])

  const busy = status === 'loading' || status === 'streaming'

  return (
    <div className="agent-chat">
      <div className="chat-quick-prompts">
        <button
          className="chat-quick-chip"
          onClick={() => submit(BRIEFING_PROMPT)}
          disabled={busy}
        >
          Market Briefing
        </button>
        <button
          className="chat-quick-chip chat-quick-chip--ghost"
          onClick={clearChat}
          disabled={busy}
          title="Clear chat"
        >
          Clear
        </button>
      </div>

      <div className="chat-messages">
        {history.length === 0 && status === 'idle' && (
          <div className="chat-empty">Ask about sites, timing, stress scenarios, or click Market Briefing for a market overview.</div>
        )}
        {history.map((msg, i) => (
          <Message key={i} role={msg.role} text={msg.text} citations={msg.citations} />
        ))}
        {(status === 'loading' || status === 'streaming') && (
          <div className="chat-message chat-message--assistant">
            <div className="chat-bubble">
              {status === 'loading'
                ? <span className="chat-thinking">Thinking…</span>
                : <MarkdownRenderer streaming>{tokens}</MarkdownRenderer>}
            </div>
            {citations.length > 0 && (
              <div className="chat-citations">
                {citations.map((c, i) => <CitationChip key={i} text={c} />)}
              </div>
            )}
          </div>
        )}
        {status === 'error' && (
          <div className="chat-message chat-message--error">
            <div className="chat-bubble">Error — check ANTHROPIC_API_KEY and backend logs.</div>
          </div>
        )}
        <div ref={endRef} />
      </div>

      <div className="chat-input-row">
        <textarea
          className="chat-input"
          value={input}
          onChange={e => setInput(e.target.value)}
          onKeyDown={onKey}
          placeholder="Ask about sites, timing, stress scenarios, or economics…"
          rows={2}
        />
        <button
          className="chat-send-btn"
          onClick={() => submit()}
          disabled={!input.trim() || busy}
        >
          →
        </button>
      </div>
    </div>
  )
}
