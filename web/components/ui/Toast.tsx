'use client'

import * as Toast from '@radix-ui/react-toast'
import * as React from 'react'

type Item = { id: number; title?: string; description: string; tone: 'info' | 'error' }
type Ctx = { add: (t: Omit<Item, 'id'>) => void }

const ToastCtx = React.createContext<Ctx>({ add: () => {} })
export const useToast = () => React.useContext(ToastCtx)

export function ToastProvider({ children }: { children: React.ReactNode }) {
  const [items, setItems] = React.useState<Item[]>([])
  const add = React.useCallback((t: Omit<Item, 'id'>) => {
    setItems((prev) => [...prev, { ...t, id: Date.now() + Math.random() }])
  }, [])
  return (
    <ToastCtx.Provider value={{ add }}>
      <Toast.Provider duration={4000} swipeDirection="right">
        {children}
        {items.map((item) => (
          <Toast.Root
            key={item.id}
            onOpenChange={(open) => { if (!open) setItems((p) => p.filter((x) => x.id !== item.id)) }}
            className={
              'rounded-md border bg-chart shadow-md p-3 grid gap-1 ' +
              (item.tone === 'error' ? 'border-error/40' : 'border-border')
            }
          >
            {item.title && <Toast.Title className="text-sm font-medium">{item.title}</Toast.Title>}
            <Toast.Description className="text-sm text-ink-soft">{item.description}</Toast.Description>
          </Toast.Root>
        ))}
        <Toast.Viewport className="fixed bottom-4 right-4 flex flex-col gap-2 w-[360px] z-50" />
      </Toast.Provider>
    </ToastCtx.Provider>
  )
}
