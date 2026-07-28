// DEMO MAP — the example that ships with the kit, of an app that does not exist. It is never
// copied into a project: /agent-kit:screens writes the project's own map from the project's own
// documents and code. Open screens.html beside it to see the viewer working, and change
// `platform` below to 'web' to see the other card frame.
//
// It is also the worked example of the format, which is documented in full in the skill's
// references/format.md: `meta` holds the platform and the id counters, `screens` holds one entry
// per screen with a `layout` of rows, and `transitions` holds the arrows. Ids are never reused —
// see the reference for why that rule is absolute.

window.SCREENS = {
  meta: {
    platform: 'mobile',        // mobile | web | desktop — picks the card frame
    nextScreenId: 11,          // the next free S<n>; never decreases
    nextTransitionId: 14,      // the next free T<n>; never decreases
  },

  screens: [
    {
      id: 'S1',
      title: 'Splash',
      purpose: 'Restores the stored session and decides where the app opens.',
      status: 'implemented',
      flow: 'Onboarding',
      code: 'src/screens/Splash.tsx',
      layout: [
        [{ type: 'image', label: 'Logo' }],
        [{ type: 'text', label: 'Loading…' }],
      ],
    },
    {
      id: 'S2',
      title: 'Sign in',
      purpose: 'Email and password for a returning person.',
      status: 'implemented',
      flow: 'Onboarding',
      code: 'src/screens/SignIn.tsx',
      layout: [
        [{ type: 'header', label: 'Welcome back' }],
        [{ type: 'input', label: 'Email' }],
        [{ type: 'input', label: 'Password' }],
        [{ type: 'button', label: 'Sign in' }],
        [{ type: 'text', label: 'Create account' }],
      ],
    },
    {
      id: 'S3',
      title: 'Sign up',
      purpose: 'Creates an account and sends the confirmation email.',
      status: 'planned',
      flow: 'Onboarding',
      layout: [
        [{ type: 'header', label: 'Create account' }],
        [{ type: 'input', label: 'Email' }],
        [{ type: 'input', label: 'Password' }],
        [{ type: 'text', label: 'Terms' }, { type: 'button', label: 'Continue' }],
      ],
    },
    {
      id: 'S4',
      title: 'Home',
      purpose: 'The library of saved items, searchable and filterable.',
      status: 'implemented',
      flow: 'Browse',
      code: 'src/screens/Home.tsx',
      layout: [
        [{ type: 'search', label: 'Search items' }],
        [{ type: 'chips', n: 4 }],
        [{ type: 'list', n: 4 }],
        [{ type: 'tabbar', n: 3 }],
      ],
    },
    {
      id: 'S5',
      title: 'Item',
      purpose: 'One item in full, with its rating and actions.',
      status: 'implemented',
      flow: 'Browse',
      code: 'src/screens/Item.tsx',
      layout: [
        [{ type: 'image', label: 'Cover' }],
        [{ type: 'header', label: 'Title' }],
        [{ type: 'custom', html: '<span style="letter-spacing:2px">★★★★☆</span>' }],
        [{ type: 'text', label: 'Description' }],
        [{ type: 'icon' }, { type: 'icon' }, { type: 'button', label: 'Save' }],
      ],
    },
    {
      id: 'S6',
      title: 'Filters',
      purpose: 'Narrows the library by tag and date.',
      status: 'planned',
      flow: 'Browse',
      type: 'overlay',
      parent: 'S4',
      layout: [
        [{ type: 'header', label: 'Filters' }],
        [{ type: 'chips', n: 6 }],
        [{ type: 'button', label: 'Apply' }],
      ],
    },
    {
      id: 'S7',
      title: 'Account',
      purpose: 'Profile, preferences, and the way out.',
      status: 'implemented',
      flow: 'Account',
      code: 'src/screens/Account.tsx',
      layout: [
        [{ type: 'header', label: 'Account' }],
        [{ type: 'card', label: 'Profile' }],
        [{ type: 'list' }],
        [{ type: 'text', label: 'Sign out' }],
        [{ type: 'tabbar', n: 3 }],
      ],
    },
    {
      id: 'S8',
      title: 'Invite friends',
      purpose: 'Shares a personal invite link and tracks who joined.',
      status: 'idea',
      flow: 'Account',
      layout: [
        [{ type: 'header', label: 'Invite' }],
        [{ type: 'text', label: 'Your link' }, { type: 'button', label: 'Copy' }],
        [{ type: 'list', n: 2 }],
      ],
    },
    {
      id: 'S9',
      title: 'Offline notice',
      purpose: 'Tells the person the app is working from its cache. Can appear over any screen.',
      status: 'implemented',
      flow: 'Browse',
      code: 'src/components/OfflineNotice.tsx',
      global: true,
      layout: [
        [{ type: 'icon' }, { type: 'text', label: 'You are offline' }],
        [{ type: 'button', label: 'Retry' }],
      ],
    },
    {
      id: 'S10',
      title: 'Printed digest',
      purpose: 'A weekly PDF of saved items, ordered by post. Dropped: no audience for it.',
      status: 'rejected',
      flow: 'Account',
      layout: [
        [{ type: 'header', label: 'Digest' }],
        [{ type: 'tabs', n: 2 }],
        [{ type: 'button', label: 'Order' }],
      ],
    },
  ],

  transitions: [
    { id: 'T1', from: 'S1', to: 'S2', trigger: 'no stored session' },
    { id: 'T2', from: 'S1', to: 'S4', trigger: 'session restored' },
    { id: 'T3', from: 'S2', to: 'S4', trigger: 'credentials accepted' },
    { id: 'T4', from: 'S2', to: 'S3', trigger: 'taps Create account' },
    { id: 'T5', from: 'S3', to: 'S4', trigger: 'account created', condition: 'email confirmed' },
    { id: 'T6', from: 'S4', to: 'S5', trigger: 'taps an item' },
    { id: 'T7', from: 'S4', to: 'S6', trigger: 'taps Filter' },
    { id: 'T8', from: 'S6', to: 'S4', trigger: 'applies filters' },
    { id: 'T9', from: 'S4', to: 'S7', trigger: 'Account tab' },
    { id: 'T10', from: 'S5', to: 'S4', trigger: 'back' },
    { id: 'T11', from: 'S7', to: 'S8', trigger: 'taps Invite friends' },
    { id: 'T12', from: 'S7', to: 'S2', trigger: 'signs out' },
    { id: 'T13', from: 'S4', to: 'S4', trigger: 'pull to refresh' },
  ],
};
