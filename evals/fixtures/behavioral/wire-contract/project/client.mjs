export function parseReceipt(payload) {
  return `${payload.amount} ${payload.currency}`;
}
