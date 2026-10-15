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
import { PAGE_SIZE } from '@/constants';
import { captureService } from '@/services/captureService';
import { questionService } from '@/services/questionService';
import { fileRepo } from '@/services/repo/fileRepo';
import { useQuestionStore } from '@/store/questionStore';
import type { Question } from '@/types/question';
import { getFabBottom, getPageMinHeight } from '@/utils/layout';

import styles from './index.module.scss';

const LibraryPage = () => {
  const [questions, setQuestions] = useState<Question[]>([]);
  const [total, setTotal] = useState(0);
  const [swipedId, setSwipedId] = useState('');
  const [detail, setDetail] = useState<Question | null>(null);
  const [dialogVisible, setDialogVisible] = useState(false);
  const [pendingDelete, setPendingDelete] = useState<Question | null>(null);
  const [sheetVisible, setSheetVisible] = useState(false);

  const pageRef = useRef(1);
  const refreshStore = useQuestionStore((state) => state.refresh);

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
    setDetail(question);
    Taro.hideTabBar({ animation: false }).catch((error) =>
      console.error('[library] hideTabBar failed', error),
    );
  };

  const closeDetail = () => {
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
    closeDetail();
    reload();
  };

  const previewImage = () => {
    if (!detail?.imagePath) return;
    const src = fileRepo.resolveImageSrc(detail.imagePath);
    if (!src) return;
    Taro.previewImage({ urls: [src], current: src });
  };

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
            <View className={styles.chipRow}>
              <Chip type={detail.imagePath ? 'blue' : 'neutral'}>
                {detail.imagePath ? '含原图' : '无原图'}
              </Chip>
            </View>

            <View className={styles.detailCard}>
              <Text className={styles.sectionLabel}>题干</Text>
              <Text className={styles.detailText}>{detail.content}</Text>
            </View>

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
                description="拍下第一道错题，建立属于你的错题卡片，随时翻面复习。"
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

      <PrivacySheet />
    </View>
  );
};

export default LibraryPage;
