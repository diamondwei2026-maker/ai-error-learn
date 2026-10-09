import React from 'react';
import { Text, View } from '@tarojs/components';

import Icon from '@/components/Icon';

import styles from './index.module.scss';

export interface ConfirmDialogProps {
  visible: boolean;
  title: string;
  description: string;
  confirmText?: string;
  cancelText?: string;
  onConfirm: () => void;
  onCancel: () => void;
}

/** 二次确认弹窗：居中卡片 280px + 遮罩 + 警示图标 */
const ConfirmDialog = ({
  visible,
  title,
  description,
  confirmText = '删除',
  cancelText = '取消',
  onConfirm,
  onCancel,
}: ConfirmDialogProps) => {
  if (!visible) return null;

  return (
    <>
      <View className={styles.mask} onClick={onCancel} />
      <View className={styles.wrap}>
        <View className={styles.dialog}>
          <View className={styles.body}>
            <View className={styles.warnIco}>
              <Icon name="warningRed" size={26} />
            </View>
            <Text className={styles.title}>{title}</Text>
            <Text className={styles.desc}>{description}</Text>
          </View>
          <View className={styles.foot}>
            <View className={styles.cancel} onClick={onCancel}>
              <Text>{cancelText}</Text>
            </View>
            <View className={styles.confirm} onClick={onConfirm}>
              <Text>{confirmText}</Text>
            </View>
          </View>
        </View>
      </View>
    </>
  );
};

export default ConfirmDialog;
