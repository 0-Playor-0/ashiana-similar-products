export function formatPrice(priceInr: number | null): string {
  if (priceInr == null) return "Price unavailable";
  return `₹${priceInr.toLocaleString("en-IN")}`;
}
