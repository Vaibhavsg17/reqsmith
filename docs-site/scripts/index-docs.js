const algoliasearch = require('algoliasearch');
const fs = require('fs');
const path = require('path');
const matter = require('gray-matter');

require('dotenv').config({ path: require('path').resolve(__dirname, '../.env') });
require('dotenv').config({ path: require('path').resolve(__dirname, '../.env.local') });

// Initialize Algolia client
const client = algoliasearch(
  process.env.ALGOLIA_APP_ID,
  process.env.ALGOLIA_ADMIN_API_KEY
);

const index = client.initIndex(process.env.ALGOLIA_INDEX_NAME || 'reqsmith');

async function indexDocuments() {
  const docsDir = path.join(__dirname, '../docs');
  const records = [];
  let recordId = 0;

  function processFile(filePath, relativePath) {
    try {
      const content = fs.readFileSync(filePath, 'utf8');
      const { data, content: markdown } = matter(content);
      
      // Create URL path (remove .mdx/.md extension)
      let urlPath = relativePath
        .replace(/\\/g, '/')
        .replace(/\.(mdx?|md)$/, '')
        .replace(/\/index$/, '');
      
      // Create absolute URL for search results
      const baseUrl = process.env.NODE_ENV === 'production' 
        ? 'https://vesperakshay.github.io/reqsmith'
        : 'http://localhost:3000';
      let fullUrl;
      
      if (urlPath === 'index' || urlPath === '') {
        fullUrl = baseUrl + '/';
      } else {
        fullUrl = baseUrl + '/' + urlPath;
      }
      
      // Extract content by sections
      const sections = extractSections(markdown, data);
      
      sections.forEach((section, index) => {
        const record = {
          objectID: `${relativePath}_${recordId++}`,
          title: data.title || section.heading || 'ReqSmith Documentation',
          url: fullUrl,
          content: section.content,
          hierarchy: {
            lvl0: data.title || 'ReqSmith Documentation',
            lvl1: section.heading || data.title,
            lvl2: section.subheading,
            lvl3: section.subsubheading
          },
          type: 'content',
          // Add AI-related boost for search ranking
          _tags: section.content.toLowerCase().includes('ai') ? ['ai', 'artificial-intelligence'] : []
        };
        
        if (record.content.trim()) {
          records.push(record);
        }
      });
      
      console.log(`✅ Processed: ${relativePath}`);
    } catch (error) {
      console.error(`❌ Error processing ${filePath}:`, error.message);
    }
  }

  function extractSections(markdown, frontmatter) {
    const lines = markdown.split('\n');
    const sections = [];
    let currentSection = {
      heading: '',
      subheading: '',
      subsubheading: '',
      content: ''
    };

    lines.forEach(line => {
      const trimmedLine = line.trim();
      
      if (trimmedLine.startsWith('# ')) {
        // Save previous section
        if (currentSection.content.trim()) {
          sections.push({ ...currentSection });
        }
        // Start new section
        currentSection = {
          heading: trimmedLine.replace(/^# /, ''),
          subheading: '',
          subsubheading: '',
          content: ''
        };
      } else if (trimmedLine.startsWith('## ')) {
        // Save previous subsection
        if (currentSection.content.trim()) {
          sections.push({ ...currentSection });
        }
        currentSection.subheading = trimmedLine.replace(/^## /, '');
        currentSection.subsubheading = '';
        currentSection.content = '';
      } else if (trimmedLine.startsWith('### ')) {
        // Save previous subsubsection
        if (currentSection.content.trim()) {
          sections.push({ ...currentSection });
        }
        currentSection.subsubheading = trimmedLine.replace(/^### /, '');
        currentSection.content = '';
      } else if (!trimmedLine.startsWith('#')) {
        // Add content (skip other heading levels for now)
        currentSection.content += line + '\n';
      }
    });

    // Add the last section
    if (currentSection.content.trim()) {
      sections.push(currentSection);
    }

    return sections;
  }

  // Process all markdown files
  function walkDir(dir, baseDir = '') {
    if (!fs.existsSync(dir)) {
      console.log(`📁 Directory not found: ${dir}`);
      return;
    }

    const files = fs.readdirSync(dir);
    
    files.forEach(file => {
      const fullPath = path.join(dir, file);
      const relativePath = path.join(baseDir, file);
      
      if (fs.statSync(fullPath).isDirectory()) {
        walkDir(fullPath, relativePath);
      } else if (file.endsWith('.md') || file.endsWith('.mdx')) {
        processFile(fullPath, relativePath);
      }
    });
  }

  console.log('🔍 Starting documentation indexing...');
  console.log(`📂 Scanning directory: ${docsDir}`);
  
  // Process all markdown files
  walkDir(docsDir);

  // Upload to Algolia
  try {
    if (records.length === 0) {
      console.log('⚠️  No records to index. Check if docs directory exists and contains .md/.mdx files.');
      return;
    }

    console.log(`📤 Uploading ${records.length} records to Algolia...`);
    
    // Clear existing index first
    await index.clearObjects();
    console.log('🗑️  Cleared existing index');
    
    // Upload new records
    const { taskID } = await index.saveObjects(records);
    console.log(`✅ Successfully indexed ${records.length} records (Task ID: ${taskID})`);
    
    // Configure index settings for better search
    await index.setSettings({
      searchableAttributes: [
        'title',
        'hierarchy.lvl0',
        'hierarchy.lvl1', 
        'hierarchy.lvl2',
        'hierarchy.lvl3',
        'content'
      ],
      attributesToHighlight: [
        'title',
        'hierarchy.lvl1',
        'hierarchy.lvl2', 
        'content'
      ],
      attributesToSnippet: [
        'content:15'
      ],
      customRanking: [
        'desc(weight.pageRank)',
        'desc(weight.level)',
        'asc(weight.position)'
      ],
      minWordSizefor1Typo: 3,
      minWordSizefor2Typos: 7,
      allowTyposOnNumericTokens: false,
      ignorePlurals: true,
      advancedSyntax: true
    });
    
    console.log('⚙️  Index settings configured');
    console.log('🎉 Indexing completed successfully!');
    
  } catch (error) {
    console.error('❌ Indexing failed:', error);
    process.exit(1);
  }
}

// Run the indexing
if (require.main === module) {
  // Check for required environment variables
  if (!process.env.ALGOLIA_APP_ID || !process.env.ALGOLIA_ADMIN_API_KEY) {
    console.error('❌ Missing required environment variables:');
    console.error('   ALGOLIA_APP_ID');
    console.error('   ALGOLIA_ADMIN_API_KEY');
    console.error('');
    console.error('💡 Make sure to set these in your environment or .env file');
    process.exit(1);
  }
  
  indexDocuments().catch(console.error);
}

module.exports = { indexDocuments };
