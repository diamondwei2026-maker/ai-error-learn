import React from 'react';
import { Image } from '@tarojs/components';
import classnames from 'classnames';

import { ICONS, type IconName } from '@/constants/icons';
import { toUnit } from '@/utils/layout';

import styles from './index.module.scss';

export interface IconProps {
  name: IconName;
  /** 尺寸（px，375 基准），默认 24 */
  size?: number;
  className?: string;
  style?: React.CSSProperties;
}

/** 线性图标：以 base64 SVG data URI 渲染，颜色已固化在 variant 中 */
const Icon = ({ name, size = 24, className, style }: IconProps) => (
  <Image
    className={classnames(styles.icon, className)}
    src={ICONS[name]}
    mode="aspectFit"
    style={{ width: toUnit(size * 2), height: toUnit(size * 2), ...style }}
  />
);

export default Icon;
