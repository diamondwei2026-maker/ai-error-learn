import React, { useState } from 'react';
import { Image, Text, View } from '@tarojs/components';
import Taro, { useDidShow } from '@tarojs/taro';

import AppButton from '@/components/AppButton';
import ConfirmDialog from '@/components/ConfirmDialog';
import Icon from '@/components/Icon';
import NavBar from '@/components/NavBar';
import PrivacySheet from '@/components/PrivacySheet';
import { AGREEMENT_PAGE_PATH, AGREEMENT_TYPE, API_BASE } from '@/constants';
import { MASCOT_DATA_URI } from '@/constants/mascot';
import { useQuestionStore } from '@/store/questionStore';
import { useUserStore } from '@/store/userStore';
import { getPageMinHeight } from '@/utils/layout';

import styles from './index.module.scss';

const ProfilePage = () => {
  const user = useUserStore((state) => state.user);
  const isLoggedIn = useUserStore((state) => state.isLoggedIn);
  const login = useUserStore((state) => state.login);
  const logout = useUserStore((state) => state.logout);
  const restore = useUserStore((state) => state.restore);
  const deleteAccount = useUserStore((state) => state.deleteAccount);
  const shouldGuideProfileSetup = useUserStore((state) => state.shouldGuideProfileSetup);
  const markProfileSetupGuided = useUserStore((state) => state.markProfileSetupGuided);
  const refreshQuestions = useQuestionStore((state) => state.refresh);

  const [busy, setBusy] = useState(false);
  const [deleteVisible, setDeleteVisible] = useState(false);

  useDidShow(() => {
    restore();
    refreshQuestions();
  });

  const hasPhoto = Boolean(user?.avatarUrl);
  const avatarSrc = user?.avatarUrl ? `${API_BASE}${user.avatarUrl}` : MASCOT_DATA_URI;
  const avatarMode = hasPhoto ? 'aspectFill' : 'aspectFit';

  /** 首次登录后引导进入「完善资料」页（仅一次，可点返回跳过） */
  const guideProfileSetup = () => {
    if (!shouldGuideProfileSetup()) return;
    markProfileSetupGuided();
    Taro.navigateTo({ url: '/pages/profile/edit/index' });
  };

  const handleLogin = async () => {
    if (busy) return;
    setBusy(true);
    try {
      await login();
      refreshQuestions();
      Taro.showToast({ title: '登录成功', icon: 'success' });
      guideProfileSetup();
    } catch (error) {
      console.error('[profile] login failed', error);
      Taro.showToast({ title: (error as Error).message || '登录失败，请重试', icon: 'none' });
    } finally {
      setBusy(false);
    }
  };

  const handleLogout = () => {
    logout();
    Taro.showToast({ title: '已退出登录', icon: 'none' });
  };

  const handleDelete = async () => {
    setDeleteVisible(false);
    if (busy) return;
    setBusy(true);
    try {
      await deleteAccount();
      refreshQuestions();
      Taro.showToast({ title: '账号已注销', icon: 'none' });
    } catch (error) {
      console.error('[profile] delete account failed', error);
      Taro.showToast({ title: (error as Error).message || '注销失败，请重试', icon: 'none' });
    } finally {
      setBusy(false);
    }
  };

  const gotoEditProfile = () => {
    if (!isLoggedIn) return;
    Taro.navigateTo({ url: '/pages/profile/edit/index' });
  };

  /** 打开协议页（隐私政策 / 用户协议共用同一页面，按 type 区分） */
  const gotoAgreement = (type: string) => {
    Taro.navigateTo({ url: `${AGREEMENT_PAGE_PATH}?type=${type}` });
  };

  return (
    <View className={styles.page} style={{ minHeight: getPageMinHeight() }}>
      <NavBar title="我的" />

      <View className={styles.body}>
        <View className={styles.userCard}>
          {isLoggedIn ? (
            <View className={styles.userHead} onClick={gotoEditProfile}>
              <View className={styles.avatar}>
                <Image className={styles.avatarImg} src={avatarSrc} mode={avatarMode} />
              </View>
              <View className={styles.userInfo}>
                <Text className={styles.nickname}>{user?.nickname || '同学'}</Text>
                <Text className={styles.userHint}>点击修改头像与昵称</Text>
              </View>
              <Icon name="chevronRightMuted" size={18} />
            </View>
          ) : (
            <>
              <View className={styles.userHead}>
                <View className={styles.avatar}>
                  <Image className={styles.avatarImg} src={avatarSrc} mode={avatarMode} />
                </View>
                <View className={styles.userInfo}>
                  <Text className={styles.nickname}>未登录</Text>
                  <Text className={styles.userHint}>登录后可在多设备同步错题</Text>
                </View>
              </View>
              <AppButton className={styles.loginBtn} disabled={busy} onClick={handleLogin}>
                微信一键登录
              </AppButton>
            </>
          )}
        </View>

        {isLoggedIn ? (
          <View className={styles.actionCard}>
            <View className={styles.row} onClick={handleLogout}>
              <Text className={styles.rowLabel}>退出登录</Text>
              <Icon name="chevronRightMuted" size={18} />
            </View>
            <View className={styles.row} onClick={() => setDeleteVisible(true)}>
              <Text className={styles.rowLabelDanger}>注销账号</Text>
              <Icon name="chevronRightMuted" size={18} />
            </View>
          </View>
        ) : null}

        {/* 服务协议：未登录也展示，便于用户在授权前查阅 */}
        <Text className={styles.sectionLabel}>服务协议</Text>
        <View className={styles.actionCard}>
          <View className={styles.row} onClick={() => gotoAgreement(AGREEMENT_TYPE.terms)}>
            <Text className={styles.rowLabel}>用户协议</Text>
            <Icon name="chevronRightMuted" size={18} />
          </View>
          <View className={styles.row} onClick={() => gotoAgreement(AGREEMENT_TYPE.privacy)}>
            <Text className={styles.rowLabel}>隐私政策</Text>
            <Icon name="chevronRightMuted" size={18} />
          </View>
        </View>
      </View>

      <ConfirmDialog
        visible={deleteVisible}
        title="注销账号"
        description="注销后将删除账号及云端全部错题数据，且无法恢复"
        confirmText="确认注销"
        onConfirm={handleDelete}
        onCancel={() => setDeleteVisible(false)}
      />

      <PrivacySheet />
    </View>
  );
};

export default ProfilePage;
