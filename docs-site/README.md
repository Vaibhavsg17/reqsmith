# ReqSmith Documentation Site

This directory contains the documentation website for ReqSmith built with Docusaurus and enhanced with AI features.

## Features

- 📚 **Complete Documentation**: All ReqSmith features and commands
- 🤖 **AI Assistant**: Interactive AI chatbot for instant help
- 🔍 **Advanced Search**: Algolia-powered search with AI enhancement
- 📱 **Mobile Responsive**: Works perfectly on all devices
- 🌙 **Dark Mode**: Support for light and dark themes
- ⚡ **Fast Performance**: Optimized static site generation

## Quick Start

1. **Install dependencies**:
   ```bash
   cd docs-site
   npm install
   ```

2. **Copy documentation files**:
   ```bash
   node copy-docs.js
   ```

3. **Start development server**:
   ```bash
   npm start
   ```

4. **Build for production**:
   ```bash
   npm run build
   ```

## AI Features Setup

### 1. Basic AI Chat (Demo Mode)
The AI chat is pre-configured with basic responses for common ReqSmith questions. No additional setup required for demo mode.

### 2. Advanced AI Integration

To connect with a real AI service, update the `getAIResponse` function in `src/components/AiChat/index.js`:

#### Option A: OpenAI Integration
```javascript
const getAIResponse = async (question) => {
  const response = await fetch('https://api.openai.com/v1/chat/completions', {
    method: 'POST',
    headers: {
      'Authorization': `Bearer ${process.env.REACT_APP_OPENAI_API_KEY}`,
      'Content-Type': 'application/json',
    },
    body: JSON.stringify({
      model: 'gpt-3.5-turbo',
      messages: [
        {
          role: 'system',
          content: 'You are a helpful assistant for ReqSmith, a CLI API testing tool. Answer questions about ReqSmith features, commands, and usage.'
        },
        {
          role: 'user',
          content: question
        }
      ],
      max_tokens: 500,
      temperature: 0.7,
    }),
  });

  const data = await response.json();
  return data.choices[0].message.content;
};
```

#### Option B: Google Gemini Integration
```javascript
const getAIResponse = async (question) => {
  const response = await fetch(`https://generativelanguage.googleapis.com/v1beta/models/gemini-pro:generateContent?key=${process.env.REACT_APP_GEMINI_API_KEY}`, {
    method: 'POST',
    headers: {
      'Content-Type': 'application/json',
    },
    body: JSON.stringify({
      contents: [{
        parts: [{
          text: `You are a helpful assistant for ReqSmith, a CLI API testing tool. Answer this question: ${question}`
        }]
      }],
      generationConfig: {
        temperature: 0.7,
        maxOutputTokens: 500,
      }
    }),
  });

  const data = await response.json();
  return data.candidates[0].content.parts[0].text;
};
```

### 3. Environment Variables

Create a `.env.local` file in the docs-site directory:

```env
# For OpenAI
REACT_APP_OPENAI_API_KEY=your_openai_api_key_here

# For Gemini
REACT_APP_GEMINI_API_KEY=your_gemini_api_key_here

# For Algolia Search (optional)
REACT_APP_ALGOLIA_APP_ID=your_algolia_app_id
REACT_APP_ALGOLIA_API_KEY=your_algolia_api_key
```

## Deployment Options

### 1. GitHub Pages (Free)

1. Build the site:
   ```bash
   npm run build
   ```

2. Deploy to GitHub Pages:
   ```bash
   npm run deploy
   ```

### 2. Vercel (Recommended)

1. Install Vercel CLI:
   ```bash
   npm i -g vercel
   ```

2. Deploy:
   ```bash
   vercel
   ```

3. For custom domain and environment variables, configure in Vercel dashboard.

### 3. Netlify

1. Connect your GitHub repository to Netlify
2. Set build command: `npm run build`
3. Set publish directory: `build`
4. Add environment variables in Netlify dashboard

### 4. Custom Server

1. Build the site:
   ```bash
   npm run build
   ```

2. Serve the `build` directory with any static file server.

## Customization

### AI Assistant Customization

Edit `src/components/AiChat/index.js` to:
- Change AI responses and behavior
- Modify the chat UI appearance
- Add more advanced AI features
- Integrate with different AI services

### Theme Customization

Edit `src/css/custom.css` to:
- Change colors and fonts
- Modify the AI chat styling
- Add custom components styling
- Override Docusaurus theme defaults

### Navigation Customization

Edit `sidebars.js` to:
- Reorganize documentation structure
- Add or remove sections
- Change navigation labels

## Features in Detail

### AI Chat Assistant
- 🤖 Floating chat button for easy access
- 💬 Context-aware responses about ReqSmith
- 📝 Code syntax highlighting in responses
- 🔗 Automatic link generation to relevant docs
- 📱 Mobile-responsive design

### Search Enhancement
- 🔍 Instant search across all documentation
- 🎯 AI-powered search suggestions
- 📊 Search analytics and insights
- 🚀 Fast, client-side search experience

### Performance Optimizations
- ⚡ Static site generation for fast loading
- 🗜️ Automatic code splitting
- 📦 Optimized bundle sizes
- 🖼️ Image optimization
- 🚀 CDN-ready deployment

## Troubleshooting

### Common Issues

1. **AI responses not working**:
   - Check API key configuration
   - Verify network connectivity
   - Check browser console for errors

2. **Search not working**:
   - Ensure Algolia configuration is correct
   - Check if search index is populated

3. **Build failures**:
   - Clear node_modules and reinstall
   - Check for TypeScript errors
   - Verify all dependencies are installed

### Getting Help

- Check the [Docusaurus documentation](https://docusaurus.io/docs)
- Report issues on the [ReqSmith GitHub repository](https://github.com/VesperAkshay/reqsmith/issues)
- Ask questions in [GitHub Discussions](https://github.com/VesperAkshay/reqsmith/discussions)

## Contributing

1. Fork the repository
2. Create a feature branch
3. Make your changes
4. Test the documentation site
5. Submit a pull request

## License

This documentation site is part of the ReqSmith project and follows the same MIT license.
