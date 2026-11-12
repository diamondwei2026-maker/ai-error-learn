import React, { useState } from 'react';
import { Text, View } from '@tarojs/components';
import Taro, { useDidShow } from '@tarojs/taro';
import classnames from 'classnames';

import ActionSheet from '@/components/ActionSheet';
import AppButton from '@/components/AppButton';
import Chip from '@/components/Chip';
import Icon from '@/components/Icon';
import LoginSheet from '@/components/LoginSheet';
import Mascot from '@/components/Mascot';
import NavBar from '@/components/NavBar';
import PrivacySheet from '@/components/PrivacySheet';
import { REVIEW_REMINDER_ENABLED } from '@/constants';
import { captureService } from '@/services/captureService';
import { questionService } from '@/services/questionService';
import { reminderService } from '@/services/reminderService';
import { useQuestionStore } from '@/store/questionStore';
import { useUserStore } from '@/store/userStore';
import {
  dueSummary,
  nextDueInfo,
  startOfDay,
  type DueSummary,
  type NextDueInfo,
} from '@/utils/reviewSchedule';
import { getPageMinHeight } from '@/utils/layout';
import { syncQuizBadge } from '@/utils/tabBadge';

import styles from './index.module.scss';

const EMPTY_DUE: DueSummary = {
  count: 0,
  overdueDays: 0,
  estimatedMinutes: 0,
  stageMin: null,
  stageMax: null,
};

const EMPTY_NEXT_DUE: NextDueInfo = { at: null, count: 0, daysUntil: 0 };

const IndexPage = () => {
  const [sheetVisible, setSheetVisible] = useState(false);
  const [loginSheetVisible, setLoginSheetVisible] = useState(false);
  const [loginBusy, setLoginBusy] = useState(false);
  const [due, setDue] = useState<DueSummary>(EMPTY_DUE);
  const [nextDue, setNextDue] = useState<NextDueInfo>(EMPTY_NEXT_DUE);
  const [reviewedToday, setReviewedToday] = useState(0);
  const [snoozed, setSnoozed] = useState(false);
  const [reminderOn, setReminderOn] = useState(false);
  const total = useQuestionStore((state) => state.total);
  const refresh = useQuestionStore((state) => state.refresh);
  const isLoggedIn = useUserStore((state) => state.isLoggedIn);
  const restoreUser = useUserStore((state) => state.restore);
  const login = useUserStore((state) => state.login);
  const shouldGuideProfileSetup = useUserStore((state) => state.shouldGuideProfileSetup);
  const markProfileSetupGuided = useUserStore((state) => state.markProfileSetupGuided);

  const refreshReview = () => {
    const now = Date.now();
    const all = questionService.all();
    const summary = dueSummary(all, now);
    setDue(summary);
    setNextDue(nextDueInfo(all, now));
    setReviewedToday(
      all.filter(
        (item) =>
          typeof item.lastReviewedAt === 'number' &&
          startOfDay(item.lastReviewedAt) === startOfDay(now),
      ).length,
    );
    syncQuizBadge(summary.count);
  };

  useDidShow(() => {
    restoreUser();
    refresh();
    setSnoozed(false);
    setReminderOn(reminderService.isOn());
    refreshReview();
  });

  /** 拍照/选图 → 压缩 → 进入编辑页（编辑页负责识别） */
  const startCapture = async (source: 'camera' | 'album') => {
    setSheetVisible(false);
    const tempFilePath = await captureService.pick(source);
    if (!tempFilePath) return;
    Taro.navigateTo({ url: `/pages/edit/index?tempPath=${encodeURIComponent(tempFilePath)}` });
  };

  /** 拍照识别需登录：游客点击时先弹登录引导 */
  const handleEntryPrimary = () => {
    if (!isLoggedIn) {
      setLoginSheetVisible(true);
      return;
    }
    setSheetVisible(true);
  };

  /** 首次登录后引导进入「完善资料」页（仅一次，可点返回跳过） */
  const guideProfileSetup = () => {
    if (!shouldGuideProfileSetup()) return;
    markProfileSetupGuided();
    Taro.navigateTo({ url: '/pages/profile/edit/index' });
  };

  const handleLogin = async () => {
    if (loginBusy) return;
    setLoginBusy(true);
    try {
      await login();
      setLoginSheetVisible(false);
      Taro.showToast({ title: '登录成功', icon: 'success' });
      guideProfileSetup();
    } catch (error) {
      console.error('[index] login failed', error);
      Taro.showToast({ title: (error as Error).message || '登录失败，请重试', icon: 'none' });
    } finally {
      setLoginBusy(false);
    }
  };

  const gotoQuiz = () => {
    Taro.switchTab({ url: '/pages/quiz/index' });
  };

  /** 提醒开关：游客先登录；开启走微信订阅授权，关闭同步服务端 */
  const toggleReminder = async () => {
    if (!isLoggedIn) {
      setLoginSheetVisible(true);
      return;
    }
    const result = reminderOn
      ? await reminderService.disable()
      : await reminderService.enable();
    setReminderOn(result.on);
    Taro.showToast({ title: result.message, icon: 'none' });
  };

  const dueRoundText =
    due.stageMin === null
      ? ''
      : due.stageMin === due.stageMax
        ? `第 ${due.stageMin} 轮到期`
        : `第 ${due.stageMin}–${due.stageMax} 轮到期`;

  const dueMetaText =
    due.overdueDays > 0
      ? `最早 ${due.overdueDays} 天前到期 · 预计 ${due.estimatedMinutes} 分钟`
      : `今日到期 · 预计 ${due.estimatedMinutes} 分钟`;

  const nextDueText = nextDue.at
    ? `下次到期：${nextDue.daysUntil === 1 ? '明天' : `${nextDue.daysUntil} 天后`} · 共 ${nextDue.count} 道`
    : '暂无后续复习安排';

  const showDueCard =
    REVIEW_REMINDER_ENABLED && total > 0 && !snoozed && (due.count > 0 || reviewedToday > 0);

  const reminderSwitch = (
    <View className={styles.switchLine}>
      <View className={styles.switchLabel}>
        <Icon name="bellMuted" size={15} />
        <Text>每日 20:00 微信提醒</Text>
      </View>
      <View
        className={classnames(styles.switch, reminderOn && styles.switchOn)}
        onClick={toggleReminder}
      >
        <View className={styles.switchKnob} />
      </View>
    </View>
  );

  return (
    <View className={styles.page} style={{ minHeight: getPageMinHeight() }}>
      <NavBar title="错题本" />

      <View className={styles.body}>
        <View className={styles.hero}>
          <View className={styles.heroText}>
            <Text className={styles.slogan}>
              把每一道错题，{'\n'}变成一次
              <Text className={styles.accent}>进步</Text>
            </Text>
          </View>
          <Mascot width={104} height={104} className={styles.heroMascot} />
        </View>

        {showDueCard ? (
          due.count > 0 ? (
            <View className={styles.dueCard}>
              <View className={styles.dueHead}>
                <Chip type="green">今日待复习</Chip>
                <Text className={styles.dueRound}>{dueRoundText}</Text>
              </View>
              <View className={styles.dueCount}>
                <Text className={classnames(styles.dueNumber, styles.num)}>{due.count}</Text>
                <Text className={styles.dueUnit}>道错题</Text>
              </View>
              <Text className={styles.dueMeta}>{dueMetaText}</Text>
              <View className={styles.dueActions}>
                <AppButton className={styles.dueBtn} onClick={gotoQuiz}>
                  开始复习
                </AppButton>
                <AppButton
                  variant="ghost"
                  className={styles.dueBtn}
                  onClick={() => setSnoozed(true)}
                >
                  稍后
                </AppButton>
              </View>
              {reminderSwitch}
            </View>
          ) : (
            <View className={styles.dueCard}>
              <View className={styles.dueHead}>
                <Chip type="neutral">今日复习</Chip>
                <Text className={styles.dueRound}>已完成</Text>
              </View>
              <View className={styles.dueCount}>
                <Text className={classnames(styles.dueNumber, styles.num)}>{reviewedToday}</Text>
                <Text className={styles.dueUnit}>道已复习完</Text>
              </View>
              <Text className={styles.dueMeta}>{nextDueText}</Text>
              {reminderSwitch}
            </View>
          )
        ) : null}

        <View className={classnames(styles.statCard, showDueCard && styles.statCardWithDue)}>
          <Text className={styles.statLabel}>错题总数</Text>
          <View className={styles.statValue}>
            <Text className={styles.statNumber}>{total}</Text>
            <Text className={styles.statUnit}>道</Text>
          </View>
        </View>

        <View className={styles.spacer} />

        <View className={styles.entryPrimary} onClick={handleEntryPrimary}>
          <View className={styles.entryIconPrimary}>
            <Icon name="cameraWhite" size={25} />
          </View>
          <View className={styles.entryText}>
            <Text className={styles.entryTitleAccent}>拍照录入</Text>
            <Text className={styles.entrySubAccent}>拍下题目，自动识别文字</Text>
          </View>
          <Icon name="chevronRightInk" size={20} className={styles.entryArrow} />
        </View>

        <View className={styles.entrySecondary} onClick={gotoQuiz}>
          <View className={styles.entryIconSecondary}>
            <Icon name="bookStackBlueInk" size={25} />
          </View>
          <View className={styles.entryText}>
            <Text className={styles.entryTitle}>开始复习</Text>
            <Text className={styles.entrySub}>按到期顺序 · 翻面看答案</Text>
          </View>
          <Icon name="chevronRightMuted" size={20} />
        </View>
      </View>

      <ActionSheet
        visible={sheetVisible}
        title="选择录入方式"
        items={[
          { key: 'camera', label: '拍照', icon: <Icon name="cameraInk" size={23} /> },
          { key: 'album', label: '从相册选择', icon: <Icon name="albumInk" size={23} /> },
        ]}
        onSelect={(key) => startCapture(key === 'camera' ? 'camera' : 'album')}
        onCancel={() => setSheetVisible(false)}
      />

      <LoginSheet
        visible={loginSheetVisible}
        onLogin={handleLogin}
        onCancel={() => setLoginSheetVisible(false)}
      />

      <PrivacySheet />
    </View>
  );
};

export default IndexPage;
