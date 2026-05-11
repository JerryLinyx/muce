import * as React from 'react'

type Variant = 'primary' | 'ghost' | 'subtle'

export interface ButtonProps extends React.ButtonHTMLAttributes<HTMLButtonElement> {
  variant?: Variant
  size?: 'sm' | 'md'
}

export const Button = React.forwardRef<HTMLButtonElement, ButtonProps>(function Button(
  { variant = 'subtle', size = 'md', className = '', ...props }, ref
) {
  const base = 'inline-flex items-center justify-center font-medium rounded-sm transition-colors disabled:opacity-50 disabled:cursor-not-allowed'
  const sizes = { sm: 'h-7 px-2.5 text-xs', md: 'h-8 px-3 text-sm' }
  const variants = {
    primary: 'bg-ink text-canvas hover:bg-ink-soft',
    ghost:   'text-ink-soft hover:text-ink hover:bg-surface',
    subtle:  'bg-accent-soft text-ink hover:bg-accent hover:text-canvas',
  }
  return <button ref={ref} className={`${base} ${sizes[size]} ${variants[variant]} ${className}`} {...props} />
})
