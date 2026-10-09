import React from 'react';
import { Image, Text, View } from '@tarojs/components';
import classnames from 'classnames';

import Icon from '@/components/Icon';
import { fileRepo } from '@/services/repo/fileRepo';
import type { Question } from '@/types/question';
import { formatTime } from '@/utils/format';

import styles from './index.module.scss';

export interface QuestionCardProps {
  question: Question;
  onClick?: () => void;
  onLongPress?: () => void;
  className?: string;
}

/** 题库列表卡片：2 行截断题干 + 含原图角标 + 时间 */
const QuestionCard = ({ question, onClick, onLongPress, className }: QuestionCardProps) => {
  const thumb = fileRepo.resolveImageSrc(question.imagePath);
  const hasImage = Boolean(question.imagePath);

  return (
    <View className={classnames(styles.card, className)} onClick={onClick} onLongPress={onLongPress}>
      <View className={styles.stem}>{question.content}</View>
      <View className={styles.foot}>
        {hasImage ? (
          <View className={styles.imageMeta}>
            <View className={styles.thumb}>
              <Image className={styles.thumbImg} src={thumb} mode="aspectFill" />
            </View>
            <Text className={styles.metaText}>含原图</Text>
          </View>
        ) : (
          <View className={styles.imageMeta}>
            <Icon name="imageOffMuted" size={14} />
            <Text className={styles.metaText}>无原图</Text>
          </View>
        )}
        <Text className={styles.time}>{formatTime(question.createdAt)}</Text>
      </View>
    </View>
  );
};

export default QuestionCard;
