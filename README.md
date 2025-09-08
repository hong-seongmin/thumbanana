# 🍌 Thumbanana

AI-powered YouTube Thumbnail Generator using Gemini 2.5 Flash Image

## ⚡ Features

- **⚡ 1-Minute Generation**: Professional thumbnails ready in just 1 minute
- **🤖 AI-Powered**: Leverages Google's Gemini 2.5 Flash Image for high-quality text rendering
- **🌍 Multilingual**: Full Korean and English language support with automatic browser detection
- **📱 Responsive Design**: Works perfectly on desktop, tablet, and mobile
- **🎨 Brand Consistency**: Upload reference images to maintain your channel's unique style
- **🔄 Multiple Variants**: Generate up to 3 thumbnails at once (for registered users)
- **📋 History Management**: Save and manage all your generated thumbnails
- **👤 User Authentication**: Guest mode and full user accounts with enhanced features

## 🎨 Style Presets

- **Bold**: High contrast and dramatic lighting for maximum impact
- **Minimal**: Clean and sophisticated design
- **Comic**: Fun and energetic style
- **Tech**: Modern and futuristic aesthetic

## 🚀 Quick Start

### Prerequisites

- Python 3.8+
- UV package manager

### Docker Installation (Recommended)

```bash
git clone https://github.com/hong-seongmin/thumbanana.git
cd thumbanana
cp .env.example .env
# Edit .env file and set your GEMINI_API_KEY
docker-compose up -d
```

Visit: http://localhost:8000

See [DOCKER.md](DOCKER.md) for detailed Docker usage.

### Local Installation

1. Clone the repository:
```bash
git clone https://github.com/hong-seongmin/thumbanana.git
cd thumbanana
```

2. Install dependencies with UV:
```bash
uv sync
```

3. Set up environment variables:
```bash
cp .env.example .env
# Edit .env with your configuration
```

4. Run the application:
```bash
./start.sh
# or manually: uv run uvicorn app.main:app --host 0.0.0.0 --port 8000 --reload
```

See [USAGE.md](USAGE.md) for detailed startup options.

5. Open your browser and visit: `http://localhost:8000`

## 🌍 Language Support

The application automatically detects your browser language and supports:

- **Korean** (`ko`): Default language, accessible at `/`
- **English** (`en`): Accessible at `/en`

You can switch languages using the toggle in the navigation bar.

## 📁 Project Structure

```
thumbanana/
├── app/
│   ├── api/           # API endpoints
│   ├── i18n/          # Internationalization files
│   ├── static/        # Static files (CSS, JS, images)
│   ├── templates/     # Jinja2 templates
│   ├── utils/         # Utility functions
│   ├── config.py      # Configuration management
│   ├── database.py    # Database models and connection
│   └── main.py        # FastAPI application
├── storage/           # File storage (uploads, generated, cache)
├── tests/            # Test files
└── README.md
```

## 🛠 Technology Stack

- **Backend**: FastAPI (Python)
- **Frontend**: HTML5, TailwindCSS, Alpine.js, HTMX
- **Database**: SQLite (configurable)
- **AI**: Google Gemini 2.5 Flash Image API
- **Internationalization**: JSON-based translation system
- **Deployment**: UV package manager

## ⚙️ Configuration

Key environment variables:

```env
# API Keys
GEMINI_API_KEY=your_gemini_api_key

# Database
DATABASE_URL=sqlite:///thumbanana.db

# Server
HOST=0.0.0.0
PORT=8000
DEBUG=true

# File Storage
UPLOAD_DIR=storage/uploads
GENERATED_DIR=storage/generated
CACHE_DIR=storage/cache
```

## 📚 API Documentation

When running in development mode, visit `/docs` for interactive API documentation (Swagger UI).

### Main Endpoints

- `POST /api/generate/` - Generate thumbnails
- `GET /api/history` - Get generation history
- `POST /api/auth/login` - User authentication
- `POST /api/auth/register` - User registration

## 🌍 Internationalization

The app uses a JSON-based translation system:

- `app/i18n/ko.json` - Korean translations
- `app/i18n/en.json` - English translations
- `app/utils/i18n.py` - Translation utilities

Adding new languages:
1. Create `app/i18n/{language_code}.json`
2. Add language code to `SUPPORTED_LANGUAGES` in `app/utils/i18n.py`
3. Update language detection logic if needed

## 🧪 Testing

Run tests with:
```bash
uv run pytest
```

## 🚀 Deployment

For production deployment:

1. Set `DEBUG=false` in environment variables
2. Configure production database
3. Set up proper static file serving
4. Configure HTTPS and security headers

## 📄 License

This project is licensed under the MIT License.

## 🤝 Contributing

1. Fork the repository
2. Create a feature branch
3. Make your changes
4. Add tests if applicable
5. Submit a pull request

## 💬 Support

If you encounter any issues or have questions:

1. Check the [Issues](https://github.com/hong-seongmin/thumbanana/issues) page
2. Create a new issue if your problem isn't already reported
3. Provide detailed information about your environment and the issue

## 🌟 Powered By

- [Google Gemini AI](https://ai.google.dev/) - Advanced AI image generation
- [FastAPI](https://fastapi.tiangulo.com/) - Modern web framework
- [TailwindCSS](https://tailwindcss.com/) - Utility-first CSS framework
- [Alpine.js](https://alpinejs.dev/) - Lightweight JavaScript framework

## ☕ Support This Project

If you find Thumbanana useful, consider supporting the project:

[![Buy Me A Coffee](https://img.shields.io/badge/Buy%20Me%20A%20Coffee-support-orange?style=for-the-badge&logo=buy-me-a-coffee)](https://buymeacoffee.com/oursophy)

---

Made with ❤️ for YouTube creators worldwide