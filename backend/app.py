import os
import uuid
import base64
import time
from io import BytesIO
from flask import Flask, request, jsonify, send_from_directory
from flask_cors import CORS
from PIL import Image
import replicate
import openai
from dotenv import load_dotenv
import requests
import threading

load_dotenv()

app = Flask(__name__, static_folder='../frontend')
CORS(app)

# Configuration
app.config['MAX_CONTENT_LENGTH'] = 16 * 1024 * 1024
UPLOAD_FOLDER = 'uploads'
OUTPUT_FOLDER = 'outputs'
ALLOWED_EXTENSIONS = {'png', 'jpg', 'jpeg', 'webp'}

os.makedirs(UPLOAD_FOLDER, exist_ok=True)
os.makedirs(OUTPUT_FOLDER, exist_ok=True)

REPLICATE_API_TOKEN = os.getenv('REPLICATE_API_TOKEN')
REPLICATE_API_TOKEN = os.getenv('REPLICATE_API_TOKEN')

# Azure OpenAI Configuration (v1.0.0+)
# We use the new AzureOpenAI client pattern
from openai import AzureOpenAI

azure_client = AzureOpenAI(
    api_key=os.getenv('AZURE_OPENAI_API_KEY'),
    api_version=os.getenv('AZURE_OPENAI_API_VERSION', "2023-05-15"),
    azure_endpoint=os.getenv('AZURE_OPENAI_ENDPOINT')
)
AZURE_DEPLOYMENT_NAME = os.getenv('AZURE_OPENAI_DEPLOYMENT_NAME', 'gpt-35-turbo')

replicate_client = replicate.Client(api_token=REPLICATE_API_TOKEN)

# Rate limiting
last_request_time = 0
REQUEST_INTERVAL = 15  # 15 seconds between requests (safe for free tier)
rate_lock = threading.Lock()

def wait_for_rate_limit():
    """Wait if we're hitting rate limits"""
    global last_request_time
    with rate_lock:
        current_time = time.time()
        time_since_last = current_time - last_request_time
        
        if time_since_last < REQUEST_INTERVAL:
            wait_time = REQUEST_INTERVAL - time_since_last
            print(f"Rate limiting: Waiting {wait_time:.1f} seconds...")
            time.sleep(wait_time)
        
        last_request_time = time.time()

def allowed_file(filename):
    return '.' in filename and filename.rsplit('.', 1)[1].lower() in ALLOWED_EXTENSIONS

def enhance_prompt(user_prompt, style="realistic", room_type="living room"):
    """Enhance prompt specifically for interior design with structure preservation"""
    try:
        system_prompt = f"""You are a professional interior designer creating prompts for AI image generation.
        
        Original request: "{user_prompt}"
        Style: {style}
        Room type: {room_type}
        
        IMPORTANT: The AI MUST keep the exact same room structure - same walls, windows, doors, layout, and perspective.
        ONLY change the interior decoration: furniture, colors, materials, lighting, decor.
        
        Create a detailed prompt that includes:
        1. Room type and style (Use terms like 'ArchDaily', 'Dezeen', 'Editorial photography')
        2. Specific furniture pieces and arrangement
        3. Color palette and materials (Mention textures like 'velvet', 'marble', 'oak wood')
        4. Lighting description (e.g., 'soft morning light', 'volumetric lighting', 'cinematic')
        5. Decor elements
        6. Keywords for quality: "photorealistic", "8k", "highly detailed", "unreal engine 5 render", "sharp focus"
        7. Structure preservation note: "identical room structure", "same architectural layout"
        
        Make it concise but detailed (2-3 sentences max)."""
        
        response = azure_client.chat.completions.create(
            model=AZURE_DEPLOYMENT_NAME, # In v1, we use 'model' but pass the deployment name
            messages=[
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": f"Create a redesign prompt for this {room_type}"}
            ],
            temperature=0.7,
            max_tokens=200
        )
        return response.choices[0].message.content
    except Exception as e:
        print(f"OpenAI error: {e}")
        # Better fallback prompts with high-quality keywords
        base_quality = "Professional interior photography, 8k, photorealistic, cinematic lighting, ArchDaily style, sharp focus."
        base_prompts = {
            "modern": f"A modern {room_type} with minimalist furniture, neutral colors, clean lines, and natural light. {base_quality} Same room structure, realistic rendering.",
            "scandinavian": f"A Scandinavian {room_type} with light wood floors, white walls, cozy textiles, and plants. {base_quality} Identical room layout, warm lighting, natural materials.",
            "industrial": f"An industrial style {room_type} with exposed brick, metal accents, concrete elements. {base_quality} Same architectural structure, moody lighting, open space.",
            "bohemian": f"A bohemian {room_type} with vibrant colors, mixed patterns, plants, layered textiles. {base_quality} Identical room shape, eclectic decor, warm atmosphere.",
            "mid-century": f"A mid-century modern {room_type} with walnut wood, retro furniture, geometric patterns. {base_quality} Same room structure, warm tones, vintage style."
        }
        return base_prompts.get(style, f"A beautifully designed {room_type} with {user_prompt}. {base_quality} Identical room structure, realistic.")

def prepare_image(image_path):
    """Prepare and optimize image"""
    try:
        img = Image.open(image_path)
        
        # Convert to RGB if necessary
        if img.mode in ('RGBA', 'LA'):
            background = Image.new('RGB', img.size, (255, 255, 255))
            if img.mode == 'RGBA':
                background.paste(img, mask=img.split()[-1])
            else:
                background.paste(img, mask=img)
            img = background
        
        # Resize if too large
        max_size = 1024
        if max(img.size) > max_size:
            ratio = max_size / max(img.size)
            new_size = tuple(int(dim * ratio) for dim in img.size)
            img = img.resize(new_size, Image.Resampling.LANCZOS)
        
        # Save optimized
        img.save(image_path, 'JPEG' if image_path.lower().endswith('.jpg') else 'PNG', 
                quality=85, optimize=True)
        return True
    except Exception as e:
        print(f"Image preparation error: {e}")
        return False

def save_image_from_output(output, output_path):
    """Handle different output types from Replicate models"""
    try:
        # Check if output is a FileOutput object
        if hasattr(output, 'read'):
            # It's a file-like object
            with open(output_path, 'wb') as f:
                f.write(output.read())
            return True
            
        # Check if output is a list with URL
        elif isinstance(output, list) and len(output) > 0:
            if isinstance(output[0], str) and output[0].startswith('http'):
                # Download from URL
                response = requests.get(output[0], timeout=30)
                if response.status_code == 200:
                    with open(output_path, 'wb') as f:
                        f.write(response.content)
                    return True
            elif hasattr(output[0], 'read'):
                # It's a file-like object in a list
                with open(output_path, 'wb') as f:
                    f.write(output[0].read())
                return True
                
        # Check if output is a string URL
        elif isinstance(output, str) and output.startswith('http'):
            response = requests.get(output, timeout=30)
            if response.status_code == 200:
                with open(output_path, 'wb') as f:
                    f.write(response.content)
                return True
                
        print(f"Unknown output format: {type(output)}")
        return False
        
    except Exception as e:
        print(f"Error saving image: {e}")
        return False

@app.route('/api/generate', methods=['POST'])
def generate_design():
    try:
        if 'image' not in request.files:
            return jsonify({'error': 'No image provided'}), 400
        
        file = request.files['image']
        if file.filename == '':
            return jsonify({'error': 'No image selected'}), 400
        
        if not allowed_file(file.filename):
            return jsonify({'error': 'Invalid file type. Use PNG, JPG, or WEBP'}), 400
        
        prompt = request.form.get('prompt', '').strip()
        style = request.form.get('style', 'modern')
        room_type = request.form.get('room_type', 'living room')
        
        if not prompt:
            return jsonify({'error': 'Please describe your design vision'}), 400
        
        # Save uploaded image
        filename = f"{uuid.uuid4()}_{file.filename}"
        input_path = os.path.join(UPLOAD_FOLDER, filename)
        file.save(input_path)
        
        # Prepare image
        prepare_image(input_path)
        
        # Enhance prompt
        enhanced_prompt = enhance_prompt(prompt, style, room_type)
        print(f"\n=== ENHANCED PROMPT ===\n{enhanced_prompt}\n=====================\n")
        
        # Apply rate limiting
        wait_for_rate_limit()
        
        generated_image_path = None
        
        # ========== TRY INTERIOR DESIGN MODELS ==========
        
        # ========== TRY INTERIOR DESIGN MODELS ==========
        
        # Priority 1: Rocket Digital AI - Interior Design SDXL (User Requested)
        # This model is specialized for interiors. We use high prompt_strength to maintain structure.
        try:
            print("Attempting RocketDigitalAI Interior Design SDXL (Priority 1)...")
            with open(input_path, 'rb') as img_file:
                output = replicate_client.run(
                    "rocketdigitalai/interior-design-sdxl:a3c091059a25590ce2d5ea13651fab63f447f21760e50c358d4b850e844f59ee",
                    input={
                        "image": img_file,
                        "prompt": f"{enhanced_prompt}, photorealistic, 8k, highly detailed, interior design magazine quality",
                        "negative_prompt": "ugly, deformed, blurry, watermark, low quality, distorted, sketches",
                        "scheduler": "DPM++ 2M Karras",
                        "depth_strength": 0.8, # Preserves depth/layout
                        "promax_strength": 0.8, # Preserves architectural lines
                        "refiner_strength": 0.5, # Enhances clarity
                        "num_inference_steps": 60,
                        "guidance_scale": 7
                    }
                )
            output_filename = f"generated_{uuid.uuid4()}.png"
            output_path = os.path.join(OUTPUT_FOLDER, output_filename)
            if save_image_from_output(output, output_path):
                generated_image_path = output_filename
                print("✓ Success with RocketDigitalAI")
        except Exception as e:
            print(f"RocketDigitalAI failed: {e}")

        # Priority 2: Room Designer (Balance)
        if not generated_image_path:
            try:
                print("Attempting room-designer (Priority 2)...")
                with open(input_path, 'rb') as img_file:
                    output = replicate_client.run(
                        "fofr/room-designer:6e7704a70176f4095d960a8f61c26c8b6f8a11c9b7a5b8f7e0c3d9d9b0e0d7e",
                        input={
                            "image": img_file,
                            "prompt": enhanced_prompt + ", maintained structure",
                            "negative_prompt": "structural changes, moved walls, blurry",
                            "steps": 35,
                            "seed": -1
                        }
                    )
                output_filename = f"generated_{uuid.uuid4()}.png"
                output_path = os.path.join(OUTPUT_FOLDER, output_filename)
                if save_image_from_output(output, output_path):
                    generated_image_path = output_filename
                    print("✓ Success with room-designer")
            except Exception as e:
                print(f"Room designer failed: {e}")

        # Priority 3: Flux Schnell (Fallback - High Quality but Loose Structure)
        if not generated_image_path:
             try:
                print(f"Attempting Flux Schnell (Priority 3)...")
                with open(input_path, 'rb') as img_file:
                    output = replicate_client.run(
                        "black-forest-labs/flux-schnell",
                        input={
                            "prompt": enhanced_prompt,
                            "aspect_ratio": "3:2",
                            "output_format": "png"
                        }
                    )
                output_filename = f"generated_{uuid.uuid4()}.png"
                output_path = os.path.join(OUTPUT_FOLDER, output_filename)
                if save_image_from_output(output, output_path):
                    generated_image_path = output_filename
                    print("✓ Success with Flux Schnell")
             except Exception as e:
                 print(f"Flux failed: {e}")

        # Final Fallback: SDXL
        if not generated_image_path:
             try:
                with open(input_path, 'rb') as img_file:
                    output = replicate_client.run(
                        "stability-ai/sdxl:39ed52f2a78e934b3ba6e2a89f5b1c712de7dfea535525255b1aa35c5565e08b",
                        input={
                            "prompt": enhanced_prompt,
                            "image": img_file,
                            "prompt_strength": 0.65,
                            "num_inference_steps": 40
                        }
                    )
                output_filename = f"generated_{uuid.uuid4()}.png"
                output_path = os.path.join(OUTPUT_FOLDER, output_filename)
                if save_image_from_output(output, output_path):
                    generated_image_path = output_filename
                else:
                    raise Exception("SDXL Failed")
             except Exception as e3:
                 raise Exception(f"All models failed. Last error: {e3}")
        
        if not generated_image_path:
            raise Exception("No image was generated")
        
        return jsonify({
            'success': True,
            'original_image': f'/uploads/{filename}',
            'generated_image': f'/outputs/{generated_image_path}',
            'prompt': enhanced_prompt,
            'message': '✨ Design generated! The AI has preserved your room structure while applying the new style.'
        })
        
    except Exception as e:
        error_msg = str(e)
        print(f"Generation error: {error_msg}")
        
        # User-friendly error messages
        if "DeploymentNotFound" in error_msg or "404" in error_msg:
             user_error = f"⚠️ Azure OpenAI Error: Deployment '{AZURE_DEPLOYMENT_NAME}' not found. Please check AZURE_OPENAI_DEPLOYMENT_NAME in your .env file."
        elif "rate limit" in error_msg.lower() or "429" in error_msg:
            user_error = "⚠️ Rate limit reached. You are on the free tier. Please wait 15 seconds."
        elif "credit" in error_msg.lower():
            user_error = "💰 Please add credit to your Replicate account (minimum $5)."
        elif "structure" in error_msg.lower():
            user_error = "🏠 Try being more specific about keeping the room structure identical."
        else:
            user_error = "❌ Generation failed. Try a different image or simplify your prompt."
        
        return jsonify({'error': user_error}), 500

# ... rest of the routes remain the same ...
@app.route('/api/status', methods=['GET'])
def api_status():
    return jsonify({
        'status': 'operational',
        'models': 'room-designer (Enhanced), ControlNet-Hough, SDXL Fallback',
        'rate_limit': '6 requests/minute (free tier)'
    })

@app.route('/api/test_prompt', methods=['POST'])
def test_prompt():
    try:
        data = request.json
        prompt = data.get('prompt', '')
        style = data.get('style', 'modern')
        room_type = data.get('room_type', 'living room')
        
        enhanced = enhance_prompt(prompt, style, room_type)
        
        return jsonify({
            'success': True,
            'original': prompt,
            'enhanced': enhanced
        })
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@app.route('/uploads/<filename>')
def serve_upload(filename):
    return send_from_directory(UPLOAD_FOLDER, filename)

@app.route('/outputs/<filename>')
def serve_output(filename):
    return send_from_directory(OUTPUT_FOLDER, filename)

@app.route('/')
def serve_frontend():
    return send_from_directory(app.static_folder, 'index.html')

@app.route('/<path:path>')
def serve_static(path):
    return send_from_directory(app.static_folder, path)

if __name__ == '__main__':
    app.run(debug=True, port=8080, threaded=True)


