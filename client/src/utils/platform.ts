/** 运行端判定（编译期常量，非微信端会被 tree shaking 剔除相关分支） */
export const isWeapp = process.env.TARO_ENV === 'weapp'
export const isH5 = process.env.TARO_ENV === 'h5'

/** 是否支持微信文件系统（仅 weapp） */
export const supportsFileSystem = isWeapp
