// Drag and Drop & File Upload Logic

document.addEventListener('DOMContentLoaded', () => {
    const dropZone = document.getElementById('drop-zone');
    const fileInput = document.getElementById('file-input');
    const fileInfoText = document.getElementById('file-info-text');
    const filenameDisplay = document.getElementById('filename-display');
    const uploadForm = document.getElementById('upload-form');
    const loadingOverlay = document.getElementById('loading-overlay');
    const loadingText = document.getElementById('loading-text');

    if (!dropZone || !fileInput) return;

    // Trigger file selection on click
    dropZone.addEventListener('click', () => {
        fileInput.click();
    });

    // Drag-and-drop event listeners
    ['dragenter', 'dragover'].forEach(eventName => {
        dropZone.addEventListener(eventName, (e) => {
            e.preventDefault();
            e.stopPropagation();
            dropZone.classList.add('dragover');
        }, false);
    });

    ['dragleave', 'drop'].forEach(eventName => {
        dropZone.addEventListener(eventName, (e) => {
            e.preventDefault();
            e.stopPropagation();
            dropZone.classList.remove('dragover');
        }, false);
    });

    // Handle dropped files
    dropZone.addEventListener('drop', (e) => {
        const dt = e.dataTransfer;
        const files = dt.files;
        if (files.length > 0) {
            fileInput.files = files;
            updateFileInfo(files[0]);
        }
    });

    // Handle file selection via input dialog
    fileInput.addEventListener('change', (e) => {
        if (fileInput.files.length > 0) {
            updateFileInfo(fileInput.files[0]);
        }
    });

    function updateFileInfo(file) {
        const ext = file.name.split('.').pop().toLowerCase();
        if (ext === 'pdf' || ext === 'docx') {
            filenameDisplay.textContent = `${file.name} (${(file.size / 1024 / 1024).toFixed(2)} MB)`;
            fileInfoText.style.display = 'block';
        } else {
            alert('Invalid file format. Please upload a PDF or DOCX file.');
            fileInput.value = '';
            fileInfoText.style.display = 'none';
        }
    }

    // Form Submission & Dynamic Loading Cycle
    if (uploadForm) {
        uploadForm.addEventListener('submit', () => {
            loadingOverlay.style.display = 'flex';
            
            const messages = [
                "Uploading resume to secure container...",
                "Running text extraction parsers...",
                "Scanning technical skills & experience layers...",
                "Matching target job description key-values...",
                "Evaluating resume design and structural layouts...",
                "Generating AI improvements & grammar recommendations...",
                "Finalizing career role projections..."
            ];
            
            let currentMessageIndex = 0;
            loadingText.textContent = messages[currentMessageIndex];
            
            // Cycle messages every 2.5 seconds to inform user of progress
            const interval = setInterval(() => {
                currentMessageIndex++;
                if (currentMessageIndex < messages.length) {
                    loadingText.textContent = messages[currentMessageIndex];
                } else {
                    loadingText.textContent = "Almost done! Rendering dashboard layout...";
                    clearInterval(interval);
                }
            }, 2500);
        });
    }
});
