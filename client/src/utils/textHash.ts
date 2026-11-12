/** 题干哈希工具：标准化 → SHA-256，用于精确去重检测。
 *
 * 标准化目的：消除 OCR 细微差异（全角/半角、空白、换行），
 * 确保相同题干的不同录入形式得到同一哈希值。
 * 不做数学公式符号的语义等价（× vs * vs x），那是语义相似度范畴。
 *
 * 实现说明：小程序真机运行时**没有** TextEncoder / crypto.subtle，
 * 因此这里使用纯 JS 的 UTF-8 编码与 SHA-256，保证真机可用且结果与标准实现一致。
 */

/** SHA-256 轮常量（标准 64 个） */
const SHA256_K = new Uint32Array([
  0x428a2f98, 0x71374491, 0xb5c0fbcf, 0xe9b5dba5, 0x3956c25b, 0x59f111f1,
  0x923f82a4, 0xab1c5ed5, 0xd807aa98, 0x12835b01, 0x243185be, 0x550c7dc3,
  0x72be5d74, 0x80deb1fe, 0x9bdc06a7, 0xc19bf174, 0xe49b69c1, 0xefbe4786,
  0x0fc19dc6, 0x240ca1cc, 0x2de92c6f, 0x4a7484aa, 0x5cb0a9dc, 0x76f988da,
  0x983e5152, 0xa831c66d, 0xb00327c8, 0xbf597fc7, 0xc6e00bf3, 0xd5a79147,
  0x06ca6351, 0x14292967, 0x27b70a85, 0x2e1b2138, 0x4d2c6dfc, 0x53380d13,
  0x650a7354, 0x766a0abb, 0x81c2c92e, 0x92722c85, 0xa2bfe8a1, 0xa81a664b,
  0xc24b8b70, 0xc76c51a3, 0xd192e819, 0xd6990624, 0xf40e3585, 0x106aa070,
  0x19a4c116, 0x1e376c08, 0x2748774c, 0x34b0bcb5, 0x391c0cb3, 0x4ed8aa4a,
  0x5b9cca4f, 0x682e6ff3, 0x748f82ee, 0x78a5636f, 0x84c87814, 0x8cc70208,
  0x90befffa, 0xa4506ceb, 0xbef9a3f7, 0xc67178f2,
]);

/** 标准化题干：NFKC 全角→半角、空白合并、换行合并、去首尾空白 */
export function normalizeForHash(text: string): string {
  if (!text) return "";
  let normalized = text;
  // 极老运行时可能不支持 Unicode 归一化，退化为原文，不能因此阻断后续流程
  try {
    if (typeof normalized.normalize === "function") {
      normalized = normalized.normalize("NFKC");
    }
  } catch (error) {
    console.warn("[textHash] normalize unsupported, fallback to raw text", error);
  }
  // 所有非换行空白 → 单空格
  normalized = normalized.replace(/[^\S\n]+/g, " ");
  // 连续 3+ 换行 → 2 个
  normalized = normalized.replace(/\n{3,}/g, "\n\n");
  return normalized.trim();
}

/** UTF-8 编码（替代真机不存在的 TextEncoder，含代理对处理） */
function utf8Encode(input: string): Uint8Array {
  const bytes: number[] = [];
  for (let i = 0; i < input.length; i += 1) {
    let code = input.charCodeAt(i);
    if (
      code >= 0xd800 &&
      code <= 0xdbff &&
      i + 1 < input.length &&
      input.charCodeAt(i + 1) >= 0xdc00 &&
      input.charCodeAt(i + 1) <= 0xdfff
    ) {
      code =
        0x10000 +
        ((code - 0xd800) << 10) +
        (input.charCodeAt(i + 1) - 0xdc00);
      i += 1;
    }
    if (code < 0x80) {
      bytes.push(code);
    } else if (code < 0x800) {
      bytes.push(0xc0 | (code >> 6), 0x80 | (code & 0x3f));
    } else if (code < 0x10000) {
      bytes.push(
        0xe0 | (code >> 12),
        0x80 | ((code >> 6) & 0x3f),
        0x80 | (code & 0x3f),
      );
    } else {
      bytes.push(
        0xf0 | (code >> 18),
        0x80 | ((code >> 12) & 0x3f),
        0x80 | ((code >> 6) & 0x3f),
        0x80 | (code & 0x3f),
      );
    }
  }
  return new Uint8Array(bytes);
}

/** 32 位循环右移 */
function rotr(value: number, shift: number): number {
  return (value >>> shift) | (value << (32 - shift));
}

/** 纯 JS SHA-256，返回 64 字符 hex 小写字符串 */
function sha256Hex(input: string): string {
  const bytes = utf8Encode(input);
  const bitLength = bytes.length * 8;

  // 填充：原文 + 0x80 + 若干 0 + 8 字节大端长度，总长为 64 的整数倍
  const paddedLength = (((bytes.length + 8) >> 6) + 1) * 64;
  const buffer = new Uint8Array(paddedLength);
  buffer.set(bytes);
  buffer[bytes.length] = 0x80;

  const highBits = Math.floor(bitLength / 0x100000000);
  const lowBits = bitLength >>> 0;
  const lengthOffset = paddedLength - 8;
  buffer[lengthOffset] = (highBits >>> 24) & 0xff;
  buffer[lengthOffset + 1] = (highBits >>> 16) & 0xff;
  buffer[lengthOffset + 2] = (highBits >>> 8) & 0xff;
  buffer[lengthOffset + 3] = highBits & 0xff;
  buffer[lengthOffset + 4] = (lowBits >>> 24) & 0xff;
  buffer[lengthOffset + 5] = (lowBits >>> 16) & 0xff;
  buffer[lengthOffset + 6] = (lowBits >>> 8) & 0xff;
  buffer[lengthOffset + 7] = lowBits & 0xff;

  const state = new Uint32Array([
    0x6a09e667, 0xbb67ae85, 0x3c6ef372, 0xa54ff53a, 0x510e527f, 0x9b05688c,
    0x1f83d9ab, 0x5be0cd19,
  ]);
  const words = new Uint32Array(64);

  for (let offset = 0; offset < paddedLength; offset += 64) {
    for (let i = 0; i < 16; i += 1) {
      const p = offset + i * 4;
      words[i] =
        ((buffer[p] << 24) |
          (buffer[p + 1] << 16) |
          (buffer[p + 2] << 8) |
          buffer[p + 3]) >>>
        0;
    }
    for (let i = 16; i < 64; i += 1) {
      const w15 = words[i - 15];
      const w2 = words[i - 2];
      const s0 = rotr(w15, 7) ^ rotr(w15, 18) ^ (w15 >>> 3);
      const s1 = rotr(w2, 17) ^ rotr(w2, 19) ^ (w2 >>> 10);
      words[i] = (words[i - 16] + s0 + words[i - 7] + s1) >>> 0;
    }

    let a = state[0];
    let b = state[1];
    let c = state[2];
    let d = state[3];
    let e = state[4];
    let f = state[5];
    let g = state[6];
    let h = state[7];

    for (let i = 0; i < 64; i += 1) {
      const s1 = rotr(e, 6) ^ rotr(e, 11) ^ rotr(e, 25);
      const ch = (e & f) ^ (~e & g);
      const temp1 = (h + s1 + ch + SHA256_K[i] + words[i]) >>> 0;
      const s0 = rotr(a, 2) ^ rotr(a, 13) ^ rotr(a, 22);
      const maj = (a & b) ^ (a & c) ^ (b & c);
      const temp2 = (s0 + maj) >>> 0;

      h = g;
      g = f;
      f = e;
      e = (d + temp1) >>> 0;
      d = c;
      c = b;
      b = a;
      a = (temp1 + temp2) >>> 0;
    }

    state[0] = (state[0] + a) >>> 0;
    state[1] = (state[1] + b) >>> 0;
    state[2] = (state[2] + c) >>> 0;
    state[3] = (state[3] + d) >>> 0;
    state[4] = (state[4] + e) >>> 0;
    state[5] = (state[5] + f) >>> 0;
    state[6] = (state[6] + g) >>> 0;
    state[7] = (state[7] + h) >>> 0;
  }

  let hex = "";
  for (let i = 0; i < 8; i += 1) {
    hex += `00000000${state[i].toString(16)}`.slice(-8);
  }
  return hex;
}

/** 计算标准化后题干的 SHA-256（返回 64 字符 hex 小写字符串） */
export async function computeContentHash(text: string): Promise<string> {
  const normalized = normalizeForHash(text);
  if (!normalized) return "";
  return sha256Hex(normalized);
}
