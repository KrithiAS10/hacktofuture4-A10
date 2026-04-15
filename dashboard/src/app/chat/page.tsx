'use client'
// src/app/chat/page.tsx
import { useState, useRef, useEffect } from 'react'
import { motion, AnimatePresence } from 'framer-motion'
import { Send } from 'lucide-react'
import { Badge, PageHeader } from '@/components/ui'
import { initialChatMessages, cannedResponses, type ChatMessage } from '@/lib/mock-data'
import clsx from 'clsx'

let cannedIdx = 0

function renderContent(text: string) {
  // Bold: **text**, Code: `text`
  const parts = text.split(/(\*\*.*?\*\*|`.*?`)/g)
  return parts.map((part, i) => {
    if (part.startsWith('**') && part.endsWith('**')) {
      return <strong key={i} className="text-white font-bold">{part.slice(2, -2)}</strong>
    }
    if (part.startsWith('`') && part.endsWith('`')) {
      return (
        <code key={i} className="bg-white/10 px-1.5 py-0.5 rounded text-[11px] font-mono text-lerna-blue2">
          {part.slice(1, -1)}
        </code>
      )
    }
    // Render newlines
    return part.split('\n').map((line, j, arr) => (
      <span key={`${i}-${j}`}>
        {line}
        {j < arr.length - 1 && <br />}
      </span>
    ))
  })
}

const quickActions = [
  'Apply fix to production',
  'Show all active incidents',
  'What is the cluster health?',
  'Run sandbox simulation',
]

export default function ChatPage() {
  const [messages, setMessages] = useState<ChatMessage[]>(initialChatMessages)
  const [input, setInput] = useState('')
  const [isTyping, setIsTyping] = useState(false)
  const bottomRef = useRef<HTMLDivElement>(null)
  const textareaRef = useRef<HTMLTextAreaElement>(null)

  useEffect(() => {
    bottomRef.current?.scrollIntoView({ behavior: 'smooth' })
  }, [messages, isTyping])

  function now() {
    const d = new Date()
    return `${d.getHours()}:${String(d.getMinutes()).padStart(2, '0')}:${String(d.getSeconds()).padStart(2, '0')}`
  }

  async function send(text: string) {
    if (!text.trim()) return
    setInput('')
    if (textareaRef.current) {
      textareaRef.current.style.height = 'auto'
    }

    const userMsg: ChatMessage = { id: Date.now().toString(), role: 'user', content: text.trim(), timestamp: now() }
    setMessages(prev => [...prev, userMsg])
    setIsTyping(true)

    await new Promise(r => setTimeout(r, 1500 + Math.random() * 800))

    const reply = cannedResponses[cannedIdx % cannedResponses.length]
    cannedIdx++
    const assistantMsg: ChatMessage = { id: (Date.now() + 1).toString(), role: 'assistant', content: reply, timestamp: now() }
    setMessages(prev => [...prev, assistantMsg])
    setIsTyping(false)
  }

  function handleKey(e: React.KeyboardEvent) {
    if (e.key === 'Enter' && !e.shiftKey) {
      e.preventDefault()
      send(input)
    }
  }

  function autoResize(e: React.ChangeEvent<HTMLTextAreaElement>) {
    setInput(e.target.value)
    e.target.style.height = 'auto'
    e.target.style.height = Math.min(e.target.scrollHeight, 120) + 'px'
  }

  return (
    <div className="p-7 flex flex-col h-screen">
      <div className="mb-5">
        <PageHeader title="Lerna AI Chat" subtitle="Natural language interface to the SRE pipeline">
          <Badge variant="purple">● GPT-4 Turbo</Badge>
        </PageHeader>
      </div>

      {/* Messages */}
      <div className="flex-1 overflow-y-auto flex flex-col gap-4 min-h-0 pb-4">
        {messages.map((msg) => (
          <motion.div
            key={msg.id}
            initial={{ opacity: 0, y: 10 }}
            animate={{ opacity: 1, y: 0 }}
            transition={{ duration: 0.25 }}
            className={clsx('flex gap-3 max-w-[85%]', msg.role === 'user' && 'flex-row-reverse ml-auto')}
          >
            <div className={clsx(
              'w-8 h-8 rounded-xl flex items-center justify-center text-[13px] font-bold shrink-0',
              msg.role === 'assistant'
                ? 'bg-gradient-to-br from-lerna-blue to-lerna-purple text-white'
                : 'bg-bg-4 text-[#8A9BBB]'
            )}>
              {msg.role === 'assistant' ? 'L' : 'U'}
            </div>
            <div>
              <div className={clsx(
                'px-4 py-3 rounded-2xl text-[13px] leading-relaxed',
                msg.role === 'assistant'
                  ? 'bg-bg-3 border border-border rounded-tl-sm'
                  : 'bg-gradient-to-br from-lerna-blue to-lerna-purple text-white rounded-tr-sm'
              )}>
                {renderContent(msg.content)}
              </div>
              <div className={clsx(
                'text-[10px] text-[#4A5B7A] font-mono mt-1 px-1',
                msg.role === 'user' && 'text-right'
              )}>
                {msg.timestamp}
              </div>
            </div>
          </motion.div>
        ))}

        {/* Typing indicator */}
        <AnimatePresence>
          {isTyping && (
            <motion.div
              initial={{ opacity: 0, y: 10 }}
              animate={{ opacity: 1, y: 0 }}
              exit={{ opacity: 0 }}
              className="flex gap-3 max-w-[85%]"
            >
              <div className="w-8 h-8 rounded-xl flex items-center justify-center bg-gradient-to-br from-lerna-blue to-lerna-purple text-white text-[13px] font-bold shrink-0">
                L
              </div>
              <div className="bg-bg-3 border border-border rounded-2xl rounded-tl-sm px-4 py-3">
                <div className="flex gap-1.5 items-center">
                  {[0,1,2].map(i => (
                    <span key={i} className={`typing-dot w-1.5 h-1.5 rounded-full bg-[#4A5B7A]`} />
                  ))}
                </div>
              </div>
            </motion.div>
          )}
        </AnimatePresence>
        <div ref={bottomRef} />
      </div>

      {/* Input Area */}
      <div className="border-t border-border pt-4 shrink-0">
        {/* Quick actions */}
        <div className="flex gap-2 mb-3 flex-wrap">
          {quickActions.map(action => (
            <button
              key={action}
              onClick={() => send(action)}
              className="text-[11px] px-3 py-1.5 rounded-lg bg-bg-3 border border-border text-[#8A9BBB] hover:border-border-2 hover:text-white transition-all font-mono cursor-pointer"
            >
              {action}
            </button>
          ))}
        </div>

        <div className="bg-bg-3 border border-border-2 rounded-2xl flex items-end gap-2 px-4 py-3 focus-within:border-lerna-blue transition-colors">
          <textarea
            ref={textareaRef}
            value={input}
            onChange={autoResize}
            onKeyDown={handleKey}
            placeholder="Ask Lerna anything about your infrastructure..."
            rows={1}
            className="flex-1 bg-transparent border-none outline-none text-[13px] font-sans text-[#E8EDF5] placeholder:text-[#4A5B7A] resize-none min-h-5 max-h-[120px] leading-relaxed"
          />
          <motion.button
            whileHover={{ scale: 1.05 }}
            whileTap={{ scale: 0.95 }}
            onClick={() => send(input)}
            className="w-9 h-9 rounded-xl bg-gradient-to-br from-lerna-blue to-lerna-purple flex items-center justify-center shrink-0 cursor-pointer border-none"
          >
            <Send size={14} className="text-white" />
          </motion.button>
        </div>
        <div className="text-[10px] text-[#4A5B7A] font-mono mt-2 text-center">
          Press Enter to send · Shift+Enter for new line
        </div>
      </div>
    </div>
  )
}