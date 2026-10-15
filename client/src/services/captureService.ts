import Taro from '@tarojs/taro';

import { PRIVACY_DENIED_MESSAGE } from '@/constants';
import { privacyService } from '@/services/privacyService';
import { isWeapp } from '@/utils/platform';

export type CaptureSource = 'camera' | 'album';

/** 题目采集：拍照/相册 → 压缩，返回可用的临时图片路径 */
export const captureService = {
  async pick(source: CaptureSource): Promise<string | undefined> {
    try {
      if (isWeapp) {
        // 隐私合规：拍照/相册属隐私接口，先确保已完成隐私授权；用户拒绝则给明确提示
        const authorized = await privacyService.requireAuthorize();
        if (!authorized) {
          Taro.showToast({ title: PRIVACY_DENIED_MESSAGE, icon: 'none' });
          return undefined;
        }
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
