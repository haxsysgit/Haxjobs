import { createContext, useContext } from 'react'

export interface ToastContextType {
  success: (msg: string) => void
  error: (msg: string) => void
  info: (msg: string) => void
}

export const ToastCtx = createContext<ToastContextType>({
  success: () => {},
  error: () => {},
  info: () => {},
})

export function useToast() {
  return useContext(ToastCtx)
}
