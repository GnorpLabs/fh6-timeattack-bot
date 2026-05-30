export function formatLapTime(ms: number): string {
  const mins = Math.floor(ms / 60000);
  const secs = ((ms % 60000) / 1000).toFixed(3).padStart(6, '0');
  return `${mins}:${secs}`;
}
