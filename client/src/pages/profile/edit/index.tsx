import React, { useEffect, useState } from 'react';
import { Button, Image, Input, Text, View } from '@tarojs/components';
import Taro from '@tarojs/taro';

import AppButton from '@/components/AppButton';
import Icon from '@/components/Icon';
import NavBar from '@/components/NavBar';
import PrivacySheet from '@/components/PrivacySheet';
import { API_BASE, NICKNAME_MAX_LENGTH, PRIVACY_DENIED_MESSAGE } from '@/constants';
import { MASCOT_DATA_URI } from '@/constants/mascot';
import { privacyService } from '@/services/privacyService';
import { useUserStore } from '@/store/userStore';
import { getPageMinHeight } from '@/utils/layout';

import styles from './index.module.scss';

const ProfileEditPage = () => {
  const user = useUserStore((state) => state.user);
  const isLoggedIn = useUserStore((state) => state.isLoggedIn);
  const updateProfile = useUserStore((state) => state.updateProfile);

  const [avatarTempPath, setAvatarTempPath] = useState('');
  const [nickname, setNickname] = useState(user?.nickname || '');
  const [saving, setSaving] = useState(false);

  useEffect(() => {
    if (!isLoggedIn) {
      Taro.navigateBack().catch(() => {
        Taro.switchTab({ url: '/pages/profile/index' });
      });
    }
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [isLoggedIn]);

  const hasAvatar = Boolean(avatarTempPath || user?.avatarUrl);
  const avatarSrc = avatarTempPath || (user?.avatarUrl ? `${API_BASE}${user.avatarUrl}` : MASCOT_DATA_URI);
  const avatarMode = hasAvatar ? 'aspectFill' : 'aspectFit';

  // eslint-disable-next-line @typescript-eslint/no-explicit-any
  const handleChooseAvatar = (event: any) => {
    const url: string | undefined = event?.detail?.avatarUrl;
    if (url) setAvatarTempPath(url);
  };

  /**
   * 昵称输入聚焦：`<input type="nickname">` 未同意隐私协议时不会触发被动监听
   * （会静默降级为普通文本输入），因此需在聚焦时主动前置授权。
   */
  const handleNicknameFocus = async () => {
    const authorized = await privacyService.requireAuthorize();
    if (!authorized) {
      Taro.showToast({ title: PRIVACY_DENIED_MESSAGE, icon: 'none' });
    }
  };

  const handleSave = async () => {
    if (saving) return;
    const trimmed = nickname.trim();
    if (trimmed.length > NICKNAME_MAX_LENGTH) {
      Taro.showToast({ title: `昵称不能超过 ${NICKNAME_MAX_LENGTH} 个字`, icon: 'none' });
      return;
    }
    setSaving(true);
    try {
      await updateProfile({ nickname: trimmed, avatarTempPath: avatarTempPath || undefined });
      Taro.showToast({ title: '已保存', icon: 'success' });
      setTimeout(() => {
        Taro.navigateBack().catch(() => {
          Taro.switchTab({ url: '/pages/profile/index' });
        });
      }, 800);
    } catch (error) {
      console.error('[profileEdit] save failed', error);
      Taro.showToast({ title: (error as Error).message || '保存失败，请重试', icon: 'none' });
    } finally {
      setSaving(false);
    }
  };

  return (
    <View className={styles.page} style={{ minHeight: getPageMinHeight() }}>
      <NavBar title="完善资料" showBack />

      <View className={styles.body}>
        <Button className={styles.avatarBtn} openType="chooseAvatar" onChooseAvatar={handleChooseAvatar}>
          <View className={styles.avatar}>
            <Image className={styles.avatarImg} src={avatarSrc} mode={avatarMode} />
          </View>
          <View className={styles.badge}>
            <Icon name="cameraWhite" size={13} />
          </View>
        </Button>
        <Text className={styles.avatarHint}>点击头像可更换</Text>

        <View className={styles.field}>
          <Text className={styles.fieldLabel}>昵称</Text>
          <View className={styles.inputBox}>
            <Input
              className={styles.input}
              type="nickname"
              value={nickname}
              maxlength={NICKNAME_MAX_LENGTH}
              placeholder="请输入昵称"
              placeholderClass={styles.placeholder}
              onFocus={handleNicknameFocus}
              onInput={(event) => setNickname(event.detail.value)}
            />
            <Text className={styles.counter}>
              {nickname.length}/{NICKNAME_MAX_LENGTH}
            </Text>
          </View>
        </View>
      </View>

      <View className={styles.actionBar}>
        <AppButton disabled={saving} onClick={handleSave}>
          保存
        </AppButton>
      </View>

      <PrivacySheet />
    </View>
  );
};

export default ProfileEditPage;
