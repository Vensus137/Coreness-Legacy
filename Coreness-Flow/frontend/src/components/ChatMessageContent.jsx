/**
 * Рендер тела сообщения: user/system — структура (переносы) + ссылки; assistant/auto — полный markdown + подсветка кода.
 * Полный рендер сразу. Анимации и чанкование — архив (ChatMessageContent.archive.jsx, chat-messages-chunks.archive.css).
 */

import { useState, useCallback } from 'react'
import { linkifySegments } from '../utils/linkify'
import ReactMarkdown from 'react-markdown'
import remarkGfm from 'remark-gfm'
import { Prism as SyntaxHighlighter } from 'react-syntax-highlighter'
import Tooltip from './Tooltip'

const LANG_LABELS = { js: 'javascript', ts: 'typescript', py: 'python', sh: 'shell', bash: 'bash', json: 'json', yaml: 'yaml', yml: 'yaml', md: 'markdown', html: 'html', css: 'css' }

function CopyIcon() {
  return (
    <svg xmlns="http://www.w3.org/2000/svg" width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round" aria-hidden>
      <rect width="14" height="14" x="8" y="8" rx="2" ry="2" />
      <path d="M4 16c-1.1 0-2-.9-2-2V4c0-1.1.9-2 2-2h10c1.1 0 2 .9 2 2" />
    </svg>
  )
}

function CheckIcon() {
  return (
    <svg xmlns="http://www.w3.org/2000/svg" width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round" aria-hidden>
      <path d="M20 6L9 17l-5-5" />
    </svg>
  )
}

/** Рендер текста с сохранением переносов и ссылок (user/system). */
export function SimpleMessageContent({ text, className }) {
  const segments = linkifySegments(text ?? '')
  return (
    <div className={className} style={{ whiteSpace: 'pre-wrap' }}>
      {segments.map((seg, i) => {
        if (seg.type === 'text') {
          return <span key={i}>{seg.value}</span>
        }
        return (
          <a
            key={i}
            href={seg.href}
            target="_blank"
            rel="noopener noreferrer"
            className="chat-message-link"
          >
            {seg.label}
          </a>
        )
      })}
    </div>
  )
}

/** Блок кода с подсветкой, меткой языка и кнопкой копирования. */
function CodeBlock({ node, inline, className, children, ...props }) {
  const match = /language-(\w+)/.exec(className ?? '')
  const code = String(children).replace(/\n$/, '')
  const [copied, setCopied] = useState(false)

  const handleCopy = useCallback(() => {
    navigator.clipboard?.writeText(code).then(() => {
      setCopied(true)
      setTimeout(() => setCopied(false), 1500)
    })
  }, [code])

  if (!inline && match) {
    const lang = (match[1] || '').toLowerCase()
    const langLabel = (LANG_LABELS[lang] ?? lang) || 'code'
    return (
      <div className="chat-code-bubble">
        <span className="chat-code-lang-badge">{langLabel}</span>
        <div className="chat-code-bubble-header">
          <Tooltip text={copied ? 'Скопировано' : 'Копировать'}>
            <button
              type="button"
              className="chat-code-copy"
              onClick={handleCopy}
              aria-label="Копировать код"
            >
              {copied ? <CheckIcon /> : <CopyIcon />}
            </button>
          </Tooltip>
        </div>
        <SyntaxHighlighter
          style={{}}
          language={match[1]}
          PreTag="div"
          className="chat-message-code-block"
          customStyle={{ background: 'transparent', backgroundColor: 'transparent' }}
          useInlineStyles={false}
          wrapLongLines
          codeTagProps={{
            className: `language-${match[1]}`,
            style: { fontSize: '0.9em', background: 'transparent', backgroundColor: 'transparent' },
          }}
        >
          {code}
        </SyntaxHighlighter>
      </div>
    )
  }
  return (
    <code className={className} {...props}>
      {children}
    </code>
  )
}

const markdownComponents = {
  pre: ({ children }) => <>{children}</>,
  code: CodeBlock,
}

/** Полный markdown (assistant/auto) — весь текст сразу. */
export function MarkdownMessageContent({ text, className }) {
  return (
    <div className={className}>
      <ReactMarkdown remarkPlugins={[remarkGfm]} components={markdownComponents}>
        {text ?? ''}
      </ReactMarkdown>
    </div>
  )
}
