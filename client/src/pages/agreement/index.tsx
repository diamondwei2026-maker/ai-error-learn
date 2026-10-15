import React from 'react';
import { Text, View } from '@tarojs/components';
import { useRouter } from '@tarojs/taro';

import NavBar from '@/components/NavBar';
import { AGREEMENT_TITLES, AGREEMENT_TYPE } from '@/constants';
import { getPageMinHeight } from '@/utils/layout';

import styles from './index.module.scss';

interface AgreementSection {
  heading: string;
  paragraphs: string[];
  bullets?: string[];
}

const PRIVACY_SECTIONS: AgreementSection[] = [
  {
    heading: '一、我们收集的信息',
    paragraphs: ['我们仅收集为你提供服务所必需的信息：'],
    bullets: [
      '你主动拍摄或从相册选择的题目图片；',
      '你授权的微信头像与昵称；',
      '用于识别账号的微信登录标识。',
    ],
  },
  {
    heading: '二、信息的使用',
    paragraphs: [
      '题目图片仅用于识别题目中的文字，帮助你建立错题记录；头像与昵称用于在应用内展示；登录标识用于在多设备之间同步你的错题数据。我们不会将上述信息用于与服务无关的用途。',
    ],
  },
  {
    heading: '三、第三方共享',
    paragraphs: [
      '为实现题目文字识别，你上传的题目图片会传输至第三方多模态大模型服务进行处理。除该识别用途外，我们不会向任何第三方出售或共享你的个人信息。',
    ],
  },
  {
    heading: '四、存储与安全',
    paragraphs: [
      '你的错题数据存储于云端数据库与服务器文件中，我们在传输过程中采取加密措施加以保护。',
    ],
  },
  {
    heading: '五、你的权利',
    paragraphs: [
      '你可以随时在「我的 → 完善资料」中更正头像与昵称；也可以通过「我的 → 注销账号」删除账号及全部云端数据，该操作不可恢复。',
    ],
  },
  {
    heading: '六、未成年人保护',
    paragraphs: ['如果你未满 18 周岁，请在监护人陪同下阅读本政策并使用本服务。'],
  },
  {
    heading: '七、联系我们',
    paragraphs: [
      '如对本政策有任何疑问，可通过小程序「我的」页面提供的联系方式与我们联系。',
    ],
  },
];

const TERMS_SECTIONS: AgreementSection[] = [
  {
    heading: '一、服务说明',
    paragraphs: ['「错题本」为你提供错题拍照识别、错题记录管理与多设备同步服务。'],
  },
  {
    heading: '二、账号规则',
    paragraphs: [
      '你通过微信授权登录后即可使用完整功能。请妥善保管账号信息，因账号泄露造成的损失由你自行承担。',
    ],
  },
  {
    heading: '三、内容规范',
    paragraphs: [
      '你在使用服务时上传的图片及填写的内容不得含有违法违规信息。我们有权对违规内容进行处理。',
    ],
  },
  {
    heading: '四、知识产权',
    paragraphs: [
      '本服务涉及的软件、界面设计等内容的知识产权归我们所有；你上传的题目内容归你所有。',
    ],
  },
  {
    heading: '五、免责声明',
    paragraphs: ['识别结果由人工智能生成，可能存在偏差，仅供参考，请以原始题目为准。'],
  },
  {
    heading: '六、协议变更',
    paragraphs: [
      '我们可能适时更新本协议，更新后将在小程序内公示。继续使用即视为接受更新后的协议。',
    ],
  },
];

/**
 * 协议页：隐私政策 / 用户协议共用同一页面，通过 query `type` 区分。
 * 纯文本分段排版，不引入富文本依赖。
 */
const AgreementPage = () => {
  const router = useRouter();
  const type =
    router.params.type === AGREEMENT_TYPE.terms ? AGREEMENT_TYPE.terms : AGREEMENT_TYPE.privacy;
  const sections = type === AGREEMENT_TYPE.terms ? TERMS_SECTIONS : PRIVACY_SECTIONS;

  return (
    <View className={styles.page} style={{ minHeight: getPageMinHeight() }}>
      <NavBar title={AGREEMENT_TITLES[type]} showBack />

      <View className={styles.body}>
        <Text className={styles.meta}>
          更新日期：2026-10-15{'\n'}生效日期：2026-10-15
        </Text>

        {sections.map((section) => (
          <View className={styles.section} key={section.heading}>
            <Text className={styles.heading}>{section.heading}</Text>
            {section.paragraphs.map((paragraph) => (
              <Text className={styles.paragraph} key={paragraph}>
                {paragraph}
              </Text>
            ))}
            {section.bullets
              ? section.bullets.map((bullet) => (
                  <Text className={styles.bullet} key={bullet}>
                    · {bullet}
                  </Text>
                ))
              : null}
          </View>
        ))}
      </View>
    </View>
  );
};

export default AgreementPage;
