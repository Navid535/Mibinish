export function getErrorMessage(err: any, fallback = 'Something went wrong. Please try again.'): string {
  if (err?.isAxiosError && !err.response) {
    return 'No connection. Check your internet and try again.';
  }

  if (!err?.response) {
    console.warn('Non-HTTP error:', err);
    return fallback;
  }

  const status = err.response.status;
  const data = err.response.data;

  if (status >= 500) {
    return 'Server error. Please try again in a moment.';
  }

  if (data && typeof data === 'object') {
    const firstFieldError = Object.values(data).find(
      (value) => Array.isArray(value) && value.length > 0,
    ) as string[] | undefined;
    if (firstFieldError) return String(firstFieldError[0]);

    if (data.detail) return String(data.detail);
    if (data.non_field_errors?.[0]) return String(data.non_field_errors[0]);
  }

  return fallback;
}