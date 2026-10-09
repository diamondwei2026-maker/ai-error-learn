import Taro from '@tarojs/taro'

import { isWeapp } from '@/utils/platform'

/** H5 降级：图片以 base64 dataURL 存入 Storage，Key 形如 q:img:{id} */
const H5_IMAGE_PREFIX = 'q:img:'
/** weapp：本地文件系统命名前缀 */
const WEAPP_FILE_PREFIX = 'q_'

export interface SavedImage {
  /** weapp 为 wxfile:// 本地路径；H5 为 Storage Key */
  path: string
  /** 字节数 */
  size: number
}

function userDataPath(): string {
  const env = (Taro as unknown as { env?: { USER_DATA_PATH?: string } }).env
  return env?.USER_DATA_PATH || ''
}

function weappFileManager() {
  return Taro.getFileSystemManager()
}

async function h5ToDataUrl(tempPath: string): Promise<string> {
  const response = await fetch(tempPath)
  const blob = await response.blob()
  return await new Promise<string>((resolve, reject) => {
    const reader = new FileReader()
    reader.onload = () => resolve(String(reader.result || ''))
    reader.onerror = () => reject(reader.error)
    reader.readAsDataURL(blob)
  })
}

/**
 * 本地文件访问层：weapp 走文件系统，H5（预览降级）走 Storage。
 * 对外接口签名一致，未来切换云端实现只需替换本模块。
 */
export const fileRepo = {
  /** 保存错题原图，返回持久化路径与字节数 */
  async saveImage(tempPath: string, id: string): Promise<SavedImage> {
    if (isWeapp) {
      const fs = weappFileManager()
      const dir = userDataPath()
      const dest = `${dir}/${WEAPP_FILE_PREFIX}${id}.jpg`
      fs.copyFileSync(tempPath, dest)
      let size = 0
      try {
        size = fs.statSync(dest).size
      } catch (error) {
        console.error('[fileRepo] stat failed', error)
      }
      return { path: dest, size }
    }

    const dataUrl = await h5ToDataUrl(tempPath)
    const key = `${H5_IMAGE_PREFIX}${id}`
    Taro.setStorageSync(key, dataUrl)
    // base64 字符数 → 近似字节数
    return { path: key, size: Math.round((dataUrl.length * 3) / 4) }
  },

  /** 删除原图 */
  removeImage(path?: string): void {
    if (!path) return
    try {
      if (isWeapp) {
        weappFileManager().unlinkSync(path)
      } else {
        Taro.removeStorageSync(path)
      }
    } catch (error) {
      console.error('[fileRepo] removeImage failed', error)
    }
  },

  /** 计算本地图片累计占用（字节） */
  calcUsage(): number {
    let total = 0
    try {
      if (isWeapp) {
        const fs = weappFileManager()
        const dir = userDataPath()
        fs.readdirSync(dir).forEach((name) => {
          if (!name.startsWith(WEAPP_FILE_PREFIX)) return
          try {
            total += fs.statSync(`${dir}/${name}`).size
          } catch (error) {
            console.error('[fileRepo] stat usage failed', error)
          }
        })
      } else {
        const info = Taro.getStorageInfoSync()
        info.keys.forEach((key) => {
          if (!key.startsWith(H5_IMAGE_PREFIX)) return
          const value = Taro.getStorageSync(key)
          if (typeof value === 'string') total += Math.round((value.length * 3) / 4)
        })
      }
    } catch (error) {
      console.error('[fileRepo] calcUsage failed', error)
    }
    return total
  },

  /** 清理无主图片（不在有效路径集合中的本地文件） */
  clearOrphans(validPaths: string[]): void {
    const valid = new Set(validPaths.filter(Boolean))
    try {
      if (isWeapp) {
        const fs = weappFileManager()
        const dir = userDataPath()
        fs.readdirSync(dir).forEach((name) => {
          if (!name.startsWith(WEAPP_FILE_PREFIX)) return
          const full = `${dir}/${name}`
          if (!valid.has(full)) fs.unlinkSync(full)
        })
      } else {
        Taro.getStorageInfoSync().keys.forEach((key) => {
          if (key.startsWith(H5_IMAGE_PREFIX) && !valid.has(key)) {
            Taro.removeStorageSync(key)
          }
        })
      }
    } catch (error) {
      console.error('[fileRepo] clearOrphans failed', error)
    }
  },

  /** 解析为 Image 组件可直接使用的 src */
  resolveImageSrc(path?: string): string {
    if (!path) return ''
    if (isWeapp) return path
    try {
      return (Taro.getStorageSync(path) as string) || ''
    } catch (error) {
      console.error('[fileRepo] resolveImageSrc failed', error)
      return ''
    }
  },

  /** 读取文件字节数（H5 降级返回 0） */
  getFileSize(path?: string): number {
    if (!path || !isWeapp) return 0
    try {
      return weappFileManager().statSync(path).size
    } catch (error) {
      console.error('[fileRepo] getFileSize failed', error)
      return 0
    }
  },
}
