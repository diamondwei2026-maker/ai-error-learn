import React, { type ReactNode } from 'react';
import { Button } from '@tarojs/components';
import classnames from 'classnames';

import styles from './index.module.scss';
import { toUnit } from '@/utils/layout';

export interface AppButtonProps {
  variant?: 'primary' | 'ghost' | 'text' | 'danger';
  children: ReactNode;
  onClick?: () => void;
  disabled?: boolean;
  /** 宽度（px，375 基准）；不传则撑满 */
  width?: number;
  icon?: ReactNode;
  className?: string;
}

/** 通用按钮：胶囊主按钮 / 次按钮 / 文字按钮 / 危险按钮（对齐 §3.5） */
const AppButton = ({
  variant = 'primary',
  children,
  onClick,
  disabled = false,
  width,
  icon,
  className,
}: AppButtonProps) => (
  <Button
    className={classnames(
      styles.btn,
      styles[variant],
      disabled && styles.disabled,
      className,
    )}
    style={width ? { width: toUnit(width * 2) } : undefined}
    hoverClass="none"
    disabled={disabled}
    onClick={() => {
      if (disabled) return;
      onClick?.();
    }}
  >
    {icon}
    {children}
  </Button>
);

export default AppButton;
