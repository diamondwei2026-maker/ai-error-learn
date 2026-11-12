/** 题干哈希工具：标准化 → SHA-256，用于精确去重检测。
 *
 * 标准化目的：消除 OCR 细微差异（全角/半角、空白、换行），
 * 确保相同题干的不同录入形式得到同一哈希值。
 * 不做数学公式符号的语义等价（× vs * vs x），那是语义相似度范畴。
 */

/** 标准化题干：NFKC 全角→半角、空白合并、换行合并、去首尾空白 */
export function normalizeForHash(text: string): string {
  if (!text) return "";
  // 全角字符 → 半角（NFKC 同时处理兼容性分解 + 组合）
  let normalized = text.normalize("NFKC");
  // 所有非换行空白 → 单空格
  normalized = normalized.replace(/[^\S\n]+/g, " ");
  // 连续 3+ 换行 → 2 个
  normalized = normalized.replace(/\n{3,}/g, "\n\n");
  return normalized.trim();
}

/** 计算标准化后题干的 SHA-256（返回 64 字符 hex 小写字符串） */
export async function computeContentHash(text: string): Promise<string> {
  const normalized = normalizeForHash(text);
  if (!normalized) return "";
  // 用 Web Crypto API（Taro/H5/小程序均可用）
  const encoder = new TextEncoder();
  const data = encoder.encode(normalized);
  const hashBuffer = await crypto.subtle.digest("SHA-256", data);
  const hashArray = Array.from(new Uint8Array(hashBuffer));
  return hashArray
    .map((b) => b.toString(16).padStart(2, "0"))
    .join("");
}
