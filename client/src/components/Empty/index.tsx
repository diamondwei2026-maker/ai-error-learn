import React from 'react';
import { Text, View } from '@tarojs/components';
import classnames from 'classnames';

import AppButton from '@/components/AppButton';
import Mascot from '@/components/Mascot';

import styles from './index.module.scss';

export interface EmptyProps {
  title: string;
  description: string;
  actionText?: string;
  onAction?: () => void;
  className?: string;
}

/** 空态：卡通形象 + 主副文案 + 行动按钮，整体垂直居中 */
const Empty = ({ title, description, actionText, onAction, className }: EmptyProps) => (
  <View className={classnames(styles.empty, className)}>
    <Mascot variant="empty" width={220} height={170} />
    <Text className={styles.title}>{title}</Text>
    <Text className={styles.desc}>{description}</Text>
    {actionText ? (
      <AppButton width={220} className={styles.action} onClick={onAction}>
        {actionText}
      </AppButton>
    ) : null}
  </View>
);

export default Empty;
