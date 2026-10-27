export function track(eventName: string, properties?: Record<string, unknown>): void {
  if (typeof window !== 'undefined' && (window as any).__NW_DEBUG) {
    console.log('[nw:analytics]', eventName, properties)
  }
}
