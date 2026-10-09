import React from 'react';
import { Image } from '@tarojs/components';
import classnames from 'classnames';

import {
  MASCOT_DATA_URI,
  MASCOT_DONE_DATA_URI,
  MASCOT_EMPTY_DATA_URI,
} from '@/constants/mascot';
import { toUnit } from '@/utils/layout';

import styles from './index.module.scss';

export interface MascotProps {
  /** default=品牌/等待；empty=空态；done=完成页庆祝 */
  variant?: 'default' | 'empty' | 'done';
  /** 宽度（px，375 基准） */
  width: number;
  /** 高度（px，375 基准） */
  height: number;
  /** 4.5s 上下浮动，遵循 prefers-reduced-motion */
  float?: boolean;
  className?: string;
}

const SOURCE: Record<string, string> = {
  default: MASCOT_DATA_URI,
  empty: MASCOT_EMPTY_DATA_URI,
  done: MASCOT_DONE_DATA_URI,
};

/** 卡通形象「小错题本」 */
const Mascot = ({ variant = 'default', width, height, float = true, className }: MascotProps) => (
  <Image
    className={classnames(styles.mascot, float && styles.floaty, className)}
    src={SOURCE[variant]}
    mode="aspectFit"
    style={{ width: toUnit(width * 2), height: toUnit(height * 2) }}
  />
);

export default Mascot;
