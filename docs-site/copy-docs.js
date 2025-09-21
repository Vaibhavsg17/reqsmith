#!/usr/bin/env node

const fs = require('fs');
const path = require('path');

// Paths
const sourceDocsPath = path.join(__dirname, '..', 'docs');
const targetDocsPath = path.join(__dirname, 'docs');

// Ensure target directory exists
if (!fs.existsSync(targetDocsPath)) {
  fs.mkdirSync(targetDocsPath, { recursive: true });
}

// Function to copy files recursively
function copyRecursive(src, dest) {
  const stat = fs.statSync(src);
  
  if (stat.isDirectory()) {
    if (!fs.existsSync(dest)) {
      fs.mkdirSync(dest, { recursive: true });
    }
    
    const items = fs.readdirSync(src);
    items.forEach(item => {
      // Skip git directories and other unwanted files
      if (item === '.git' || item === 'node_modules' || item === 'docs.json') {
        return;
      }
      
      const srcPath = path.join(src, item);
      const destPath = path.join(dest, item);
      copyRecursive(srcPath, destPath);
    });
  } else {
    // Only copy .mdx and .md files, and images
    const ext = path.extname(src).toLowerCase();
    if (['.mdx', '.md', '.png', '.jpg', '.jpeg', '.gif', '.svg'].includes(ext)) {
      fs.copyFileSync(src, dest);
      console.log(`Copied: ${src} -> ${dest}`);
    }
  }
}

// Copy documentation files
try {
  console.log('Copying documentation files...');
  copyRecursive(sourceDocsPath, targetDocsPath);
  
  // Create static images directory if it doesn't exist
  const staticPath = path.join(__dirname, 'static');
  const staticImagesPath = path.join(staticPath, 'img');
  
  if (!fs.existsSync(staticImagesPath)) {
    fs.mkdirSync(staticImagesPath, { recursive: true });
  }
  
  // Copy images to static directory
  const sourceImagesPath = path.join(sourceDocsPath, 'images');
  if (fs.existsSync(sourceImagesPath)) {
    copyRecursive(sourceImagesPath, staticImagesPath);
  }
  
  // Copy logo if it exists
  const sourceLogoPath = path.join(sourceDocsPath, 'logo');
  if (fs.existsSync(sourceLogoPath)) {
    copyRecursive(sourceLogoPath, staticImagesPath);
  }
  
  console.log('✅ Documentation files copied successfully!');
  console.log('\nNext steps:');
  console.log('1. cd docs-site');
  console.log('2. npm install');
  console.log('3. npm start');
  
} catch (error) {
  console.error('❌ Error copying files:', error.message);
  process.exit(1);
}
