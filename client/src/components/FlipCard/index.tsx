import React, { type ReactNode } from 'react';
import { View } from '@tarojs/components';
import classnames from 'classnames';

import styles from './index.module.scss';
import { toUnit } from '@/utils/layout';

export interface FlipCardProps {
  flipped: boolean;
  front: ReactNode;
  back: ReactNode;
  /** 卡片高度（px，375 基准），默认 360 */
  height?: number;
  onFlip?: () => void;
}

/** 卡片翻面：纯 CSS 3D（perspective 1000px + rotateY 180° + 0.4s） */
const FlipCard = ({ flipped, front, back, height = 360, onFlip }: FlipCardProps) => (
  <View className={styles.flip} style={{ height: toUnit(height * 2) }} onClick={onFlip}>
    <View className={classnames(styles.inner, flipped && styles.isBack)}>
      <View className={classnames(styles.face, styles.front)}>{front}</View>
      <View className={classnames(styles.face, styles.back)}>{back}</View>
    </View>
  </View>
);

export default FlipCard;
