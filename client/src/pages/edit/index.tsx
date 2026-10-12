import React, { useEffect, useRef, useState } from 'react';
import { Image, Text, Textarea, View } from '@tarojs/components';
import Taro, { useRouter } from '@tarojs/taro';
import classnames from 'classnames';

import ActionSheet from '@/components/ActionSheet';
import AppButton from '@/components/AppButton';
import Chip from '@/components/Chip';
import Icon from '@/components/Icon';
import Mascot from '@/components/Mascot';
import NavBar from '@/components/NavBar';
import { ANSWER_MAX_LENGTH, CONTENT_MAX_LENGTH } from '@/constants';
import { captureService } from '@/services/captureService';
import { recognitionService } from '@/services/recognitionService';
import type { SplitMethod } from '@/services/recognitionService';
import { questionService } from '@/services/questionService';
import { fileRepo } from '@/services/repo/fileRepo';
import { useQuestionStore } from '@/store/questionStore';
import { getPageMinHeight } from '@/utils/layout';

import styles from './index.module.scss';

type Phase = 'recognizing' | 'form';

const delay = (ms: number) => new Promise((resolve) => setTimeout(resolve, ms));

const EditPage = () => {
  const router = useRouter();
  const rawTempPath = router.params.tempPath || '';
  const initialTempPath = rawTempPath.includes('%') ? decodeURIComponent(rawTempPath) : rawTempPath;

  const [tempPath, setTempPath] = useState(initialTempPath);
  const [phase, setPhase] = useState<Phase>(initialTempPath ? 'recognizing' : 'form');
  const [content, setContent] = useState('');
  const [answer, setAnswer] = useState('');
  const [splitMethod, setSplitMethod] = useState<SplitMethod>('none');
  const [recognizeFailed, setRecognizeFailed] = useState(false);
  const [progress, setProgress] = useState(0);
  const [imageSize, setImageSize] = useState(0);
  const [saved, setSaved] = useState(false);
  const [sheetVisible, setSheetVisible] = useState(false);
  const [contentFocused, setContentFocused] = useState(false);

  const startedRef = useRef('');
  const refreshStore = useQuestionStore((state) => state.refresh);

  const runRecognize = async (path: string) => {
    setPhase('recognizing');
    setRecognizeFailed(false);
    setProgress(0);

    const timer = setInterval(() => {
      setProgress((value) => (value >= 90 ? 90 : value + 9));
    }, 140);

    const [result] = await Promise.all([recognitionService.recognize(path), delay(700)]);
    clearInterval(timer);
    setProgress(100);

    if (result.ok) {
      setContent(result.text);
      setAnswer(result.answer);
      setSplitMethod(result.splitMethod);
      setRecognizeFailed(false);
    } else {
      setContent('');
      setAnswer('');
      setSplitMethod('none');
      setRecognizeFailed(true);
      Taro.showToast({ title: result.message || '识别失败，请手动输入', icon: 'none' });
    }
    setPhase('form');
  };

  useEffect(() => {
    if (!initialTempPath || startedRef.current === initialTempPath) return;
    startedRef.current = initialTempPath;
    void runRecognize(initialTempPath);
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [initialTempPath]);

  const handleRetake = async (source: 'camera' | 'album') => {
    setSheetVisible(false);
    const path = await captureService.pick(source);
    if (!path) return;
    setTempPath(path);
    startedRef.current = '';
    await runRecognize(path);
  };

  const handleSave = async () => {
    const trimmed = content.trim();
    if (!trimmed || saved) return;
    setSaved(true);
    try {
      await questionService.create({ content: trimmed, answer, tempImagePath: tempPath || undefined });
      refreshStore();
      console.info('[edit] question saved');
      setTimeout(() => {
        Taro.switchTab({ url: '/pages/library/index' });
      }, 1500);
    } catch (error) {
      console.error('[edit] save failed', error);
      setSaved(false);
      Taro.showToast({ title: '保存失败，请重试', icon: 'none' });
    }
  };

  useEffect(() => {
    if (!tempPath) return;
    const size = fileRepo.getFileSize(tempPath);
    setImageSize(size);
  }, [tempPath]);

  const previewImage = () => {
    if (!tempPath) return;
    Taro.previewImage({ urls: [tempPath], current: tempPath });
  };

  if (phase === 'recognizing') {
    return (
      <View className={styles.page} style={{ minHeight: getPageMinHeight() }}>
        <NavBar title="识别中" />
        <View className={styles.body}>
          <View className={styles.thumbCard}>
            <View className={styles.recognizeThumb}>
              <Image className={styles.thumbImg} src={tempPath} mode="aspectFill" />
            </View>
            <View className={styles.thumbInfo}>
              <Text className={styles.thumbTitle}>原图已压缩</Text>
              <Text className={styles.thumbSub}>
                {imageSize > 0 ? `${Math.max(1, Math.round(imageSize / 1024))} KB · 已压缩上传` : '已压缩上传'}
              </Text>
            </View>
            <Chip type="blue">识别中</Chip>
          </View>

          <View className={styles.recognizeCenter}>
            <Mascot width={86} height={86} />
            <View className={styles.recognizeStatus}>
              <View className={styles.spinner} />
              <Text className={styles.recognizeStatusText}>正在识别题目…</Text>
            </View>
          </View>

          <View className={styles.bar}>
            <View className={styles.barInner} style={{ width: `${progress}%` }} />
          </View>
          <Text className={styles.recognizePercent}>已完成 {progress}%</Text>

          <Text className={styles.previewLabel}>题干预览</Text>
          <View className={styles.skeletonCard}>
            <View className={classnames(styles.sk, styles.sk92)} />
            <View className={classnames(styles.sk, styles.sk100)} />
            <View className={classnames(styles.sk, styles.sk74)} />
            <View className={classnames(styles.sk, styles.sk46)} />
          </View>
        </View>

        <View className={styles.actionBar}>
          <AppButton variant="text" onClick={() => Taro.navigateBack()}>
            取消识别
          </AppButton>
        </View>
      </View>
    );
  }

  const canSave = content.trim().length > 0 && !saved;

  const answerTip = recognizeFailed
    ? '请手动填写'
    : splitMethod === 'vlm'
      ? 'AI 已识别答案 · 请校对'
      : '未识别到答案 · 可手动填写';

  return (
    <View className={styles.page} style={{ minHeight: getPageMinHeight() }}>
      <NavBar title="编辑校对" rightText="重拍" onRightClick={() => setSheetVisible(true)} />

      <View className={styles.formBody}>
        <View className={styles.thumbCard}>
          <View className={styles.thumb}>
            <Image className={styles.thumbImg} src={tempPath} mode="aspectFill" />
          </View>
          <View className={styles.thumbInfo}>
            <Text className={styles.thumbTitle}>原图已保存</Text>
            <Text className={styles.thumbSub}>
              {imageSize > 0 ? `压缩后 ${Math.max(1, Math.round(imageSize / 1024))} KB` : '已压缩'}
            </Text>
          </View>
          {tempPath ? (
            <Text className={styles.link} onClick={previewImage}>
              查看大图
            </Text>
          ) : null}
        </View>

        <View className={styles.fieldHead}>
          <Text className={styles.fieldLabel}>
            题干 <Text className={styles.required}>*</Text>
          </Text>
          <View className={styles.fieldActions}>
            <Text className={styles.fieldTip}>
              {recognizeFailed ? '识别失败 · 请手动输入' : 'AI 已识别 · 请校对'}
            </Text>
          </View>
        </View>
        <View className={classnames(styles.inputBox, contentFocused && styles.inputBoxFocused)}>
          <Textarea
            className={styles.textarea}
            value={content}
            placeholder="请输入或校对题干（纯文本）"
            maxlength={CONTENT_MAX_LENGTH}
            onInput={(event) => setContent(event.detail.value)}
            onFocus={() => setContentFocused(true)}
            onBlur={() => setContentFocused(false)}
          />
          <Text className={styles.counter}>
            {content.length} / {CONTENT_MAX_LENGTH}
          </Text>
        </View>

        <View className={styles.fieldHead}>
          <Text className={styles.fieldLabel}>答案</Text>
          <Text className={styles.fieldTip}>{answerTip}</Text>
        </View>
        <View className={styles.inputBox}>
          <Textarea
            className={styles.textareaAnswer}
            value={answer}
            placeholder="请输入答案（可留空）"
            maxlength={ANSWER_MAX_LENGTH}
            onInput={(event) => setAnswer(event.detail.value)}
          />
          <Text className={styles.counter}>
            {answer.length} / {ANSWER_MAX_LENGTH}
          </Text>
        </View>

        <View className={styles.note}>
          <Icon name="infoBlueInk" size={16} />
          <Text className={styles.noteText}>仅支持纯文本，不解析公式与图文混排</Text>
        </View>
      </View>

      <View className={styles.actionBar}>
        <AppButton disabled={!canSave} onClick={handleSave}>
          保存入库
        </AppButton>
      </View>

      {saved ? (
        <View className={styles.toast}>
          <Icon name="checkGreen" size={16} />
          <Text className={styles.toastText}>已保存</Text>
        </View>
      ) : null}

      <ActionSheet
        visible={sheetVisible}
        title="选择录入方式"
        items={[
          { key: 'camera', label: '拍照', icon: <Icon name="cameraInk" size={23} /> },
          { key: 'album', label: '从相册选择', icon: <Icon name="albumInk" size={23} /> },
        ]}
        onSelect={(key) => handleRetake(key === 'camera' ? 'camera' : 'album')}
        onCancel={() => setSheetVisible(false)}
      />
    </View>
  );
};

export default EditPage;
