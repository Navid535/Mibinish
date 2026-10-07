export function daysUntilPurge(
  completedAt: string | null | undefined,
  retentionDays: number,
): number | null {
  if (!completedAt) return null;

  const completedDate = new Date(completedAt);
  const deadline = new Date(completedDate.getTime() + retentionDays * 24 * 60 * 60 * 1000);
  const now = new Date();

  const diffMs = deadline.getTime() - now.getTime();
  return Math.ceil(diffMs / (24 * 60 * 60 * 1000));
}