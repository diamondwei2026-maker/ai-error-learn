import React from 'react';
import { Text, View } from '@tarojs/components';
import Taro from '@tarojs/taro';

import { getNavLayout, toUnit } from '@/utils/layout';
import Icon from '@/components/Icon';

import styles from './index.module.scss';

export interface NavBarProps {
  title: string;
  showBack?: boolean;
  /** 自定义返回行为（默认 navigateBack） */
  onBack?: () => void;
  /** 右侧文字操作（如「编辑」「重拍」） */
  rightText?: string;
  onRightClick?: () => void;
  /** 右侧自定义节点（如计时器） */
  rightSlot?: React.ReactNode;
}

/** 自定义导航栏：毛玻璃①，微信端自动避让胶囊按钮 */
const NavBar = ({
  title,
  showBack = false,
  onBack,
  rightText,
  onRightClick,
  rightSlot,
}: NavBarProps) => {
  const layout = getNavLayout();

  const handleBack = () => {
    if (onBack) {
      onBack();
      return;
    }
    Taro.navigateBack({ delta: 1 }).catch(() => {
      Taro.switchTab({ url: '/pages/index/index' });
    });
  };

  return (
    <>
      <View className={styles.navbar} style={{ paddingTop: toUnit(layout.statusBarHeight * 2) }}>
        <View className={styles.bar} style={{ height: toUnit(layout.navHeight * 2) }}>
          {showBack ? (
            <View className={styles.back} onClick={handleBack}>
              <Icon name="chevronLeftInk" size={24} />
            </View>
          ) : null}
          <Text className={styles.title}>{title}</Text>
          {rightSlot ? (
            <View className={styles.action} style={{ right: toUnit(layout.rightInset * 2) }}>
              {rightSlot}
            </View>
          ) : rightText ? (
            <Text
              className={styles.actionText}
              style={{ right: toUnit(layout.rightInset * 2) }}
              onClick={onRightClick}
            >
              {rightText}
            </Text>
          ) : null}
        </View>
      </View>
      <View
        className={styles.spacer}
        style={{ height: toUnit((layout.statusBarHeight + layout.navHeight) * 2) }}
      />
    </>
  );
};

export default NavBar;
