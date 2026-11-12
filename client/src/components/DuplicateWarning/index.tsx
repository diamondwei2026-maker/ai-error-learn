import React from 'react';
import { Text, View } from '@tarojs/components';

import Icon from '@/components/Icon';
import type { Question } from '@/types/question';
import { formatTime } from '@/utils/format';

import styles from './index.module.scss';

export interface DuplicateWarningProps {
  visible: boolean;
  /** 重复题目列表（按创建时间倒序） */
  duplicates: Question[];
  /** 已录入题干预览长度（字符数） */
  previewChars?: number;
  onView: (question: Question) => void;
  onSaveAnyway: () => void;
  onCancel: () => void;
}

/** 重复录入提醒弹窗：温和提醒，用户决定是否继续保存 */
const DuplicateWarning = ({
  visible,
  duplicates,
  previewChars = 60,
  onView,
  onSaveAnyway,
  onCancel,
}: DuplicateWarningProps) => {
  if (!visible || duplicates.length === 0) return null;

  const first = duplicates[0];
  const preview =
    first.content.length > previewChars
      ? first.content.slice(0, previewChars) + '…'
      : first.content;

  return (
    <>
      <View className={styles.mask} onClick={onCancel} />
      <View className={styles.wrap}>
        <View className={styles.dialog}>
          <View className={styles.body}>
            <View className={styles.warnIco}>
              <Icon name="warningRed" size={26} />
            </View>
            <Text className={styles.title}>这道题好像已经记录过了</Text>
            <Text className={styles.meta}>
              你之前在 {formatTime(first.createdAt)} 录入过：
            </Text>
            <View className={styles.previewBox}>
              <Text className={styles.previewText}>{preview}</Text>
            </View>
            {duplicates.length > 1 && (
              <Text className={styles.more}>
                还有 {duplicates.length - 1} 条相似记录
              </Text>
            )}
          </View>
          <View className={styles.foot}>
            <View
              className={styles.btn}
              onClick={() => first && onView(first)}
            >
              <Text>查看已录入</Text>
            </View>
            <View className={styles.divider} />
            <View className={styles.btnPrimary} onClick={onSaveAnyway}>
              <Text>仍然保存</Text>
            </View>
            <View className={styles.divider} />
            <View className={styles.btn} onClick={onCancel}>
              <Text>取消</Text>
            </View>
          </View>
        </View>
      </View>
    </>
  );
};

export default DuplicateWarning;
