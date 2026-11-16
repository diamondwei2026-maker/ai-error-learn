import React, { useRef, useState } from 'react';
import { Image, Text, View } from '@tarojs/components';
import Taro, { useDidShow, useReachBottom } from '@tarojs/taro';

import ActionSheet from '@/components/ActionSheet';
import AppButton from '@/components/AppButton';
import Chip from '@/components/Chip';
import ConfirmDialog from '@/components/ConfirmDialog';
import Empty from '@/components/Empty';
import Icon from '@/components/Icon';
import NavBar from '@/components/NavBar';
import PrivacySheet from '@/components/PrivacySheet';
import QuestionCard from '@/components/QuestionCard';
import SwipeItem from '@/components/SwipeItem';
import VariantSheet, { type VariantSheetState } from '@/components/VariantSheet';
import {
  AI_CODE,
  AI_ERROR_MESSAGES,
  AI_SUBJECT_LABELS,
  AI_VARIANT_ENABLED,
  AUTH_CODE,
  PAGE_SIZE,
} from '@/constants';
import { aiService, type AiVariantResult } from '@/services/aiService';
import { captureService } from '@/services/captureService';
import { questionService } from '@/services/questionService';
import { fileRepo } from '@/services/repo/fileRepo';
import { ApiRequestError } from '@/services/request';
import { useQuestionStore } from '@/store/questionStore';
import { useUserStore } from '@/store/userStore';
import type { Question } from '@/types/question';
import { getFabBottom, getPageMinHeight } from '@/utils/layout';

import styles from './index.module.scss';

type AiState = 'idle' | VariantSheetState;

const LibraryPage = () => {
  const [questions, setQuestions] = useState<Question[]>([]);
  const [total, setTotal] = useState(0);
  const [swipedId, setSwipedId] = useState('');
  const [detail, setDetail] = useState<Question | null>(null);
  const [dialogVisible, setDialogVisible] = useState(false);
  const [pendingDelete, setPendingDelete] = useState<Question | null>(null);
  const [sheetVisible, setSheetVisible] = useState(false);
  const [aiVisible, setAiVisible] = useState(false);
  const [aiState, setAiState] = useState<AiState>('idle');
  const [aiData, setAiData] = useState<AiVariantResult | null>(null);
  const [aiError, setAiError] = useState('');
  const [aiEntryHidden, setAiEntryHidden] = useState(false);

  const pageRef = useRef(1);
  const aiSeq = useRef(0);
  const refreshStore = useQuestionStore((state) => state.refresh);
  const isLoggedIn = useUserStore((state) => state.isLoggedIn);

  /** 切换 / 关闭详情时清空举一反三状态，并丢弃在途请求结果 */
  const resetAi = () => {
    aiSeq.current += 1;
    setAiVisible(false);
    setAiState('idle');
    setAiData(null);
    setAiError('');
  };

  const reload = () => {
    pageRef.current = 1;
    setQuestions(questionService.list(1));
    setTotal(questionService.count());
    refreshStore();
  };

  useDidShow(() => {
    reload();
    setSwipedId('');
    setDetail(null);
    Taro.showTabBar({ animation: false }).catch((error) =>
      console.error('[library] showTabBar failed', error),
    );
  });

  /** 详情预览为无 tabBar 的独立视图（对齐原型 08/09 屏） */
  const openDetail = (question: Question) => {
    resetAi();
    setDetail(question);
    Taro.hideTabBar({ animation: false }).catch((error) =>
      console.error('[library] hideTabBar failed', error),
    );
  };

  const closeDetail = () => {
    resetAi();
    setDetail(null);
    Taro.showTabBar({ animation: false }).catch((error) =>
      console.error('[library] showTabBar failed', error),
    );
  };

  useReachBottom(() => {
    const allCount = questionService.count();
    if (pageRef.current * PAGE_SIZE >= allCount) return;
    pageRef.current += 1;
    setQuestions((prev) => [...prev, ...questionService.list(pageRef.current)]);
  });

  const handleCapture = async (source: 'camera' | 'album') => {
    setSheetVisible(false);
    const tempFilePath = await captureService.pick(source);
    if (!tempFilePath) return;
    Taro.navigateTo({ url: `/pages/edit/index?tempPath=${encodeURIComponent(tempFilePath)}` });
  };

  const askDelete = (question: Question) => {
    setPendingDelete(question);
    setDialogVisible(true);
  };

  const confirmDelete = async () => {
    if (pendingDelete) {
      await questionService.remove(pendingDelete.id);
      console.info('[library] removed question', pendingDelete.id);
    }
    setDialogVisible(false);
    setPendingDelete(null);
    setSwipedId('');
    resetAi();
    closeDetail();
    reload();
  };

  const previewImage = () => {
    if (!detail?.imagePath) return;
    const src = fileRepo.resolveImageSrc(detail.imagePath);
    if (!src) return;
    Taro.previewImage({ urls: [src], current: src });
  };

  /** 请求变式题：保留上一轮结果，失败进入统一重试态 */
  const requestVariants = async () => {
    if (!detail) return;
    const seq = aiSeq.current + 1;
    aiSeq.current = seq;
    setAiVisible(true);
    setAiState('loading');
    setAiError('');
    try {
      const data = await aiService.generateVariants({
        questionId: detail.id,
        content: detail.content,
        answer: detail.answer,
        // 已有分类时透传，服务端据此跳过重新分类
        subject: detail.subject,
        questionType: detail.questionType,
        knowledgePoints: detail.knowledgePoints,
      });
      if (seq !== aiSeq.current) return;
      setAiData(data);
      setAiState(data.variants.length > 0 ? 'success' : 'empty');
      // 惰性回填元信息：仅填补本地缺失字段，无变更时不写盘
      if (questionService.patchMeta(detail.id, data)) {
        const updated = questionService.get(detail.id);
        if (updated) setDetail(updated);
        reload();
      }
    } catch (error) {
      if (seq !== aiSeq.current) return;
      const code = error instanceof ApiRequestError ? error.code : 0;
      if (code === AI_CODE.notEnabled) {
        // 服务端未开放：隐藏入口，本次会话不再展示
        setAiVisible(false);
        setAiState('idle');
        setAiEntryHidden(true);
        Taro.showToast({ title: AI_ERROR_MESSAGES[AI_CODE.notEnabled], icon: 'none' });
        return;
      }
      if (code === AI_CODE.rateLimited) {
        setAiVisible(false);
        setAiState('idle');
        Taro.showToast({ title: AI_ERROR_MESSAGES[AI_CODE.rateLimited], icon: 'none' });
        return;
      }
      if (code === AUTH_CODE.unauthorized || code === AUTH_CODE.tokenInvalid) {
        setAiState('needLogin');
        return;
      }
      setAiError(
        error instanceof Error ? error.message : AI_ERROR_MESSAGES[AI_CODE.upstreamBusy],
      );
      setAiState('error');
    }
  };

  /** 入口点击：请求中防抖；已有结果直接复用；未登录不发请求 */
  const openAiSheet = () => {
    if (!detail || aiState === 'loading') return;
    setAiVisible(true);
    if (aiState !== 'idle') return;
    if (!isLoggedIn) {
      setAiState('needLogin');
      return;
    }
    requestVariants();
  };

  /** 登录成功自动继续本次生成 */
  const handleAiLogin = async () => {
    try {
      await useUserStore.getState().login();
      await requestVariants();
    } catch {
      Taro.showToast({ title: '登录未完成，请重试', icon: 'none' });
    }
  };

  const closeAiSheet = () => setAiVisible(false);

  const detailImage = detail ? fileRepo.resolveImageSrc(detail.imagePath) : '';

  return (
    <View className={styles.page} style={{ minHeight: getPageMinHeight() }}>
      <NavBar
        title={detail ? '题目详情' : '题库'}
        showBack={Boolean(detail)}
        onBack={closeDetail}
      />

      {detail ? (
        <>
          <View className={styles.detailBody}>
            <View className={styles.detailCard}>
              <Text className={styles.sectionLabel}>题干</Text>
              <Text className={styles.detailText}>{detail.content}</Text>
            </View>

            {detail.subject || detail.questionType || detail.knowledgePoints?.length ? (
              <View className={styles.metaRow}>
                {detail.subject ? (
                  <Chip type="green">{AI_SUBJECT_LABELS[detail.subject] || '其他'}</Chip>
                ) : null}
                {detail.questionType ? (
                  <Chip type="neutral">{detail.questionType}</Chip>
                ) : null}
                {detail.knowledgePoints?.map((point) => (
                  <Chip key={point} type="neutral" className={styles.metaChipKnowledge}>
                    {point}
                  </Chip>
                ))}
              </View>
            ) : null}

            {detail.imagePath ? (
              <View className={styles.detailImageCard}>
                <View className={styles.imageHead}>
                  <Text className={styles.sectionLabel}>原图</Text>
                  <Text className={styles.link} onClick={previewImage}>
                    点击查看大图
                  </Text>
                </View>
                <View className={styles.imageBox} onClick={previewImage}>
                  <Image className={styles.image} src={detailImage} mode="aspectFill" />
                </View>
              </View>
            ) : null}

            <View className={styles.answerCard}>
              <Text className={styles.sectionLabelAccent}>答案</Text>
              <Text className={styles.detailText}>{detail.answer || '（未填写答案）'}</Text>
            </View>

            {AI_VARIANT_ENABLED && !aiEntryHidden ? (
              <View className={styles.aiEntry} onClick={openAiSheet}>
                <View className={styles.aiEntryIco}>
                  <Icon name="sparkleWhite" size={20} />
                </View>
                <View className={styles.aiEntryText}>
                  <View className={styles.aiEntryTitle}>
                    <Text>再来三道变式</Text>
                    <Text className={styles.aiEntryTag}>AI</Text>
                  </View>
                  <Text className={styles.aiEntrySub}>生成 3 道同类型题，确认是否真的掌握</Text>
                </View>
                <View className={styles.aiEntryArrow}>
                  <Icon name="chevronRightMuted" size={20} />
                </View>
              </View>
            ) : null}
          </View>

          <View className={styles.actionBar}>
            <AppButton
              variant="danger"
              icon={<Icon name="trashRed" size={18} />}
              onClick={() => askDelete(detail)}
            >
              删除本题
            </AppButton>
          </View>
        </>
      ) : (
        <>
          <View className={styles.listBody}>
            <View className={styles.listHead}>
              <Text className={styles.listTitle}>全部错题</Text>
              <Text className={styles.listCount}>{total} 道</Text>
            </View>

            {questions.length === 0 ? (
              <Empty
                title="还没有错题"
                description="拍下第一道错题，建立属于你的错题卡片，随时翻看题干与答案。"
                actionText="去录入第一道错题"
                onAction={() => setSheetVisible(true)}
              />
            ) : (
              questions.map((question) => (
                <SwipeItem
                  key={question.id}
                  className={styles.row}
                  open={swipedId === question.id}
                  onOpen={() => setSwipedId(question.id)}
                  onClose={() => setSwipedId('')}
                  onDelete={() => askDelete(question)}
                >
                  <QuestionCard
                    question={question}
                    onClick={() => openDetail(question)}
                    onLongPress={() => askDelete(question)}
                  />
                </SwipeItem>
              ))
            )}
          </View>

          {questions.length > 0 ? (
            <View
              className={styles.fab}
              style={{ bottom: getFabBottom() }}
              onClick={() => setSheetVisible(true)}
            >
              <Icon name="plusWhite" size={26} />
            </View>
          ) : null}
        </>
      )}

      <ActionSheet
        visible={sheetVisible}
        title="选择录入方式"
        items={[
          { key: 'camera', label: '拍照', icon: <Icon name="cameraInk" size={23} /> },
          { key: 'album', label: '从相册选择', icon: <Icon name="albumInk" size={23} /> },
        ]}
        onSelect={(key) => handleCapture(key === 'camera' ? 'camera' : 'album')}
        onCancel={() => setSheetVisible(false)}
      />

      <ConfirmDialog
        visible={dialogVisible}
        title="删除这道错题？"
        description="删除后将同时清理该题的原图文件，且无法恢复。"
        onConfirm={confirmDelete}
        onCancel={() => setDialogVisible(false)}
      />

      <VariantSheet
        visible={aiVisible}
        state={aiState === 'idle' ? 'loading' : aiState}
        data={aiData}
        errorMessage={aiError}
        onClose={closeAiSheet}
        onRetry={requestVariants}
        onRegenerate={requestVariants}
        onContinue={closeAiSheet}
        onLogin={handleAiLogin}
      />

      <PrivacySheet />
    </View>
  );
};

export default LibraryPage;
