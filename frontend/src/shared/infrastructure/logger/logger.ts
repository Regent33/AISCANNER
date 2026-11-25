/** Structured logging adapter. Swap the sink here; callers never touch console directly. */
export type Logger = {
  info(event: string, data?: Record<string, unknown>): void
  warn(event: string, data?: Record<string, unknown>): void
  error(event: string, data?: Record<string, unknown>): void
}

export const consoleLogger: Logger = {
  info: (event, data) => console.info(`[${event}]`, data ?? {}),
  warn: (event, data) => console.warn(`[${event}]`, data ?? {}),
  error: (event, data) => console.error(`[${event}]`, data ?? {}),
}
