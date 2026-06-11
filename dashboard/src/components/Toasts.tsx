import { createContext, useContext, useState, useCallback, type ReactNode } from 'react'

type ToastType = 'success' | 'error' | 'info'

interface Toast {
  id: number
  type: ToastType
  message: string
}

interface ToastContextType {
  success: (msg: string) => void
  error: (msg: string) => void
  info: (msg: string) => void
}

const ToastCtx = createContext<ToastContextType>({
  success: () => {},
  error: () => {},
  info: () => {},
})

let toastId = 0

export function useToast() {
  return useContext(ToastCtx)
}

export function ToastProvider({ children }: { children: ReactNode }) {
  const [toasts, setToasts] = useState<Toast[]>([])

  const addToast = useCallback((type: ToastType, message: string) => {
    const id = ++toastId
    setToasts(prev => [...prev.slice(-4), { id, type, message }])
    setTimeout(() => {
      setToasts(prev => prev.filter(t => t.id !== id))
    }, 3500)
  }, [])

  const ctx: ToastContextType = {
    success: (msg: string) => addToast('success', msg),
    error: (msg: string) => addToast('error', msg),
    info: (msg: string) => addToast('info', msg),
  }

  const typeColors: Record<ToastType, string> = {
    success: 'var(--success)',
    error: 'var(--danger)',
    info: 'var(--accent)',
  }

  const typeIcons: Record<ToastType, string> = {
    success: '✓',
    error: '✗',
    info: 'ℹ',
  }

  return (
    <ToastCtx.Provider value={ctx}>
      {children}
      <div style={{
        position: 'fixed',
        top: 16,
        right: 16,
        zIndex: 9999,
        display: 'flex',
        flexDirection: 'column',
        gap: 8,
        maxWidth: 380,
      }}>
        {toasts.map(t => (
          <div key={t.id} style={{
            background: 'var(--bg)',
            border: `1px solid ${typeColors[t.type]}`,
            borderLeft: `4px solid ${typeColors[t.type]}`,
            borderRadius: 'var(--radius-sm)',
            padding: '10px 14px',
            fontSize: 13,
            boxShadow: '0 4px 16px rgba(0,0,0,0.12)',
            display: 'flex',
            gap: 10,
            alignItems: 'flex-start',
            animation: 'slideIn 0.2s ease-out',
          }}>
            <span style={{ color: typeColors[t.type], fontWeight: 700, flexShrink: 0 }}>
              {typeIcons[t.type]}
            </span>
            <span style={{ lineHeight: 1.4 }}>{t.message}</span>
          </div>
        ))}
      </div>
      <style>{`
        @keyframes slideIn {
          from { opacity: 0; transform: translateX(20px); }
          to { opacity: 1; transform: translateX(0); }
        }
      `}</style>
    </ToastCtx.Provider>
  )
}
