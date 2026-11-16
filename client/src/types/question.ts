/** 识题元信息（识别时自动产出，存量题可能缺失） */
export interface QuestionMeta {
  /** 学科：math / physics / chemistry / other */
  subject?: string
  /** 题型：选择题 / 填空题 / 解答题 / 证明题 / 其他 */
  questionType?: string
  /** 知识点标签（≤3 条） */
  knowledgePoints?: string[]
}

/** 错题记录（MVP 最小数据维度，对齐方案设计文档 §4.1） */
export interface Question extends QuestionMeta {
  /** 唯一 ID（时间戳 + 随机串） */
  id: string
  /** 纯文本题干（必填） */
  content: string
  /** 答案（可空字符串） */
  answer: string
  /** 本地文件路径（压缩后的原图）；H5 预览为 base64 dataURL 的存储键 */
  imagePath?: string
  /** 图片字节数，用于容量统计 */
  imageSize?: number
  /** 创建时间戳 */
  createdAt: number
  /** 更新时间戳 */
  updatedAt: number
  /** 标准化题干的 SHA-256（64 字符），去重用；存量题可能缺失 */
  contentHash?: string
}

/** 应用级元数据 */
export interface AppMeta {
  /** 数据结构版本，用于未来迁移 */
  schemaVersion: number
  /** 本地图片累计占用（字节） */
  imageBytes: number
  /** 题目总数（冗余缓存，加速列表） */
  questionCount: number
}
