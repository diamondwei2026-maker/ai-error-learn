import React, { useEffect, type PropsWithChildren } from 'react';
import { useDidShow, useDidHide } from '@tarojs/taro';
// 全局样式
import './app.scss';
import { fileRepo } from './services/repo/fileRepo';
import { storageRepo } from './services/repo/storageRepo';

function App(props: PropsWithChildren<Record<string, never>>) {
  useEffect(() => {
    // 启动时清理无主图片文件（对比 q:list 中的 imagePath 与文件系统实际文件）
    try {
      const validPaths = storageRepo
        .listQuestions()
        .map((item) => item.imagePath)
        .filter(Boolean) as string[];
      fileRepo.clearOrphans(validPaths);
      console.info('[App] startup cleanup done, valid images =', validPaths.length);
    } catch (error) {
      console.error('[App] startup cleanup failed', error);
    }
  }, []);

  // 对应 onShow
  useDidShow(() => {});

  // 对应 onHide
  useDidHide(() => {});

  return props.children;
}

export default App;
