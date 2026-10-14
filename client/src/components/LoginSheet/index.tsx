import React from 'react';
import { Text, View } from '@tarojs/components';

import AppButton from '@/components/AppButton';

import styles from './index.module.scss';

export interface LoginSheetProps {
  visible: boolean;
  onLogin: () => void;
  onCancel: () => void;
  title?: string;
  description?: string;
}

const DEFAULT_TITLE = '登录后使用拍照识别';
const DEFAULT_DESCRIPTION = '识别题目需要登录账号，登录后还可在多设备同步错题';

/** 登录引导底部弹层：遮罩 + 毛玻璃面板（复用 ActionSheet 的面板规范，不改动 ActionSheet 本身） */
const LoginSheet = ({
  visible,
  onLogin,
  onCancel,
  title = DEFAULT_TITLE,
  description = DEFAULT_DESCRIPTION,
}: LoginSheetProps) => {
  if (!visible) return null;

  return (
    <>
      <View className={styles.mask} onClick={onCancel} />
      <View className={styles.sheet}>
        <Text className={styles.title}>{title}</Text>
        <Text className={styles.desc}>{description}</Text>
        <AppButton onClick={onLogin}>微信一键登录</AppButton>
        <AppButton variant="text" className={styles.cancel} onClick={onCancel}>
          暂不登录
        </AppButton>
      </View>
    </>
  );
};

export default LoginSheet;
