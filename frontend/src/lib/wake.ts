// Pure wake-phrase matching (no browser APIs) so it can be unit-tested.
function lev(a: string, b: string): number {
  const d = Array.from({ length: a.length + 1 }, (_, i) => [i, ...Array(b.length).fill(0)]);
  for (let j = 1; j <= b.length; j++) d[0][j] = j;
  for (let i = 1; i <= a.length; i++) for (let j = 1; j <= b.length; j++)
    d[i][j] = Math.min(d[i - 1][j] + 1, d[i][j - 1] + 1, d[i - 1][j - 1] + (a[i - 1] === b[j - 1] ? 0 : 1));
  return d[a.length][b.length];
}
const GREET = new Set(["hey", "hi", "hello", "okay", "ok", "hay", "yo", "hei", "ey"]);

/** "Hey Nila, what's the time" -> { matched: true, rest: "what's the time" }. Tolerates mis-hearings of the name. */
export function matchWake(transcript: string, name: string): { matched: boolean; rest: string } {
  const words = transcript.toLowerCase().replace(/[^\p{L}\p{N}\s']/gu, " ").split(/\s+/).filter(Boolean);
  const n = name.toLowerCase().replace(/[^\p{L}\p{N}]/gu, "");
  if (!n) return { matched: false, rest: "" };
  const tol = n.length >= 6 ? 2 : n.length >= 4 ? 1 : 0;
  for (let i = 0; i < words.length - 1; i++) {
    if (GREET.has(words[i]) && lev(words[i + 1], n) <= tol) return { matched: true, rest: words.slice(i + 2).join(" ") };
  }
  // greeting glued to the name by the recogniser: "heynila"
  for (let i = 0; i < words.length; i++) for (const g of GREET) if (words[i].startsWith(g) && lev(words[i].slice(g.length), n) <= tol && words[i].length > g.length) return { matched: true, rest: words.slice(i + 1).join(" ") };
  return { matched: false, rest: "" };
}

