export default defineAppConfig({
  pages: [
    'pages/index/index',
    'pages/library/index',
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
        text: '错题库',
        iconPath: 'assets/tabbar/library.png',
        selectedIconPath: 'assets/tabbar/library-selected.png',
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
