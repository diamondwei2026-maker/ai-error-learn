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
import { REVIEW_REMINDER_ENABLED } from '@/constants';
import { questionService } from '@/services/questionService';
import { fileRepo } from '@/services/repo/fileRepo';
import { reminderService } from '@/services/reminderService';
import { useUserStore } from '@/store/userStore';
import type { Question } from '@/types/question';
import { formatDuration } from '@/utils/format';
import { getPageMinHeight } from '@/utils/layout';
import { nextDueInfo, type NextDueInfo, type ReviewRating } from '@/utils/reviewSchedule';
import { syncQuizBadge } from '@/utils/tabBadge';

import styles from './index.module.scss';

type Phase = 'loading' | 'card' | 'emptyAll' | 'emptyDue' | 'done';

const EMPTY_NEXT_DUE: NextDueInfo = { at: null, count: 0, daysUntil: 0 };

const dueDayText = (info: NextDueInfo) =>
  info.daysUntil === 1 ? '明天' : `${info.daysUntil} 天后`;

const QuizPage = () => {
  const [phase, setPhase] = useState<Phase>('loading');
  const [queue, setQueue] = useState<Question[]>([]);
  const [current, setCurrent] = useState<Question | null>(null);
  const [flipped, setFlipped] = useState(false);
  const [index, setIndex] = useState(1);
  const [seconds, setSeconds] = useState(0);
  const [remembered, setRemembered] = useState(0);
  const [forgot, setForgot] = useState(0);
  const [nextDue, setNextDue] = useState<NextDueInfo>(EMPTY_NEXT_DUE);
  const [reminderOn, setReminderOn] = useState(false);
  const isLoggedIn = useUserStore((state) => state.isLoggedIn);

  const startRound = () => {
    const all = questionService.all();
    if (all.length === 0) {
      setQueue([]);
      setCurrent(null);
      setPhase('emptyAll');
      syncQuizBadge(0);
      return;
    }

    const due = questionService.listDue();
    if (due.length === 0) {
      setQueue([]);
      setCurrent(null);
      setNextDue(nextDueInfo(all));
      setPhase('emptyDue');
      syncQuizBadge(0);
      return;
    }

    setQueue(due);
    setCurrent(due[0]);
    setIndex(1);
    setSeconds(0);
    setFlipped(false);
    setRemembered(0);
    setForgot(0);
    setPhase('card');
    syncQuizBadge(due.length);
  };

  useDidShow(() => {
    setReminderOn(reminderService.isOn());
    startRound();
  });

  // 本轮计时
  useEffect(() => {
    if (phase !== 'card') return undefined;
    const timer = setInterval(() => setSeconds((value) => value + 1), 1000);
    return () => clearInterval(timer);
  }, [phase]);

  const finishRound = () => {
    setPhase('done');
    setNextDue(nextDueInfo(questionService.all()));
    syncQuizBadge(questionService.dueCount());
  };

  const goNext = () => {
    if (index >= queue.length) {
      finishRound();
      return;
    }
    setIndex(index + 1);
    setCurrent(queue[index]);
    setFlipped(false);
    syncQuizBadge(questionService.dueCount());
  };

  /** 自评：推进轮次并落库，随后进入下一题 */
  const handleRating = (rating: ReviewRating) => {
    if (!current) return;
    questionService.markReviewed(current.id, rating);
    if (rating === 'remembered') setRemembered((value) => value + 1);
    else setForgot((value) => value + 1);
    goNext();
  };

  const progress = queue.length > 0 ? Math.round((index / queue.length) * 100) : 0;
  const imageSrc = current ? fileRepo.resolveImageSrc(current.imagePath) : '';
  const roundStage = current?.reviewStage ?? 1;

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

  /** 完成页订阅引导：游客先登录，已开启则直接提示 */
  const handleSubscribe = async () => {
    if (!isLoggedIn) {
      Taro.showToast({ title: '请先登录后再开启提醒', icon: 'none' });
      return;
    }
    if (reminderOn) {
      Taro.showToast({ title: '提醒已开启', icon: 'none' });
      return;
    }
    const result = await reminderService.enable();
    setReminderOn(result.on);
    Taro.showToast({ title: result.message, icon: 'none' });
  };

  if (phase === 'emptyAll') {
    return (
      <View className={styles.page} style={{ minHeight: getPageMinHeight() }}>
        <NavBar title="刷题" />
        <View className={styles.body}>
          <Empty
            title="还没有错题"
            description="先录入几道错题，再回来按到期顺序复习吧。"
            actionText="去拍照录入"
            onAction={gotoIndex}
          />
        </View>

        <PrivacySheet />
      </View>
    );
  }

  if (phase === 'emptyDue') {
    return (
      <View className={styles.page} style={{ minHeight: getPageMinHeight() }}>
        <NavBar title="刷题" />
        <View className={styles.body}>
          <Empty
            title="今天没有要复习的题"
            description={
              nextDue.at
                ? `下次到期：${dueDayText(nextDue)} · 共 ${nextDue.count} 道`
                : '暂无后续复习安排'
            }
            actionText="去拍照录入"
            onAction={gotoIndex}
          />
        </View>

        <PrivacySheet />
      </View>
    );
  }

  if (phase === 'done') {
    const reviewed = remembered + forgot;
    return (
      <View className={styles.page} style={{ minHeight: getPageMinHeight() }}>
        <NavBar title="刷题" />
        <View className={styles.doneBody}>
          <View className={styles.doneMain}>
            <Mascot variant="done" width={220} height={180} />
            <Text className={styles.doneTitle}>本轮完成！</Text>
            <Text className={styles.doneSub}>
              {reviewed >= queue.length
                ? `今天到期的 ${queue.length} 道题都复习完了`
                : `本轮复习 ${reviewed} 道，还有 ${queue.length - reviewed} 道留到下次`}
            </Text>

            <View className={styles.statGrid}>
              <View className={styles.statCell}>
                <Text className={styles.statNumber}>{reviewed}</Text>
                <Text className={styles.statLabel}>复习题数</Text>
              </View>
              <View className={styles.statCell}>
                <Text className={styles.statNumber}>{remembered}</Text>
                <Text className={styles.statLabel}>记住了</Text>
              </View>
              <View className={styles.statCell}>
                <Text className={styles.statNumber}>{forgot}</Text>
                <Text className={styles.statLabel}>待巩固</Text>
              </View>
            </View>
          </View>

          {REVIEW_REMINDER_ENABLED ? (
            <View className={styles.subCard}>
              <View className={styles.subHead}>
                <View className={styles.subIcon}>
                  <Icon name="bellMuted" size={20} />
                </View>
                <Text className={styles.subTitle}>别错过下次复习</Text>
              </View>
              <Text className={styles.subDesc}>
                {nextDue.at
                  ? `${dueDayText(nextDue)}有 ${nextDue.count} 道题到期，20:00 提醒你回来复习。`
                  : '暂无后续到期安排，可继续拍照录入新错题。'}
              </Text>
              <AppButton className={styles.subBtn} onClick={handleSubscribe}>
                开启微信提醒
              </AppButton>
              <Text className={styles.subNote}>提醒通过微信服务通知发送，仅在你授权后送达</Text>
            </View>
          ) : null}

          <View className={styles.doneActions}>
            <AppButton variant="text" onClick={gotoLibrary}>
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
        <Chip type="green">第 {roundStage} 轮复习</Chip>
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
        <Chip type="green">第 {roundStage} 轮复习</Chip>
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
            <Text className={classnames(styles.progressTotal, styles.num)}>/ {queue.length}</Text>
            <Text className={styles.progressLabel}>题</Text>
          </View>
          <Chip type="green">第 {roundStage} 轮复习</Chip>
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

        {flipped ? (
          <View className={styles.rate}>
            <View className={styles.rateQuestion}>
              <Icon name="helpMuted" size={15} />
              <Text>这道题现在有把握了吗？</Text>
            </View>
            <View className={styles.rateButtons}>
              <AppButton
                className={classnames(styles.rateBtn, styles.rateBtnWarn)}
                onClick={() => handleRating('forgot')}
              >
                没记住
              </AppButton>
              <AppButton className={styles.rateBtn} onClick={() => handleRating('remembered')}>
                记住了
              </AppButton>
            </View>
          </View>
        ) : (
          <View className={styles.actions}>
            <AppButton onClick={() => setFlipped(true)}>显示答案</AppButton>
            <AppButton variant="text" className={styles.actionsSecond} onClick={goNext}>
              本轮跳过
            </AppButton>
          </View>
        )}
      </View>

      <PrivacySheet />
    </View>
  );
};

export default QuizPage;
