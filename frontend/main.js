document.addEventListener('DOMContentLoaded', () => {
    // --- Elements ---
    const uploadZone = document.getElementById('uploadZone');
    const imageInput = document.getElementById('imageInput');
    const previewContainer = document.getElementById('previewContainer');
    const previewImage = document.getElementById('previewImage');
    const changeImageBtn = document.getElementById('changeImageBtn');
    
    const styleCards = document.querySelectorAll('.style-card');
    const roomTypeSelect = document.getElementById('roomType');
    const promptInput = document.getElementById('prompt');
    const enhanceBtn = document.getElementById('enhanceBtn');
    const generateBtn = document.getElementById('generateBtn');
    
    const resultPlaceholder = document.getElementById('resultPlaceholder');
    const loadingOverlay = document.getElementById('loadingOverlay');
    const resultsContainer = document.getElementById('resultsContainer');
    const generatedResult = document.getElementById('generatedResult');
    const originalResult = document.getElementById('originalResult');
    const downloadBtn = document.getElementById('downloadBtn');
    
    const errorMessage = document.getElementById('errorMessage');

    // --- State ---
    let selectedStyle = 'modern';
    let uploadedFile = null;

    // --- Configuration ---
    const styleTips = {
        modern: "Tip: Focus on clean lines, neutral colors, and functional furniture.",
        scandinavian: "Tip: Use light wood, whites, and cozy textures.",
        industrial: "Tip: Exposed brick, metal accents, and open spaces work best.",
        bohemian: "Tip: Vibrant colors, patterns, and plants.",
        "mid-century": "Tip: Retro furniture, organic shapes, and wood accents.",
        luxury: "Tip: Marble, velvet, gold accents, and sophisticated lighting." 
    };

    // --- Event Listeners ---

    // 1. File Upload
    uploadZone.addEventListener('click', () => imageInput.click());
    
    imageInput.addEventListener('change', handleFileSelect);
    
    uploadZone.addEventListener('dragover', (e) => {
        e.preventDefault();
        uploadZone.classList.add('drag-over');
    });

    uploadZone.addEventListener('dragleave', () => {
        uploadZone.classList.remove('drag-over');
    });

    uploadZone.addEventListener('drop', (e) => {
        e.preventDefault();
        uploadZone.classList.remove('drag-over');
        if (e.dataTransfer.files.length) {
            imageInput.files = e.dataTransfer.files;
            handleFileSelect();
        }
    });

    changeImageBtn.addEventListener('click', (e) => {
        e.stopPropagation();
        resetUpload();
    });

    // 2. Style Selection
    styleCards.forEach(card => {
        card.addEventListener('click', () => {
            // UI Update
            styleCards.forEach(c => c.classList.remove('active'));
            card.classList.add('active');
            
            // Logic Update
            selectedStyle = card.dataset.style;
            updateStyleTip(selectedStyle);
        });
    });

    // 3. Prompt Enhancement
    enhanceBtn.addEventListener('click', async () => {
        const text = promptInput.value.trim();
        if (!text) {
            showError("Please enter a basic prompt first.");
            return;
        }

        setLoading(true, "Enhancing your prompt...");
        
        try {
            const response = await fetch('/api/test_prompt', {
                method: 'POST',
                headers: {'Content-Type': 'application/json'},
                body: JSON.stringify({
                    prompt: text,
                    style: selectedStyle,
                    room_type: roomTypeSelect.value
                })
            });
            const data = await response.json();
            
            if (data.success) {
                promptInput.value = data.enhanced;
                // Optional: Flash success
            } else {
                showError("Enhancement failed: " + data.error);
            }
        } catch (e) {
            showError("Network error during enhancement.");
        } finally {
            setLoading(false);
        }
    });

    // 4. Generation
    generateBtn.addEventListener('click', async () => {
        if (!uploadedFile) {
            showError("Please upload an image first.");
            return;
        }
        if (!promptInput.value.trim()) {
            showError("Please describe your vision.");
            return;
        }

        setLoading(true, "Designing your space... (This takes ~30s)");
        hideResults();

        const formData = new FormData();
        formData.append('image', uploadedFile);
        formData.append('prompt', promptInput.value.trim());
        formData.append('style', selectedStyle);
        formData.append('room_type', roomTypeSelect.value);

        try {
            const response = await fetch('/api/generate', {
                method: 'POST',
                body: formData
            });
            const data = await response.json();

            if (data.success) {
                showResults(data.original_image, data.generated_image);
                promptInput.value = data.prompt; // Update with the final used prompt
            } else {
                showError(data.error || "Generation failed.");
            }
        } catch (e) {
            showError("Network error during generation.");
            console.error(e);
        } finally {
            setLoading(false);
        }
    });

    // --- Functions ---

    function handleFileSelect() {
        const file = imageInput.files[0];
        if (!file) return;

        if (!file.type.startsWith('image/')) {
            showError("Please upload a valid image file.");
            return;
        }

        uploadedFile = file; // Store for sending
        
        // Show preview
        const reader = new FileReader();
        reader.onload = (e) => {
            previewImage.src = e.target.result;
            uploadZone.classList.add('hidden');
            previewContainer.classList.remove('hidden');
            previewContainer.classList.add('fade-in');
            hideError();
        };
        reader.readAsDataURL(file);
    }

    function resetUpload() {
        uploadedFile = null;
        imageInput.value = '';
        previewImage.src = '';
        previewContainer.classList.add('hidden');
        uploadZone.classList.remove('hidden');
        hideResults();
    }

    function updateStyleTip(style) {
        const tipEl = document.getElementById('styleTip');
        if (tipEl && styleTips[style]) {
            tipEl.textContent = styleTips[style];
        }
    }

    function setLoading(isLoading, message = "") {
        if (isLoading) {
            loadingOverlay.style.display = 'flex';
            loadingOverlay.querySelector('p').textContent = message;
            resultPlaceholder.classList.add('hidden');
            resultsContainer.style.display = 'none';
            generateBtn.disabled = true; // Disable button
        } else {
            loadingOverlay.style.display = 'none';
            generateBtn.disabled = false; // Re-enable button
        }
    }

    function hideResults() {
        resultsContainer.style.display = 'none';
        resultPlaceholder.classList.remove('hidden');
    }

    function showResults(originalUrl, generatedUrl) {
        resultPlaceholder.classList.add('hidden');
        resultsContainer.style.display = 'flex'; // Show stacked view
        
        // Update images
        generatedResult.src = generatedUrl;
        originalResult.src = originalUrl;
        
        // Update download link
        downloadBtn.href = generatedUrl;

        // Reset text
        errorMessage.textContent = "";

        // Scroll result into view smoothly
        resultsContainer.scrollIntoView({ behavior: 'smooth', block: 'start' });
    }

    function showError(msg) {
        // Simple alert for now, or use a toast
        alert(msg); 
    }
    
    // Init styles
    updateStyleTip('modern');
});
