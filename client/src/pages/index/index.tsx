import React, { useState } from 'react';
import { Text, View } from '@tarojs/components';
import Taro, { useDidShow } from '@tarojs/taro';

import ActionSheet from '@/components/ActionSheet';
import Chip from '@/components/Chip';
import Icon from '@/components/Icon';
import LoginSheet from '@/components/LoginSheet';
import Mascot from '@/components/Mascot';
import NavBar from '@/components/NavBar';
import { captureService } from '@/services/captureService';
import { useQuestionStore } from '@/store/questionStore';
import { useUserStore } from '@/store/userStore';
import { getPageMinHeight } from '@/utils/layout';

import styles from './index.module.scss';

const IndexPage = () => {
  const [sheetVisible, setSheetVisible] = useState(false);
  const [loginSheetVisible, setLoginSheetVisible] = useState(false);
  const [loginBusy, setLoginBusy] = useState(false);
  const total = useQuestionStore((state) => state.total);
  const refresh = useQuestionStore((state) => state.refresh);
  const isLoggedIn = useUserStore((state) => state.isLoggedIn);
  const restoreUser = useUserStore((state) => state.restore);
  const login = useUserStore((state) => state.login);

  useDidShow(() => {
    restoreUser();
    refresh();
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

  const handleLogin = async () => {
    if (loginBusy) return;
    setLoginBusy(true);
    try {
      await login();
      setLoginSheetVisible(false);
      Taro.showToast({ title: '登录成功', icon: 'success' });
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

  return (
    <View className={styles.page} style={{ minHeight: getPageMinHeight() }}>
      <NavBar title="错题本" />

      <View className={styles.body}>
        <View className={styles.hero}>
          <View className={styles.heroText}>
            <Chip type="green">MVP 核心闭环</Chip>
            <Text className={styles.slogan}>
              把每一道错题，{'\n'}变成一次
              <Text className={styles.accent}>进步</Text>
            </Text>
            <Text className={styles.sloganSub}>拍下题目即入库 · 随时翻面复习</Text>
          </View>
          <Mascot width={104} height={104} className={styles.heroMascot} />
        </View>

        <View className={styles.statCard}>
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
            <Icon name="refreshBlueInk" size={25} />
          </View>
          <View className={styles.entryText}>
            <Text className={styles.entryTitle}>开始刷题</Text>
            <Text className={styles.entrySub}>随机抽题 · 翻面看答案</Text>
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
    </View>
  );
};

export default IndexPage;
