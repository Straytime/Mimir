export function fmt02(n: number | null | undefined): string {
  if (n === null || n === undefined) {
    return "??";
  }

  return String(n).padStart(2, "0");
}
