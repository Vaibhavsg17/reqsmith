# Algolia AI Search Setup Guide

This guide will help you set up Algolia DocSearch for AI-powered search in your ReqSmith documentation.

## Step 1: Create Algolia Account

1. Go to [Algolia](https://www.algolia.com/) and create a free account
2. Create a new application (choose the "Free" plan)
3. Note down your **Application ID**

## Step 2: Get API Keys

In your Algolia dashboard:

1. Go to **Settings** > **API Keys**
2. Copy these keys:
   - **Application ID** (e.g., `BH4D9OD16A`)
   - **Search-Only API Key** (safe to make public)
   - **Admin API Key** (keep private, for indexing only)

## Step 3: Manual Crawler Setup (Recommended)

Skip the DocSearch approval process and set up your own crawler for immediate AI search:

## Step 3: Manual Crawler Setup (Recommended)

Skip the DocSearch approval process and set up your own crawler for immediate AI search:

### Install Dependencies
```bash
npm install algoliasearch gray-matter
```

### Create Index
```bash
# Install Algolia CLI (optional, for index management)
npm install -g @algolia/cli

# Login to Algolia (optional)
algolia profile add

# Create index (optional, will be created automatically)
algolia indices create reqsmith
```

## Step 4: Environment Variables

Create `.env.local`:
```bash
ALGOLIA_APP_ID=your_app_id
ALGOLIA_SEARCH_API_KEY=your_search_api_key
ALGOLIA_ADMIN_API_KEY=your_admin_api_key
ALGOLIA_INDEX_NAME=reqsmith
```

## Step 5: Test Local Indexing

Index your documentation locally:
```bash
# Set environment variables
export ALGOLIA_APP_ID=your_app_id
export ALGOLIA_ADMIN_API_KEY=your_admin_api_key
export ALGOLIA_INDEX_NAME=reqsmith

# Run indexing
npm run index-docs
```

## Step 6: Configure GitHub Secrets

In your GitHub repository settings, add these secrets:
- `ALGOLIA_APP_ID`
- `ALGOLIA_SEARCH_API_KEY` 
- `ALGOLIA_ADMIN_API_KEY`

## Step 7: Deploy and Test

1. Push your changes to trigger deployment
2. The workflow will automatically:
   - Index your documentation
   - Build the site with search enabled
   - Deploy to GitHub Pages
3. Test search at: `https://vesperakshay.github.io/reqsmith/`

1. Start your docs site: `npm start`
2. Try searching in the search bar
3. You should see AI-enhanced search results with:
   - Smart highlighting
   - Contextual results
   - Fast, typo-tolerant search

## Features

Your AI search now includes:

✅ **Smart Search**: Natural language queries  
✅ **Instant Results**: Sub-100ms response times  
✅ **Typo Tolerance**: Finds results even with typos  
✅ **Contextual Highlighting**: Shows relevant snippets  
✅ **AI Enhancement**: Special highlighting for AI features  
✅ **Mobile Optimized**: Great experience on all devices  

## Troubleshooting

### Search not working?
1. Check your API keys in `.env.local`
2. Verify the index name matches
3. Check browser console for errors

### No results?
1. Make sure your docs are indexed (run `npm run index-docs`)
2. Check if the index exists in Algolia dashboard
3. Verify your content has the right structure

### Styling issues?
1. Check if CSS is loading properly
2. Verify theme compatibility
3. Check for conflicting styles

## Advanced Configuration

### Custom Search Parameters
```javascript
// In docusaurus.config.js
algolia: {
  searchParameters: {
    facetFilters: ['type:content'],
    hitsPerPage: 20,
    attributesToRetrieve: ['hierarchy', 'content', 'anchor', 'url'],
    attributesToHighlight: ['hierarchy', 'content'],
    attributesToSnippet: ['content:15'],
  }
}
```

### Custom Ranking
Prioritize AI-related content:
```javascript
customRanking: [
  'desc(weight.pageRank)',
  'desc(weight.ai_score)', // Custom AI relevance score
  'asc(weight.position)'
]
```

That's it! Your documentation now has powerful AI search capabilities. 🚀
