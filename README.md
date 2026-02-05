# 🏠 RoomReimagine AI

Transform your interior spaces with AI-powered design generation.

## ✨ Features

- 🎨 **AI-Powered Redesign**: Upload a room photo and get stunning AI-generated redesigns
- 🏡 **Multiple Styles**: Modern, Scandinavian, Industrial, Bohemian, Mid-Century, and Luxury
- 🎯 **Room-Specific**: Optimized for living rooms, bedrooms, kitchens, bathrooms, dining rooms, and offices
- 💡 **Smart Prompts**: AI-enhanced prompts for better results
- 📱 **Beautiful UI**: Modern, responsive design with smooth animations

## 🚀 Live Demo

[Visit RoomReimagine AI](https://roomreimagine-ai.onrender.com) *(Replace with your actual URL)*

## 🛠️ Tech Stack

- **Frontend**: HTML, CSS, JavaScript
- **Backend**: Flask (Python)
- **AI Models**: Replicate API (Interior Design SDXL, Room Designer, Flux)
- **Prompt Enhancement**: Azure OpenAI GPT-4

## 📦 Local Setup

1. **Clone the repository**:
   ```bash
   git clone https://github.com/YOUR_USERNAME/roomreimagine-ai.git
   cd roomreimagine-ai
   ```

2. **Create virtual environment**:
   ```bash
   python -m venv venv
   source venv/bin/activate  # On Windows: venv\Scripts\activate
   ```

3. **Install dependencies**:
   ```bash
   pip install -r requirements.txt
   ```

4. **Set up environment variables**:
   
   Create a `.env` file in the root directory:
   ```env
   REPLICATE_API_TOKEN=your_replicate_token
   AZURE_OPENAI_ENDPOINT=your_azure_endpoint
   AZURE_OPENAI_API_KEY=your_azure_key
   AZURE_OPENAI_API_VERSION=2024-02-15-preview
   AZURE_OPENAI_DEPLOYMENT_NAME=gpt-4o
   FLASK_ENV=development
   SECRET_KEY=your_secret_key
   ```

5. **Run the application**:
   ```bash
   python backend/app.py
   ```

6. **Open in browser**: Navigate to `http://localhost:8080`

## 🌐 Deployment

See [DEPLOYMENT_GUIDE.md](DEPLOYMENT_GUIDE.md) for detailed deployment instructions on Render.

## 📝 Usage

1. Upload a photo of your room
2. Select the room type
3. Choose your desired design style
4. (Optional) Add custom design preferences
5. Click "Generate Design"
6. Download your AI-generated redesign!

## 💳 API Costs

This application uses paid APIs:
- **Replicate**: ~$0.01-0.05 per image generation
- **Azure OpenAI**: ~$0.002 per prompt enhancement

Make sure you have credits in both services.

## 🤝 Contributing

Contributions are welcome! Please feel free to submit a Pull Request.

## 📄 License

This project is open source and available under the MIT License.

## 👤 Author

Built with ❤️ by Glassy India

---

**Need help?** Check out the [deployment guide](DEPLOYMENT_GUIDE.md) or open an issue!
