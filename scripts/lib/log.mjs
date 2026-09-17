export function warn(msg) { console.warn(`[warn] ${msg}`); }
export function fail(msg) { console.error(`[error] ${msg}`); process.exit(1); }
