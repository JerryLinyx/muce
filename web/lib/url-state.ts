export function paramsFromSearch(sp: URLSearchParams): Record<string, string> {
  const out: Record<string, string> = {}
  sp.forEach((v, k) => { out[k] = v })
  return out
}

export function mergeSearch(
  sp: URLSearchParams,
  overrides: Record<string, string | null | undefined>,
): string {
  const next = new URLSearchParams(sp)
  for (const [k, v] of Object.entries(overrides)) {
    if (v === null || v === undefined || v === '') next.delete(k)
    else next.set(k, v)
  }
  return next.toString()
}
