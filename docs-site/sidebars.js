/**
 * Creating a sidebar enables you to:
 - create an ordered group of docs
 - render a sidebar for each doc of that group
 - provide next/previous navigation

 The sidebars can be generated from the filesystem, or explicitly defined here.

 Create as many sidebars as you want.
 */

// @ts-check

/** @type {import('@docusaurus/plugin-content-docs').SidebarsConfig} */
const sidebars = {
  // By default, Docusaurus generates a sidebar from the docs folder structure
  tutorialSidebar: [
    {
      type: 'doc',
      id: 'index',
      label: 'Welcome',
    },
    {
      type: 'doc',
      id: 'installation',
      label: 'Installation',
    },
    {
      type: 'doc',
      id: 'quickstart',
      label: 'Quick Start',
    },
    {
      type: 'category',
      label: '🤖 AI Features',
      collapsed: false,
      items: [
        'concepts/ai-features'
      ]
    },
    {
      type: 'category',
      label: 'Concepts',
      items: [
        'concepts/requests',
        'concepts/templates',
        'concepts/environments',
        'concepts/history',
        'concepts/caching',
      ],
    },
    {
      type: 'category',
      label: 'CLI Commands',
      items: [
        'cli',
        'cli/request',
        'cli/template',
        'cli/env',
        'cli/history',
        'cli/config',
      ],
    },
    {
      type: 'category',
      label: 'Advanced Features',
      items: [
        'advanced/batch-requests',
        'advanced/graphql',
        'advanced/authentication',
        'advanced/troubleshooting',
      ],
    },
    {
      type: 'category',
      label: 'Examples',
      items: [
        'examples/basic-requests',
        'examples/advanced-scenarios',
        'examples/integrations',
        'examples/team-workflows',
        'examples/real-world-apis',
      ],
    },
    {
      type: 'doc',
      id: 'configuration',
      label: 'Configuration',
    },
  ],
};

export default sidebars;
