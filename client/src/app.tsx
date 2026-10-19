import React, { useEffect, type PropsWithChildren } from "react";
import Taro, { useDidShow, useDidHide } from "@tarojs/taro";
// 全局样式
import "./app.scss";
import { fileRepo } from "./services/repo/fileRepo";
import { storageRepo } from "./services/repo/storageRepo";
import { privacyService } from "./services/privacyService";
import { syncService } from "./services/syncService";
import { useUserStore } from "./store/userStore";

function App(props: PropsWithChildren<Record<string, never>>) {
  useEffect(() => {
    // 启动时清理无主图片文件（对比 q:list 中的 imagePath 与文件系统实际文件）
    try {
      const validPaths = storageRepo
        .listQuestions()
        .map((item) => item.imagePath)
        .filter(Boolean) as string[];
      fileRepo.clearOrphans(validPaths);
      console.info(
        "[App] startup cleanup done, valid images =",
        validPaths.length,
      );
    } catch (error) {
      console.error("[App] startup cleanup failed", error);
    }

    // 恢复登录态；已登录则后台静默同步一次（失败不影响使用）
    try {
      useUserStore.getState().restore();
      if (useUserStore.getState().isLoggedIn) {
        void syncService.syncNow();
      }
    } catch (error) {
      console.error("[App] restore session failed", error);
    }

    // 隐私合规：注册被动监听 + 启动查询授权状态（非阻断，失败不阻塞启动）
    try {
      privacyService.init();
      privacyService.checkOnLaunch();
    } catch (error) {
      console.error("[App] privacy init failed", error);
    }

    // TODO(debug-netprobe): 临时网络探针，排查结束后删除
    const probeTargets = [
      "https://example.com/",
      "https://errorlearn.diamondwtech.com/api/v1/health",
    ];
    const probe = (url: string) =>
      new Promise<Record<string, unknown>>((resolve) => {
        const startedAt = Date.now();
        Taro.request({
          url,
          method: "GET",
          timeout: 8000,
          success: (res) =>
            resolve({
              url,
              ok: true,
              status: res.statusCode,
              cost: Date.now() - startedAt,
            }),
          fail: (err) => {
            const failure = err as { errMsg?: string; errno?: number };
            resolve({
              url,
              ok: false,
              errMsg: failure.errMsg,
              errno: failure.errno,
              cost: Date.now() - startedAt,
            });
          },
        });
      });
    probeTargets
      .reduce<Promise<void>>(
        (chain, url) =>
          chain
            .then(() => probe(url))
            .then((result) =>
              console.warn("[netprobe]", JSON.stringify(result)),
            ),
        Promise.resolve(),
      )
      .then(() => {
        Taro.getNetworkType()
          .then((res) =>
            console.warn("[netprobe] network", JSON.stringify(res)),
          )
          .catch((error) => console.warn("[netprobe] network failed", error));
      });
  }, []);

  // 对应 onShow
  useDidShow(() => {});

  // 对应 onHide
  useDidHide(() => {});

  return props.children;
}

export default App;
