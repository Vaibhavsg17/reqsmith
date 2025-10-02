# ReqSmith


⚡ **ReqSmith** is a powerful, cross-platform command-line tool designed to make API testing faster, smarter, and more efficient. Whether you’re working with REST, GraphQL, or complex workflows, ReqSmith simplifies the process of sending requests, analyzing responses, and managing test scenarios — all from your terminal.

Unlike traditional **CLI-based** API clients, ReqSmith comes with hybrid caching (in-memory + disk) for blazing-fast repeated requests, template and environment management for reusable workflows, and a rich output system that highlights and formats responses for maximum readability.

✨ A. Features
----------

*   🔗 **HTTP/REST API Testing** – Supports `GET`, `POST`, `PUT`, `PATCH`, `DELETE`, and `OPTIONS` methods
*   🧩 **GraphQL Support** – Easily run GraphQL queries and mutations
*   ⚡ **Hybrid Caching** – Memory + disk-based caching for optimal speed and persistence
*   📝 **Template Management** – Save, manage, and reuse request templates
*   🌍 **Environment Variables** – Seamlessly switch between dev, staging, and prod environments
*   ⏳ **Request History** – Track, review, and replay past requests
*   🎨 **Rich Output** – Color-coded responses with pretty-printed `JSON/XML` formatting
*   🤖 **AI Assistance (optional)** – Google Gemini-powered features for validation, suggestions, and analysis
*   🖥️ **Cross-Platform** – Works on **Windows**, **macOS**, and **Linux**



<img width="1879" height="954" alt="image" src="https://github.com/user-attachments/assets/ea8041b5-eabe-4159-b263-edcbdda6dafc" />


📦 B. Requirements
---------------

*   Python **3.9 or higher**
*   Network connectivity for API testing
*   (Optional) [**Gemini API Key**](https://aistudio.google.com/app/api-keys) for AI features
    

🚀 C. Installation
---------------
```   
pip install reqsmith
```


⚙️ D. Configuration
----------------

Customizable options include:

*   **Storage**: cache size, cache location
*   **Network**: timeouts, retries, proxy settings
*   **Output**: `JSON/XML` formatting preferences, color options
*   **AI**: `Gemini API key` and toggle for AI-powered features
    

🤖 E. AI Assistance
----------------

ReqSmith integrates with **Google’s Gemini API** for smarter API testing.

### Setup AI Features

1.  **Get a Gemini API Key:**
    
    *   Visit [**Google AI Studio**](https://aistudio.google.com/app/api-keys)
    *   Sign in with your Google account
    *   Generate a new API key
        
**Option A: Using ReqSmith config (recommended)** 
```
# Run the interactive setup
python scripts/setup_ai.py

# Or configure directly
reqsmith config set ai.gemini_api_key "your-api-key-here"
```
**Option B: Using environment variable export** 
```
export GEMINI_API_KEY="your-api-key-here"
```
    
    

### AI Capabilities

*   🔑 **Smart Header Suggestions** – Automatically suggest headers for APIs
*   ✅ **JSON Validation** – Validate and debug JSON with detailed explanations
*   📖 **Status Code Explanations** – Human-friendly descriptions of HTTP errors
*   🧪 **Test Scenario Generation** – Generate test cases for your endpoints
*   🔍 **API Analysis** – Detect patterns and provide optimization suggestions
    

### AI Usage Examples

```
# Get AI-suggested headers
reqsmith request get https://api.github.com/user --ai-headers

# AI-powered JSON validation
reqsmith validate --json '{"name": "test"}' --ai-suggest

# Natural language status explanations
reqsmith explain-status 404

# Generate test scenarios
reqsmith analyze https://api.example.com/users --generate-tests
```

🛠️ F. Development
---------------

Clone and install in development mode:
```
git clone https://github.com/VesperAkshay/reqsmith.git  
cd reqsmith  
```
```
pip install -e .
```

Run unit tests:
```
pytest
```


🗺️ G. Roadmap
-----------

*   Support for WebSocket testing
*   AI-assisted contract testing
*   Enhanced CLI autocomplete
*   Plugin system for custom integrations
    

📄 License
----------

This project is licensed under the **MIT License** – see the LICENSE file for details.
