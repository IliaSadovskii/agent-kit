// A miniature screen map, in the format /agent-kit:screens writes. The cross-check reads the ids
// and the statuses out of it with a pattern; nothing here is executed by the kit.
window.SCREENS = {
  meta: { platform: 'mobile', nextScreenId: 5, nextTransitionId: 1 },

  screens: [
    { id: 'S1', title: 'Offer form', status: 'implemented' },
    { id: 'S2', title: 'Offer inbox', status: 'planned' },
    { id: 'S3', title: 'Bulk upload', status: 'rejected' },
    { id: 'S4', title: 'Offer history', status: 'idea' },
  ],

  transitions: [],
};
