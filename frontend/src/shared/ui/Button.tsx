import type { ButtonHTMLAttributes } from 'react'

type Props = ButtonHTMLAttributes<HTMLButtonElement> & { variant?: 'primary' | 'secondary' | 'quiet' }

const STYLE = {
  primary: 'bg-accent text-accent-ink hover:opacity-90',
  secondary: 'border border-control bg-surface text-ink hover:bg-bg',
  quiet: 'text-muted hover:text-ink hover:bg-bg',
}

export function Button({ variant = 'secondary', className = '', type = 'button', ...rest }: Props) {
  return (
    <button
      type={type}
      {...rest}
      className={`inline-flex items-center justify-center gap-2 whitespace-nowrap rounded-lg px-4 py-2 text-sm font-medium
        transition active:translate-y-px disabled:cursor-not-allowed disabled:opacity-40 ${STYLE[variant]} ${className}`}
    />
  )
}
