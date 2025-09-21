// @ts-check
// `@type` JSDoc annotations allow editor autocompletion and type checking
// (when paired with `@ts-check`).
// There are various equivalent ways to declare your Docusaurus config.
// See: https://docusaurus.io/docs/api/docusaurus-config

import { themes as prismThemes } from 'prism-react-renderer';

// Load environment variables
require('dotenv').config();

/** @type {import('@docusaurus/types').Config} */
const config = {
  title: 'ReqSmith',
  tagline: 'Command-line API testing tool with hybrid caching and AI assistance',
  favicon: 'img/favicon.ico',

  // Set the production url of your site here
  url: process.env.NODE_ENV === 'production' ? 'https://vesperakshay.github.io' : 'http://localhost:3000',
  // Set the /<baseUrl>/ pathname under which your site is served
  // For GitHub pages deployment, it is often '/<projectName>/'
  baseUrl: process.env.NODE_ENV === 'production' ? '/reqsmith/' : '/',

  // GitHub pages deployment config.
  // If you aren't using GitHub pages, you don't need these.
  organizationName: 'VesperAkshay', // Usually your GitHub org/user name.
  projectName: 'reqsmith', // Usually your repo name.

  onBrokenLinks: 'throw',
  onBrokenMarkdownLinks: 'warn',

  // Even if you don't use internationalization, you can use this field to set
  // useful metadata like html lang. For example, if your site is Chinese, you
  // may want to replace "en" with "zh-Hans".
  i18n: {
    defaultLocale: 'en',
    locales: ['en'],
  },

  presets: [
    [
      'classic',
      /** @type {import('@docusaurus/preset-classic').Options} */
      ({
        docs: {
          sidebarPath: './sidebars.js',
          // Please change this to your repo.
          // Remove this to remove the "edit this page" links.
          editUrl:
            'https://github.com/VesperAkshay/reqsmith/tree/main/docs/',
          routeBasePath: '/', // Serve docs at site root
          // Set the main doc (index page)
          id: 'default',
        },
        blog: false, // Disable blog
        theme: {
          customCss: './src/css/custom.css',
        },
      }),
    ],
  ],

  themeConfig:
    /** @type {import('@docusaurus/preset-classic').ThemeConfig} */
    ({
      // Social card image (optional)
      // image: 'img/reqsmith-social-card.jpg',
      navbar: {
        title: 'ReqSmith',
        logo: {
          alt: 'ReqSmith Logo',
          src: 'img/logo.svg',
        },
        items: [
          {
            type: 'docSidebar',
            sidebarId: 'tutorialSidebar',
            position: 'left',
            label: 'Documentation',
          },
          {
            to: '/concepts/ai-features',
            label: '🤖 AI Features',
            position: 'left',
          },
          {
            href: 'https://github.com/VesperAkshay/reqsmith',
            label: 'GitHub',
            position: 'right',
          },
        ],
      },
      footer: {
        style: 'dark',
        links: [
          {
            title: 'Docs',
            items: [
              {
                label: 'Quick Start',
                to: '/quickstart',
              },
              {
                label: 'Installation',
                to: '/installation',
              },
              {
                label: 'CLI Reference',
                to: '/cli',
              },
            ],
          },
          {
            title: 'Community',
            items: [
              {
                label: 'GitHub Issues',
                href: 'https://github.com/VesperAkshay/reqsmith/issues',
              },
              {
                label: 'GitHub Discussions',
                href: 'https://github.com/VesperAkshay/reqsmith/discussions',
              },
            ],
          },
          {
            title: 'More',
            items: [
              {
                label: 'GitHub',
                href: 'https://github.com/VesperAkshay/reqsmith',
              },
              {
                label: 'PyPI',
                href: 'https://pypi.org/project/reqsmith/',
              },
            ],
          },
        ],
        copyright: `Copyright © ${new Date().getFullYear()} ReqSmith Team. Built with Docusaurus.`,
      },
      prism: {
        theme: prismThemes.github,
        darkTheme: prismThemes.dracula,
        additionalLanguages: ['bash', 'json', 'yaml', 'python'],
      },
      algolia: {
        appId: process.env.ALGOLIA_APP_ID || 'YIDG796A7B',
        apiKey: process.env.ALGOLIA_SEARCH_API_KEY || '2a3acba245bf5d98188264f1237e2243',
        indexName: process.env.ALGOLIA_INDEX_NAME || 'reqsmith',
        contextualSearch: false,
        searchParameters: {
          hitsPerPage: 8,
          attributesToHighlight: ['title', 'hierarchy.lvl1', 'hierarchy.lvl2', 'content'],
          attributesToSnippet: ['content:15'],
        },
        placeholder: 'Search ReqSmith docs...',
        searchPagePath: 'search',
        // Customize search modal
        transformItems: function (items) {
          return items.map(item => ({
            ...item,
            // Clean up the hierarchy display
            hierarchy: {
              ...item.hierarchy,
              lvl0: item.hierarchy.lvl0 || 'ReqSmith Docs',
            }
          }));
        },
      },
    }),

  plugins: [
    // AI Chat plugin configuration will be added here
  ],
};

export default config;
