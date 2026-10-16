export default defineAppConfig({
  pages: [
    'pages/index/index',
    'pages/library/index',
    'pages/quiz/index',
    'pages/profile/index',
    'pages/edit/index',
    'pages/profile/edit/index',
    'pages/agreement/index',
  ],
  lazyCodeLoading: 'requiredComponents',
  window: {
    navigationStyle: 'custom',
    backgroundTextStyle: 'light',
    navigationBarBackgroundColor: '#ffffff',
    navigationBarTitleText: '错题本',
    navigationBarTextStyle: 'black',
    backgroundColor: '#FAFBFD',
  },
  tabBar: {
    custom: false,
    color: '#4B5563',
    selectedColor: '#056B36',
    backgroundColor: '#FFFFFF',
    borderStyle: 'white',
    list: [
      {
        pagePath: 'pages/index/index',
        text: '首页',
        iconPath: 'assets/tabbar/home.png',
        selectedIconPath: 'assets/tabbar/home-selected.png',
      },
      {
        pagePath: 'pages/library/index',
        text: '题库',
        iconPath: 'assets/tabbar/library.png',
        selectedIconPath: 'assets/tabbar/library-selected.png',
      },
      {
        pagePath: 'pages/quiz/index',
        text: '刷题',
        iconPath: 'assets/tabbar/quiz.png',
        selectedIconPath: 'assets/tabbar/quiz-selected.png',
      },
      {
        pagePath: 'pages/profile/index',
        text: '我的',
        iconPath: 'assets/tabbar/profile.png',
        selectedIconPath: 'assets/tabbar/profile-selected.png',
      },
    ],
  },
});
