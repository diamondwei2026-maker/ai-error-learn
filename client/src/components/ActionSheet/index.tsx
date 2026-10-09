import React, { type ReactNode } from 'react';
import { Text, View } from '@tarojs/components';

import styles from './index.module.scss';

export interface ActionSheetItem {
  key: string;
  label: string;
  icon?: ReactNode;
}

export interface ActionSheetProps {
  visible: boolean;
  title?: string;
  items: ActionSheetItem[];
  onSelect: (key: string) => void;
  onCancel: () => void;
}

/** 底部弹层：遮罩 + 毛玻璃④面板（录入方式选择等） */
const ActionSheet = ({ visible, title, items, onSelect, onCancel }: ActionSheetProps) => {
  if (!visible) return null;

  return (
    <>
      <View className={styles.mask} onClick={onCancel} />
      <View className={styles.sheet}>
        {title ? <Text className={styles.title}>{title}</Text> : null}
        {items.map((item) => (
          <View key={item.key} className={styles.item} onClick={() => onSelect(item.key)}>
            {item.icon}
            <Text className={styles.itemLabel}>{item.label}</Text>
          </View>
        ))}
        <View className={styles.cancel} onClick={onCancel}>
          <Text className={styles.cancelText}>取消</Text>
        </View>
      </View>
    </>
  );
};

export default ActionSheet;
