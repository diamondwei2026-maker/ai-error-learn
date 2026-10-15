import React, { useEffect, useState } from 'react';
import { Image, Text, View } from '@tarojs/components';
import Taro, { useDidShow } from '@tarojs/taro';
import classnames from 'classnames';

import AppButton from '@/components/AppButton';
import Chip from '@/components/Chip';
import Empty from '@/components/Empty';
import FlipCard from '@/components/FlipCard';
import Icon from '@/components/Icon';
import Mascot from '@/components/Mascot';
import NavBar from '@/components/NavBar';
import PrivacySheet from '@/components/PrivacySheet';
import { questionService } from '@/services/questionService';
import { fileRepo } from '@/services/repo/fileRepo';
import type { Question } from '@/types/question';
import { formatDuration } from '@/utils/format';
import { getPageMinHeight } from '@/utils/layout';

import styles from './index.module.scss';

type Phase = 'loading' | 'card' | 'empty' | 'done';

const QuizPage = () => {
  const [phase, setPhase] = useState<Phase>('loading');
  const [current, setCurrent] = useState<Question | null>(null);
  const [flipped, setFlipped] = useState(false);
  const [roundTotal, setRoundTotal] = useState(0);
  const [index, setIndex] = useState(1);
  const [seconds, setSeconds] = useState(0);

  const startRound = () => {
    const count = questionService.count();
    if (count === 0) {
      setCurrent(null);
      setPhase('empty');
      return;
    }
    questionService.resetRound();
    const first = questionService.pickRandom();
    if (!first) {
      setCurrent(null);
      setPhase('empty');
      return;
    }
    setRoundTotal(count);
    setIndex(1);
    setSeconds(0);
    setFlipped(false);
    setCurrent(first);
    setPhase('card');
  };

  useDidShow(() => {
    startRound();
  });

  // 本轮计时
  useEffect(() => {
    if (phase !== 'card') return undefined;
    const timer = setInterval(() => setSeconds((value) => value + 1), 1000);
    return () => clearInterval(timer);
  }, [phase]);

  const goNext = () => {
    if (!current) return;
    if (index >= roundTotal) {
      setPhase('done');
      return;
    }
    const nextQuestion = questionService.pickRandom([current.id]);
    setIndex(index + 1);
    setFlipped(false);
    setCurrent(nextQuestion || null);
  };

  const progress = roundTotal > 0 ? Math.round((index / roundTotal) * 100) : 0;
  const imageSrc = current ? fileRepo.resolveImageSrc(current.imagePath) : '';

  const previewImage = () => {
    if (!imageSrc) return;
    Taro.previewImage({ urls: [imageSrc], current: imageSrc });
  };

  const gotoIndex = () => {
    Taro.switchTab({ url: '/pages/index/index' });
  };

  const gotoLibrary = () => {
    Taro.switchTab({ url: '/pages/library/index' });
  };

  if (phase === 'empty') {
    return (
      <View className={styles.page} style={{ minHeight: getPageMinHeight() }}>
        <NavBar title="刷题" />
        <View className={styles.body}>
          <Empty
            title="还没有错题"
            description="先录入几道错题，再回来随机抽题复习吧。"
            actionText="去录入错题"
            onAction={gotoIndex}
          />
        </View>

        <PrivacySheet />
      </View>
    );
  }

  if (phase === 'done') {
    return (
      <View className={styles.page} style={{ minHeight: getPageMinHeight() }}>
        <NavBar title="刷题" />
        <View className={styles.doneBody}>
          <View className={styles.doneMain}>
            <Mascot variant="done" width={220} height={180} />
            <Text className={styles.doneTitle}>本轮完成！</Text>
            <Text className={styles.doneSub}>你复习了本轮全部 {roundTotal} 道错题</Text>

            <View className={styles.statCard}>
              <View className={styles.statCell}>
                <Text className={styles.statNumber}>{roundTotal}</Text>
                <Text className={styles.statLabel}>本轮题数（道）</Text>
              </View>
              <View className={styles.statDivider} />
              <View className={styles.statCell}>
                <Text className={styles.statNumber}>{formatDuration(seconds)}</Text>
                <Text className={styles.statLabel}>本轮用时</Text>
              </View>
            </View>

            <View className={styles.doneHint}>
              <Icon name="clockMuted" size={14} />
              <Text className={styles.doneHintText}>坚持复习，进步会累积成看得见的曲线</Text>
            </View>
          </View>

          <View className={styles.doneActions}>
            <AppButton onClick={startRound}>再来一轮</AppButton>
            <AppButton variant="ghost" className={styles.doneActionsSecond} onClick={gotoLibrary}>
              返回题库
            </AppButton>
          </View>
        </View>

        <PrivacySheet />
      </View>
    );
  }

  if (phase === 'loading' || !current) {
    return (
      <View className={styles.page} style={{ minHeight: getPageMinHeight() }}>
        <NavBar title="刷题" />
        <View className={styles.body} />

        <PrivacySheet />
      </View>
    );
  }

  const front = (
    <View className={styles.faceCard}>
      <Text className={styles.watermark}>{String(index).padStart(2, '0')}</Text>
      <View className={styles.chipRow}>
        <Chip type="blue">复习模式</Chip>
      </View>
      <View className={styles.frontStem}>{current.content}</View>
      <View className={styles.masked}>
        <Icon name="lockMuted" size={26} />
        <Text className={styles.maskedPrimary}>答案已遮挡</Text>
        <Text className={styles.maskedHint}>点击卡片翻面查看答案与原图</Text>
      </View>
    </View>
  );

  const back = (
    <View className={classnames(styles.faceCard, styles.faceCardBack)}>
      <View className={styles.chipRow}>
        <Chip type="blue">复习模式</Chip>
      </View>
      <View className={styles.backStem}>{current.content}</View>
      <View className={styles.backDivider} />
      <View className={styles.answerLabel}>
        <Icon name="checkCircleInk" size={14} />
        <Text className={styles.answerLabelText}>答案</Text>
      </View>
      <View className={styles.answerBox}>
        <Text className={styles.answerText}>{current.answer || '（未填写答案）'}</Text>
      </View>
      {imageSrc ? (
        <>
          <View className={styles.imageHead}>
            <Text className={styles.imageLabel}>原图</Text>
            <Text className={styles.link} onClick={previewImage}>
              点击查看大图
            </Text>
          </View>
          <View className={styles.imageBox} onClick={previewImage}>
            <Image className={styles.image} src={imageSrc} mode="aspectFill" />
          </View>
        </>
      ) : null}
    </View>
  );

  return (
    <View className={styles.page} style={{ minHeight: getPageMinHeight() }}>
      <NavBar
        title="刷题"
        rightSlot={
          <Text className={classnames(styles.timer, styles.num)}>{formatDuration(seconds)}</Text>
        }
      />

      <View className={styles.body}>
        <View className={styles.progressRow}>
          <View className={styles.progressText}>
            <Text className={styles.progressLabel}>第</Text>
            <Text className={classnames(styles.progressIndex, styles.num)}>{index}</Text>
            <Text className={classnames(styles.progressTotal, styles.num)}>/ {roundTotal}</Text>
            <Text className={styles.progressLabel}>题</Text>
          </View>
          {flipped ? (
            <Chip type="green">
              <Icon name="checkInk" size={11} className={styles.chipIcon} />
              已翻面
            </Chip>
          ) : (
            <Chip type="blue">复习模式</Chip>
          )}
        </View>

        <View className={styles.bar}>
          <View className={styles.barInner} style={{ width: `${progress}%` }} />
        </View>

        <FlipCard
          flipped={flipped}
          front={front}
          back={back}
          height={420}
          onFlip={() => setFlipped((value) => !value)}
        />

        <View className={styles.flipHint}>
          <Icon name="refreshMuted" size={14} />
          <Text className={styles.flipHintText}>
            {flipped ? '点击卡片或按「收起答案」回到正面（0.4s）' : '点击卡片或按「显示答案」翻面（0.4s）'}
          </Text>
        </View>

        <View className={styles.actions}>
          {flipped ? (
            <>
              <AppButton onClick={goNext}>下一题</AppButton>
              <AppButton
                variant="text"
                className={styles.actionsSecond}
                onClick={() => setFlipped(false)}
              >
                收起答案
              </AppButton>
            </>
          ) : (
            <>
              <AppButton onClick={() => setFlipped(true)}>显示答案</AppButton>
              <AppButton variant="text" className={styles.actionsSecond} onClick={goNext}>
                下一题
              </AppButton>
            </>
          )}
        </View>
      </View>

      <PrivacySheet />
    </View>
  );
};

export default QuizPage;
