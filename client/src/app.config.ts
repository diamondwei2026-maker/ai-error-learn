export default defineAppConfig({
  pages: [
    'pages/index/index',
    'pages/library/index',
    'pages/quiz/index',
    'pages/edit/index',
  ],
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
        iconPath: 'assets/tabbar/home.svg',
        selectedIconPath: 'assets/tabbar/home-selected.svg',
      },
      {
        pagePath: 'pages/library/index',
        text: '题库',
        iconPath: 'assets/tabbar/library.svg',
        selectedIconPath: 'assets/tabbar/library-selected.svg',
      },
      {
        pagePath: 'pages/quiz/index',
        text: '刷题',
        iconPath: 'assets/tabbar/quiz.svg',
        selectedIconPath: 'assets/tabbar/quiz-selected.svg',
      },
    ],
  },
});
