export function ErrorBanner({ children }: { children: React.ReactNode }) {
  return (
    <div className="border border-error/30 bg-canvas rounded-md px-3 py-2 text-sm text-error">
      {children}
    </div>
  )
}
