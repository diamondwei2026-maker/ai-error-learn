import Taro from '@tarojs/taro';

import { isWeapp } from '@/utils/platform';

export type CaptureSource = 'camera' | 'album';

/** 题目采集：拍照/相册 → 压缩，返回可用的临时图片路径 */
export const captureService = {
  async pick(source: CaptureSource): Promise<string | undefined> {
    try {
      if (isWeapp) {
        const res = await Taro.chooseMedia({
          count: 1,
          mediaType: ['image'],
          sourceType: [source],
          sizeType: ['compressed'],
        });
        let path = res.tempFiles?.[0]?.tempFilePath || '';
        if (path) {
          try {
            const compressed = await Taro.compressImage({
              src: path,
              quality: 70,
              compressedWidth: 1080,
            });
            path = compressed.tempFilePath || path;
          } catch (error) {
            console.error('[captureService] compressImage failed', error);
          }
        }
        return path || undefined;
      }

      const res = await Taro.chooseImage({
        count: 1,
        sizeType: ['compressed'],
        sourceType: [source],
      });
      return res.tempFilePaths?.[0] || undefined;
    } catch (error) {
      console.error('[captureService] pick failed', error);
      return undefined;
    }
  },
};
