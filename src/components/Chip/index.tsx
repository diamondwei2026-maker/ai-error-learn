import React, { type ReactNode } from 'react';
import { View } from '@tarojs/components';
import classnames from 'classnames';

import styles from './index.module.scss';

export interface ChipProps {
  /** 语义：绿色（正向）/ 蓝色（复习）/ 橙色（提醒）/ 中性 */
  type?: 'green' | 'blue' | 'orange' | 'neutral';
  children: ReactNode;
  className?: string;
}

/** 标签（Chip）：圆角胶囊，高 22px，字号 12/600 */
const Chip = ({ type = 'neutral', children, className }: ChipProps) => (
  <View className={classnames(styles.chip, styles[type], className)}>{children}</View>
);

export default Chip;
