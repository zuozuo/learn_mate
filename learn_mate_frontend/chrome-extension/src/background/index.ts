import 'webextension-polyfill';
import { exampleThemeStorage } from '@extension/storage';

exampleThemeStorage.get().then(theme => {
  console.log('theme', theme);
});

// 监听扩展图标点击事件
chrome.action.onClicked.addListener(() => {
  console.log('Extension icon clicked');
  // 打开新标签页到 Learn Mate 聊天界面
  chrome.tabs.create({
    url: chrome.runtime.getURL('new-tab/index.html'),
  });
});

console.log('Background loaded');
console.log("Edit 'chrome-extension/src/background/index.ts' and save to reload.");
