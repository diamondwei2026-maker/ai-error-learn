import Taro from '@tarojs/taro';

import { isH5, isWeapp } from './platform';

export interface NavLayout {
  /** 状态栏高度（px） */
  statusBarHeight: number;
  /** 导航条内容高度（px），微信端与胶囊按钮对齐 */
  navHeight: number;
  /** 右侧操作距屏幕右边的距离（px），微信端避让胶囊 */
  rightInset: number;
}

const DEFAULT_LAYOUT: NavLayout = { statusBarHeight: 0, navHeight: 44, rightInset: 16 };

/** 计算自定义导航栏布局（仅微信端读取真实状态栏与胶囊位置） */
export function getNavLayout(): NavLayout {
  try {
    const info = Taro.getWindowInfo();
    const statusBarHeight = isWeapp ? info.statusBarHeight || 20 : 0;
    let navHeight = 44;
    let rightInset = 16;
    if (isWeapp) {
      const menu = Taro.getMenuButtonBoundingClientRect();
      if (menu && menu.height) {
        navHeight = (menu.top - statusBarHeight) * 2 + menu.height;
        rightInset = Math.max(16, info.windowWidth - menu.left + 8);
      }
    }
    return { statusBarHeight, navHeight, rightInset };
  } catch (error) {
    console.error('[layout] getNavLayout failed', error);
    return { ...DEFAULT_LAYOUT };
  }
}

/** H5 预览的 tabBar 高度（px）：Taro 原生 tabBar 覆盖在视口底部，需要补偿 */
const H5_TAB_BAR_HEIGHT = 50;

/**
 * H5 下 rpx → px 的换算系数。
 * 模板把根字号固定在 18px（见 src/index.html），而 H5 的 baseFontSize 为 37.5，
 * 因此 SCSS 中的 rpx 实际按 18/37.5 渲染；内联样式需保持一致，故用同一系数。
 */
const H5_RPX_TO_PX = 18 / 37.5;

/**
 * 将 rpx 数值转换为当前端可用的尺寸单位。
 * 内联样式不会被 postcss 处理，H5 下直接写 rpx 会失效（导致元素回退到默认尺寸），
 * 因此内联尺寸统一走本函数。
 */
export function toUnit(rpx: number): string {
  if (isH5) {
    return `${Number((rpx * H5_RPX_TO_PX).toFixed(2))}px`;
  }
  return `${rpx}rpx`;
}

/**
 * 页面最小高度。
 * - weapp：页面视口本身已排除 tabBar，100vh 即正确
 * - H5：视口含 tabBar，需减去其高度，避免底部内容被遮挡
 */
export function getPageMinHeight(): string {
  return isH5 ? `calc(100vh - ${H5_TAB_BAR_HEIGHT}px)` : '100vh';
}

/** 悬浮按钮距屏幕底部的距离，H5 需让开 tabBar */
export function getFabBottom(): string {
  const base = isH5 ? 132 : 32;
  return `calc(${toUnit(base)} + constant(safe-area-inset-bottom))`;
}

