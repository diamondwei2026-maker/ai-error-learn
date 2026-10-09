import React, { useRef, useState } from 'react';
import { Text, View } from '@tarojs/components';
import type { ITouchEvent } from '@tarojs/components';
import classnames from 'classnames';

import styles from './index.module.scss';
import { toUnit } from '@/utils/layout';

export interface SwipeItemProps {
  /** 是否处于左滑展开态（受控） */
  open: boolean;
  onOpen: () => void;
  onClose: () => void;
  onDelete: () => void;
  children: React.ReactNode;
  className?: string;
}

const ACTION_WIDTH = 76; // 与原型一致：76px

/** 列表项左滑删除：左移 76px 露出删除按钮 */
const SwipeItem = ({ open, onOpen, onClose, onDelete, children, className }: SwipeItemProps) => {
  const startX = useRef(0);
  const [dragging, setDragging] = useState(false);
  const [offset, setOffset] = useState(0);

  const handleTouchStart = (event: ITouchEvent) => {
    startX.current = event.touches[0].clientX;
    setDragging(true);
  };

  const handleTouchMove = (event: ITouchEvent) => {
    if (!dragging) return;
    const delta = event.touches[0].clientX - startX.current;
    const base = open ? -ACTION_WIDTH : 0;
    const next = Math.min(0, Math.max(-ACTION_WIDTH, base + delta));
    setOffset(next);
  };

  const handleTouchEnd = () => {
    if (!dragging) return;
    setDragging(false);
    const shouldOpen = offset < -ACTION_WIDTH / 2;
    setOffset(0);
    if (shouldOpen) onOpen();
    else onClose();
  };

  const translate = dragging ? offset : open ? -ACTION_WIDTH : 0;

  return (
    <View className={classnames(styles.swipe, className)}>
      <View className={styles.deleteAction} onClick={onDelete}>
        <Text className={styles.deleteText}>删除</Text>
      </View>
      <View
        className={styles.content}
        style={{
          transform: `translateX(${toUnit(translate * 2)})`,
          transition: dragging ? 'none' : 'transform 0.28s cubic-bezier(0.22, 0.61, 0.36, 1)',
        }}
        onTouchStart={handleTouchStart}
        onTouchMove={handleTouchMove}
        onTouchEnd={handleTouchEnd}
        onTouchCancel={handleTouchEnd}
      >
        {children}
      </View>
    </View>
  );
};

export default SwipeItem;
