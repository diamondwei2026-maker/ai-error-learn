import React, { useEffect, useState } from 'react';
import { ScrollView, Text, View } from '@tarojs/components';
import classnames from 'classnames';

import AppButton from '@/components/AppButton';
import Chip from '@/components/Chip';
import Icon from '@/components/Icon';
import { AI_SUBJECT_LABELS } from '@/constants';
import type { AiVariantResult } from '@/services/aiService';

import styles from './index.module.scss';

export type VariantSheetState = 'loading' | 'success' | 'empty' | 'error' | 'needLogin';

export interface VariantSheetProps {
  visible: boolean;
  state: VariantSheetState;
  data: AiVariantResult | null;
  /** 失败态文案（网络异常等），缺省展示上游繁忙文案 */
  errorMessage?: string;
  onClose: () => void;
  /** 失败重试（同一道题） */
  onRetry: () => void;
  /** 空结果重新生成（同一道题） */
  onRegenerate: () => void;
  /** 关闭弹层（仅关闭，保留当前结果便于再次打开） */
  onContinue: () => void;
  onLogin: () => void;
}

const SKELETON_WIDTHS = [styles.sk40, styles.sk85, styles.sk60, styles.sk85];

/** 举一反三底部弹层：加载 / 成功 / 空结果 / 失败重试 / 未登录兜底 */
const VariantSheet = ({
  visible,
  state,
  data,
  errorMessage,
  onClose,
  onRetry,
  onRegenerate,
  onContinue,
  onLogin,
}: VariantSheetProps) => {
  const [expandedIndex, setExpandedIndex] = useState(0);

  useEffect(() => {
    setExpandedIndex(0);
  }, [data]);

  if (!visible) return null;

  const isLogin = state === 'needLogin';
  const variants = data?.variants ?? [];

  const sheetClass = classnames(styles.sheet, {
    [styles.sheetLoading]: state === 'loading',
    [styles.sheetSuccess]: state === 'success',
    [styles.sheetState]: state === 'empty' || state === 'error',
    [styles.sheetLogin]: isLogin,
  });

  const toggleAnswer = (index: number) => {
    setExpandedIndex((value) => (value === index ? -1 : index));
  };

  const renderMeta = () => {
    if (state === 'loading') {
      return (
        <View className={styles.metaRow}>
          <Chip className={styles.chipLoading}>识别学科中</Chip>
          <Chip className={styles.chipLoading}>识别题型中</Chip>
          <Chip className={styles.chipLoading}>提取知识点</Chip>
        </View>
      );
    }
    if (state !== 'success' || !data) return null;

    return (
      <View className={styles.metaRow}>
        <Chip type="green">{AI_SUBJECT_LABELS[data.subject] || '其他'}</Chip>
        {data.questionType ? <Chip type="green">{data.questionType}</Chip> : null}
        {data.knowledgePoints.map((point) => (
          <Chip key={point}>{point}</Chip>
        ))}
      </View>
    );
  };

  const renderState = () => {
    if (state === 'empty') {
      return (
        <>
          <View className={classnames(styles.stateIco, styles.stateIcoNeutral)}>
            <Icon name="boxMuted" size={24} />
          </View>
          <Text className={styles.stateTitle}>这次没有生成出合适的变式题</Text>
          <Text className={styles.stateDesc}>
            可能是题目信息不足，换一道题或稍后再试都能重新生成。
          </Text>
        </>
      );
    }
    if (state === 'error') {
      return (
        <>
          <View className={classnames(styles.stateIco, styles.stateIcoWarn)}>
            <Icon name="warningRed" size={24} />
          </View>
          <Text className={styles.stateTitle}>{errorMessage || 'AI 太忙了，稍后再试'}</Text>
          <Text className={styles.stateDesc}>本次生成没有完成，重试一次即可。</Text>
        </>
      );
    }
    return (
      <>
        <View className={classnames(styles.stateIco, styles.stateIcoGreen)}>
          <Icon name="lockGreenInk" size={24} />
        </View>
        <Text className={styles.stateTitle}>微信登录后即可生成</Text>
        <Text className={styles.stateDesc}>
          生成过程需要消耗 AI 服务额度，登录后可保存使用记录并防止滥用。
        </Text>
      </>
    );
  };

  const renderBody = () => {
    if (state === 'loading') {
      return (
        <ScrollView scrollY className={styles.scroll}>
          <View className={styles.scrollInner}>
            {[0, 1, 2].map((item) => (
              <View key={item} className={styles.skeletonCard}>
                {SKELETON_WIDTHS.map((width, line) => (
                  <View
                    key={line}
                    className={classnames(styles.skLine, width, line === 1 && styles.skGap)}
                  />
                ))}
              </View>
            ))}
            <View className={styles.loadingText}>
              <View className={styles.dotPulse}>
                <View className={styles.dot} />
                <View className={classnames(styles.dot, styles.dot2)} />
                <View className={classnames(styles.dot, styles.dot3)} />
              </View>
              正在分析题型与知识点，约需 10–30 秒
            </View>
          </View>
        </ScrollView>
      );
    }

    if (state === 'success') {
      return (
        <ScrollView scrollY className={styles.scroll}>
          <View className={styles.scrollInner}>
            {variants.map((variant, item) => {
              const expanded = expandedIndex === item;
              return (
                <View key={`${item}-${variant.stem.slice(0, 12)}`} className={styles.variantCard}>
                  <View className={styles.vHead}>
                    <View className={styles.vNo}>变式 {item + 1}</View>
                    {data?.questionType ? (
                      <Text className={styles.vType}>{data.questionType}</Text>
                    ) : null}
                  </View>
                  <Text className={styles.vStem}>{variant.stem}</Text>
                  {variant.answer ? (
                    <View className={styles.vToggle} onClick={() => toggleAnswer(item)}>
                      <Text>{expanded ? '收起答案' : '展开答案'}</Text>
                      <Icon
                        name={expanded ? 'chevronUpMuted' : 'chevronDownMuted'}
                        size={14}
                      />
                    </View>
                  ) : null}
                  {expanded && variant.answer ? (
                    <View className={styles.vAnswer}>
                      <Text className={styles.vAnswerText}>{variant.answer}</Text>
                    </View>
                  ) : null}
                </View>
              );
            })}
            <View className={styles.sheetNote}>
              <Icon name="infoBlueInk" size={12} />
              <Text>内容由 AI 生成，仅供参考</Text>
            </View>
          </View>
        </ScrollView>
      );
    }

    return (
      <View className={styles.stateScroll}>
        <View className={styles.stateBox}>{renderState()}</View>
      </View>
    );
  };

  const renderFoot = () => {
    if (state === 'loading') {
      return (
        <View className={styles.foot}>
          <AppButton disabled className={styles.footBtn}>
            生成中…
          </AppButton>
        </View>
      );
    }
    if (state === 'success') {
      return (
        <View className={styles.foot}>
          <AppButton variant="ghost" className={styles.footBtnGhost} onClick={onRegenerate}>
            换一批
          </AppButton>
          <AppButton className={styles.footBtn} onClick={onContinue}>
            关闭
          </AppButton>
        </View>
      );
    }
    if (state === 'empty') {
      return (
        <View className={styles.foot}>
          <AppButton variant="ghost" className={styles.footBtnGhost} onClick={onContinue}>
            关闭
          </AppButton>
          <AppButton className={styles.footBtn} onClick={onRegenerate}>
            重新生成
          </AppButton>
        </View>
      );
    }
    if (state === 'error') {
      return (
        <View className={styles.foot}>
          <AppButton variant="ghost" className={styles.footBtnGhost} onClick={onContinue}>
            关闭
          </AppButton>
          <AppButton className={styles.footBtn} onClick={onRetry}>
            重试
          </AppButton>
        </View>
      );
    }
    return (
      <View className={styles.foot}>
        <AppButton variant="ghost" className={styles.footBtnGhost} onClick={onClose}>
          稍后再说
        </AppButton>
        <AppButton className={styles.footBtn} onClick={onLogin}>
          微信登录
        </AppButton>
      </View>
    );
  };

  return (
    <>
      <View className={styles.mask} onClick={onClose} catchMove />
      <View className={sheetClass} catchMove>
        <View className={styles.handle} />
        <View className={styles.head}>
          <View className={styles.titleRow}>
            <View className={styles.titleWrap}>
              <View className={styles.titleRowInner}>
                <Text className={styles.title}>{isLogin ? '登录后使用举一反三' : '举一反三'}</Text>
              </View>
              <Text className={styles.sub}>
                {isLogin ? '登录后即可生成同类练习题' : '以下为 AI 生成的同类练习题，不会存入错题本'}
              </Text>
            </View>
            <View className={styles.close} onClick={onClose}>
              <Icon name="closeMuted" size={14} />
            </View>
          </View>
          {renderMeta()}
        </View>

        {renderBody()}

        {renderFoot()}
      </View>
    </>
  );
};

export default VariantSheet;
