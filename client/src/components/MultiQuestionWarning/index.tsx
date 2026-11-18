import { Text, View } from '@tarojs/components';

import Icon from '@/components/Icon';

import styles from './index.module.scss';

export interface MultiQuestionWarningProps {
  visible: boolean;
  /** 重新拍摄：交由页面打开既有 ActionSheet */
  onRetake: () => void;
  /** 手动输入：关闭弹窗，保留空表单 */
  onManualInput: () => void;
}

/** 整页多题阻断弹窗：一次只能录入一道题，遮罩点击不关闭 */
const MultiQuestionWarning = ({
  visible,
  onRetake,
  onManualInput,
}: MultiQuestionWarningProps) => {
  if (!visible) return null;

  return (
    <>
      <View className={styles.mask} />
      <View className={styles.wrap}>
        <View className={styles.dialog}>
          <View className={styles.body}>
            <View className={styles.warnIco}>
              <Icon name="warningRed" size={26} />
            </View>
            <Text className={styles.title}>这张图里有多道题</Text>
            <Text className={styles.desc}>
              当前版本一次只能录入一道题，请重新拍摄其中一道。
            </Text>
          </View>
          <View className={styles.foot}>
            <View className={styles.btn} onClick={onManualInput}>
              <Text>手动输入</Text>
            </View>
            <View className={styles.divider} />
            <View className={styles.btnPrimary} onClick={onRetake}>
              <Text>重新拍摄</Text>
            </View>
          </View>
        </View>
      </View>
    </>
  );
};

export default MultiQuestionWarning;
