import React from 'react';
import { Text, View } from '@tarojs/components';
import Taro from '@tarojs/taro';

import AppButton from '@/components/AppButton';
import Icon from '@/components/Icon';
import { AGREEMENT_PAGE_PATH, AGREEMENT_TYPE } from '@/constants';
import { privacyService } from '@/services/privacyService';
import { usePrivacyStore } from '@/store/privacyStore';

import styles from './index.module.scss';

/**
 * 隐私授权弹层（底部弹层，复用 LoginSheet 的面板规范）。
 * 需逐页挂载：小程序端 App 组件不渲染页面节点，弹层无法全局承载。
 */
const PrivacySheet = () => {
  const visible = usePrivacyStore((state) => state.visible);
  const contractName = usePrivacyStore((state) => state.contractName);
  const agree = usePrivacyStore((state) => state.agree);
  const disagree = usePrivacyStore((state) => state.disagree);

  if (!visible) return null;

  const gotoAgreement = (type: string) => {
    Taro.navigateTo({ url: `${AGREEMENT_PAGE_PATH}?type=${type}` });
  };

  return (
    <>
      <View className={styles.mask} />
      <View className={styles.sheet}>
        <Text className={styles.title}>用户隐私保护提示</Text>

        <Text className={styles.text}>
          感谢你使用「错题本」。在使用前，请阅读并同意
          <Text
            className={styles.link}
            onClick={() => gotoAgreement(AGREEMENT_TYPE.terms)}
          >
            《用户协议》
          </Text>
          和
          <Text
            className={styles.link}
            onClick={() => gotoAgreement(AGREEMENT_TYPE.privacy)}
          >
            《隐私政策》
          </Text>
          。
        </Text>

        <Text className={styles.text}>
          为了提供错题识别与多设备同步服务，我们会收集你主动选择的照片 / 相册图片、你的微信头像与昵称，以及微信登录标识用于账号识别。图片仅用于识别题目文字，不会用于其他用途。
        </Text>

        <View className={styles.contract} onClick={() => privacyService.openContract()}>
          <Text className={styles.contractText}>{contractName || '查看平台隐私协议'}</Text>
          <Icon name="chevronRightLink" size={14} />
        </View>

        <View className={styles.actions}>
          {/* 「同意」必须是原生按钮，微信会校验该按钮是否真被点击过 */}
          <AppButton openType="agreePrivacyAuthorization" onAgreePrivacyAuthorization={agree}>
            同意并继续
          </AppButton>
          <AppButton variant="text" className={styles.cancel} onClick={disagree}>
            暂不授权
          </AppButton>
        </View>
      </View>
    </>
  );
};

export default PrivacySheet;
