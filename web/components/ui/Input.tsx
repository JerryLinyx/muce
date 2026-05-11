import * as React from 'react'

export const Input = React.forwardRef<HTMLInputElement, React.InputHTMLAttributes<HTMLInputElement>>(
  function Input({ className = '', ...props }, ref) {
    return (
      <input
        ref={ref}
        className={
          'h-8 px-2.5 text-sm rounded-sm bg-canvas border border-border ' +
          'focus:outline-none focus:border-border-strong focus:bg-chart ' +
          'placeholder:text-ink-muted ' + className
        }
        {...props}
      />
    )
  }
)
