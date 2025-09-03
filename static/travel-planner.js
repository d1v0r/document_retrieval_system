function markdownToHtml(markdown) {
    let text = markdown
        .replace(/\*\*([^*]+)\*\*/g, '$1')
        .replace(/\*([^*]+)\*/g, '$1')
        .replace(/`([^`]+)`/g, '$1')
        .replace(/\[([^\]]+)\]\([^)]+\)/g, '$1')
        .replace(/^#+\s*/gm, '')
        .replace(/\n{3,}/g, '\n\n')
        .trim();
    
    return text;
}

document.addEventListener('DOMContentLoaded', function() {
    const interestBtns = document.querySelectorAll('.interest-btn');
    const customInterestInput = document.getElementById('customInterest');
    const addInterestBtn = document.getElementById('addInterestBtn');
    const selectedInterestsContainer = document.getElementById('selectedInterests');
    const preferencesInput = document.getElementById('preferences');
    const selectedInterests = new Set();

    const dropZone = document.getElementById('dropZone');
    const fileInput = document.getElementById('fileInput');
    const uploadBtn = document.getElementById('uploadBtn');
    const fileList = document.getElementById('fileList');
    const uploadStatus = document.getElementById('uploadStatus');
    const documentList = document.getElementById('documentList');

    if (fileInput && uploadBtn) {
        dropZone.addEventListener('click', () => fileInput.click());
        
        uploadBtn.addEventListener('click', async () => {
            if (fileInput.files.length === 0) {
                showStatus('Please select files to upload first', 'error');
                return;
            }
            await handleFileUpload(fileInput.files);
        });

        ['dragenter', 'dragover'].forEach(eventName => {
            dropZone.addEventListener(eventName, highlight, false);
        });

        ['dragleave', 'drop'].forEach(eventName => {
            dropZone.addEventListener(eventName, unhighlight, false);
        });

        dropZone.addEventListener('drop', handleDrop, false);
    }

    async function handleFileUpload(files) {
        const formData = new FormData();
        const validTypes = [
            'application/pdf', 
            'text/plain', 
            'text/markdown', 
            'text/x-markdown',
            'application/msword',
            'application/vnd.openxmlformats-officedocument.wordprocessingml.document'
        ];
        
        let validFiles = 0;
        for (const file of files) {
            if (validTypes.includes(file.type) || file.name.match(/\.(pdf|txt|md|doc|docx)$/i)) {
                formData.append('files', file);
                validFiles++;
                console.log(`Adding file: ${file.name}, type: ${file.type}`);
            } else {
                console.warn(`Skipping unsupported file: ${file.name}, type: ${file.type}`);
            }
        }

        if (validFiles === 0) {
            const errorMsg = 'No valid files selected. Please upload PDF, TXT, MD, DOC, or DOCX files only.';
            console.error(errorMsg);
            showStatus(errorMsg, 'error');
            return false;
        }

        showStatus('Uploading files...', 'uploading');
        uploadBtn.disabled = true;

        try {
            console.log('Sending upload request to /api/upload');
            const response = await fetch('http://localhost:5000/api/upload', {
                method: 'POST',
                body: formData,
                // Don't set Content-Type header, let the browser set it with the correct boundary
                headers: {
                    'Accept': 'application/json'
                }
            });

            console.log('Upload response status:', response.status);
            
            let result;
            try {
                result = await response.json();
                console.log('Upload response:', result);
            } catch (jsonError) {
                console.error('Error parsing JSON response:', jsonError);
                throw new Error('Invalid response from server');
            }

            if (!response.ok) {
                const errorMsg = result.detail || result.message || 'File upload failed';
                console.error('Upload failed:', errorMsg);
                throw new Error(errorMsg);
            }

            showStatus('Files uploaded and processed successfully!', 'success');
            updateDocumentList();
            fileInput.value = ''; 
            updateFileList([]);

        } catch (error) {
            console.error('Upload error:', error);
            const errorMessage = error.message || 'Failed to upload files. Please try again.';
            showStatus(`Error: ${errorMessage}`, 'error');
        } finally {
            uploadBtn.disabled = false;
        }
    }

    function highlight(e) {
        e.preventDefault();
        e.stopPropagation();
        dropZone.classList.add('border-blue-500', 'bg-blue-50');
    }

    function unhighlight(e) {
        e.preventDefault();
        e.stopPropagation();
        dropZone.classList.remove('border-blue-500', 'bg-blue-50');
    }

    function handleDrop(e) {
        e.preventDefault();
        unhighlight(e);
        const dt = e.dataTransfer;
        const files = dt.files;
        fileInput.files = files;
        updateFileList(files);
    }

    function updateFileList(files) {
        fileList.innerHTML = '';
        if (files.length === 0) return;

        const list = document.createElement('ul');
        list.className = 'space-y-2';

        for (const file of files) {
            const item = document.createElement('li');
            item.className = 'flex items-center justify-between text-sm';
            item.innerHTML = `
                <span class="truncate">${file.name}</span>
                <span class="text-gray-500 text-xs">${formatFileSize(file.size)}</span>
            `;
            list.appendChild(item);
        }

        fileList.appendChild(list);
    }

    function formatFileSize(bytes) {
        if (bytes === 0) return '0 Bytes';
        const k = 1024;
        const sizes = ['Bytes', 'KB', 'MB', 'GB'];
        const i = Math.floor(Math.log(bytes) / Math.log(k));
        return parseFloat((bytes / Math.pow(k, i)).toFixed(2)) + ' ' + sizes[i];
    }

    function showStatus(message, type = 'info') {
        if (!uploadStatus) return;

        uploadStatus.className = 'mt-4 p-3 rounded-md';
        uploadStatus.innerHTML = '';

        const icon = {
            success: '✅',
            error: '❌',
            info: 'ℹ️',
            uploading: '⏳'
        }[type] || 'ℹ️';

        uploadStatus.innerHTML = `
            <div class="flex items-center space-x-2 text-sm">
                <span>${icon}</span>
                <span>${message}</span>
            </div>
        `;
    }

        async function updateDocumentList() {
        try {
            const response = await fetch('/api/documents');
            const result = await response.json();

            if (response.ok && result.documents && result.documents.length > 0) {
                const list = document.createElement('div');
                list.className = 'space-y-2';

                result.documents.forEach(doc => {
                    const item = document.createElement('div');
                    item.className = 'flex items-center justify-between text-sm p-2 hover:bg-gray-50 rounded';
                    item.innerHTML = `
                        <span class="truncate">${doc.name}</span>
                        <span class="text-gray-500 text-xs">${formatFileSize(doc.size)}</span>
                    `;
                    list.appendChild(item);
                });

                documentList.innerHTML = '';
                documentList.appendChild(list);
            } else {
                documentList.innerHTML = '<p class="text-sm text-gray-500 text-center py-4">No documents uploaded yet</p>';
            }
        } catch (error) {
            console.error('Error fetching documents:', error);
            documentList.innerHTML = '<p class="text-sm text-red-500 text-center py-4">Error loading documents</p>';
        }
    }

        updateDocumentList();

    interestBtns.forEach(btn => {
        btn.addEventListener('click', function() {
            const interest = this.getAttribute('data-interest');
            toggleInterest(interest, this);
        });
    });

    addInterestBtn.addEventListener('click', addCustomInterest);
    
    customInterestInput.addEventListener('keypress', function(e) {
        if (e.key === 'Enter') {
            e.preventDefault();
            addCustomInterest();
        }
    });

    function toggleInterest(interest, button) {
        if (selectedInterests.has(interest)) {
            selectedInterests.delete(interest);
            button.classList.remove('selected');
        } else {
            selectedInterests.add(interest);
            button.classList.add('selected');
        }
        updateSelectedInterests();
    }

    function addCustomInterest() {
        const interest = customInterestInput.value.trim();
        if (interest && !selectedInterests.has(interest)) {
            selectedInterests.add(interest);
            customInterestInput.value = '';
            updateSelectedInterests();
        }
    }

    function updateSelectedInterests() {
        selectedInterestsContainer.innerHTML = '';
        selectedInterests.forEach(interest => {
            const tag = document.createElement('div');
            tag.className = 'selected-interest';
            tag.innerHTML = `
                ${interest}
                <button type="button" data-interest="${interest}" aria-label="Remove ${interest}">&times;</button>
            `;
            selectedInterestsContainer.appendChild(tag);
        });

        document.querySelectorAll('.selected-interest button').forEach(btn => {
            btn.addEventListener('click', function() {
                const interest = this.getAttribute('data-interest');
                selectedInterests.delete(interest);
                updateSelectedInterests();
                
                interestBtns.forEach(btn => {
                    if (btn.getAttribute('data-interest') === interest) {
                        btn.classList.remove('selected');
                    }
                });
            });
        });

        preferencesInput.value = Array.from(selectedInterests).join(', ');
    }

    const form = document.getElementById('itineraryForm');
    const newPlanBtn = document.getElementById('new-plan-btn');
    
    if (!form) return;
    
    // Add event listener for the new plan button
    if (newPlanBtn) {
        newPlanBtn.addEventListener('click', function() {
            // Scroll to the form
            form.scrollIntoView({ behavior: 'smooth' });
            // Reset the form
            form.reset();
            // Clear any existing results
            const resultsDiv = document.getElementById('results');
            if (resultsDiv) {
                resultsDiv.classList.add('hidden');
            }
            // Clear selected interests
            const selectedInterests = document.getElementById('selectedInterests');
            if (selectedInterests) {
                selectedInterests.innerHTML = '';
            }
            // Reset the preferences hidden input
            const preferencesInput = document.getElementById('preferences');
            if (preferencesInput) {
                preferencesInput.value = '';
            }
        });
    }

    const style = document.createElement('style');
    style.textContent = `
        /* Position the title at the bottom of the content */
        .bg-white {
            display: flex;
            flex-direction: column;
        }
        
        #itinerary-content {
            order: 1;
        }
        
        .itinerary-title {
            order: 2;
            margin-top: 2rem;
            margin-bottom: 1rem;
        }
        
        .spinner {
            display: inline-block;
            animation: spin 1s linear infinite;
        }
        @keyframes spin {
            0% { transform: rotate(0deg); }
            100% { transform: rotate(360deg); }
        }
        .hidden { display: none; }
    `;
    document.head.appendChild(style);

        form.addEventListener('submit', generateItinerary);

    async function generateItinerary(event) {
        event.preventDefault();
        
        const city = document.getElementById('city').value.trim();
        const days = document.getElementById('days').value;
        const preferences = document.getElementById('preferences').value.trim();
        const generateButton = document.getElementById('generate-itinerary-btn');
        const spinner = generateButton ? generateButton.querySelector('.spinner') : null;
        
        if (spinner) spinner.classList.remove('hidden');
        
        try {
            const response = await fetch('/api/generate-itinerary', {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json',
                },
                body: JSON.stringify({
                    destination: city,
                    duration: parseInt(days, 10),
                    preferences: preferences || 'No specific preferences'
                })
            });

            const data = await response.json();
            
            if (!response.ok) {
                console.error('API Error:', data);
                throw new Error(data.detail?.message || 'Failed to generate itinerary');
            }
            
            // Show the results container
            const resultsDiv = document.getElementById('results');
            if (resultsDiv) {
                resultsDiv.classList.remove('hidden');
                resultsDiv.innerHTML = ''; // Clear previous results
                
                // Create a container for the itinerary
                const container = document.createElement('div');
                container.className = 'bg-white p-6 rounded-lg shadow-md';
                
                // Create content container first
                const contentDiv = document.createElement('div');
                contentDiv.id = 'itinerary-content';
                container.appendChild(contentDiv);
                
                // Add container to results
                resultsDiv.appendChild(container);
                
                // Add title after content (will be moved to the bottom by CSS)
                const title = document.createElement('h2');
                title.className = 'itinerary-title text-2xl font-bold mt-8 mb-6 text-center';
                title.textContent = `Your ${data.duration}-Day Travel Plan for ${data.destination}`;
                container.appendChild(title);
                
                // Hide the generate button
                const generateBtn = document.getElementById('generate-itinerary-btn');
                if (generateBtn) {
                    generateBtn.style.display = 'none';
                }
                
                // Display the itinerary
                if (data.itinerary) {
                    displayItinerary(data.itinerary);
                    
                    // Show action buttons
                    const actionButtons = document.querySelector('.action-buttons');
                    if (actionButtons) {
                        actionButtons.classList.remove('hidden');
                    }
                    
                    // Set up download button
                    const downloadBtn = document.getElementById('download-pdf-btn');
                    if (downloadBtn) {
                        downloadBtn.onclick = () => generatePDF(data.itinerary, `${city.replace(/\s+/g, '_')}_Itinerary`);
                    }
                }
            }
            
        } catch (error) {
            console.error('Error generating itinerary:', error);
            showStatus(`Error: ${error.message || 'Failed to generate itinerary. Please try again.'}`, 'error');
        } finally {
            const generateButton = document.getElementById('generate-itinerary-btn');
            if (generateButton) {
                generateButton.disabled = false;
                const buttonText = generateButton.querySelector('span');
                const spinner = generateButton.querySelector('.spinner');
                if (buttonText) buttonText.textContent = 'Generate travel plan';
                if (spinner) spinner.classList.add('hidden');
            }
        }
    }
    
    function generatePDF(content, filename = 'itinerary.pdf') {
        try {
            const { jsPDF } = window.jspdf;
            const doc = new jsPDF();

            // Set default font (don't need to load custom font)
            doc.setFont('helvetica');
            
            // Add title
            doc.setFontSize(18);
            doc.setTextColor(40, 62, 80);
            doc.text('Travel Itinerary', 105, 20, { align: 'center' });
            
            // Add content with word wrap
            doc.setFontSize(11);
            doc.setTextColor(0, 0, 0);
            
            // Split content into lines and process each line
            const lines = content.split('\n');
            let y = 30; // Starting Y position after title
            
            for (let i = 0; i < lines.length; i++) {
                const line = lines[i].trim();
                if (!line) {
                    y += 5; // Add some space for empty lines
                    continue;
                }
                
                // Check if this is a day header
                if (line.match(/^Day \d+:/i)) {
                    doc.setFontSize(14);
                    doc.setFont(undefined, 'bold');
                    y += 10; // Extra space before day header
                    doc.text(line, 20, y);
                    y += 10;
                    doc.setFontSize(11);
                    doc.setFont(undefined, 'normal');
                    continue;
                }
                
                // Simple text addition with word wrap
                const splitText = doc.splitTextToSize(line, 170);
                doc.text(splitText, 20, y);
                y += splitText.length * 7; // Adjust line height
                
                // Add page break if needed
                if (y > 270) {  // Near bottom of A4
                    doc.addPage();
                    y = 20;
                } else {
                    y += 5; // Space between paragraphs
                }
            }
            
            doc.save(filename);
            return true;
            
        } catch (error) {
            console.error('Error generating PDF:', error);
            showStatus('Error generating PDF. You can try printing the page instead (Ctrl+P).', 'error');
            return false;
        }
    }
    
    function displayItinerary(itinerary) {
        console.log('Displaying itinerary:', itinerary);
        const resultsDiv = document.getElementById('results');
        const itineraryDiv = document.getElementById('itinerary-content');
        
        if (!resultsDiv || !itineraryDiv) {
            console.error('Required elements not found in the DOM');
            return;
        }
        
        // Clear any existing content
        itineraryDiv.innerHTML = '';
        
        itineraryDiv.innerHTML = '';
        
        let content = itinerary;

            content = content
            .replace(/^#\s*[\d\-Day]+\s+[^\n]+/i, '')
            .replace(/\*\*Morning([^*]+)\*\*/gi, '\nMorning $1\n')
            .replace(/\*\*Afternoon([^*]+)\*\*/gi, '\nAfternoon $1\n')
            .replace(/\*\*Evening([^*]+)\*\*/gi, '\nEvening $1\n')
            .replace(/\*\*([^*]+)\*\*/g, '$1')
            .replace(/\n{3,}/g, '\n\n');

        
        const contentDiv = document.createElement('div');
        contentDiv.className = 'prose max-w-none';
        
        const lines = content.split('\n');
        let currentSection = null;
        
        lines.forEach(line => {
            line = line.trim();
            if (!line) return;
            
            if (line.startsWith('## ')) {
                if (currentSection) {
                    contentDiv.appendChild(currentSection);
                }
                currentSection = document.createElement('div');
                currentSection.className = 'mb-6 p-4 bg-gray-50 rounded-lg';
                
                const header = document.createElement('h2');
                header.className = 'text-xl font-bold mb-3 text-gray-800';
                header.textContent = line.replace('## ', '');
                currentSection.appendChild(header);
            }
            // Handle time sections (Morning/Afternoon/Evening)
            else if (line.match(/^(Morning|Afternoon|Evening)\s*\(/i)) {
                const timeDiv = document.createElement('div');
                timeDiv.className = 'mt-4 mb-3';
                
                const timeHeader = document.createElement('h4');
                timeHeader.className = 'font-semibold text-gray-800 mb-1';
                
                // Extract time range from parentheses
                const timeMatch = line.match(/(.*?)\s*\(([^)]+)\)/);
                if (timeMatch) {
                    timeHeader.textContent = timeMatch[1].trim();
                    
                    const timeRange = document.createElement('span');
                    timeRange.className = 'text-sm font-normal text-gray-600 ml-2';
                    timeRange.textContent = timeMatch[2].trim();
                    timeHeader.appendChild(timeRange);
                } else {
                    timeHeader.textContent = line;
                }
                
                timeDiv.appendChild(timeHeader);
                
                if (currentSection) {
                    currentSection.appendChild(timeDiv);
                } else {
                    contentDiv.appendChild(timeDiv);
                }
            }
            // Handle regular paragraphs
            else {
                const p = document.createElement('p');
                p.className = 'mb-3 text-gray-700';
                p.textContent = line;
                
                if (currentSection) {
                    currentSection.appendChild(p);
                } else {
                    contentDiv.appendChild(p);
                }
            }
        });
        
        if (currentSection) {
            contentDiv.appendChild(currentSection);
        }
        
        itineraryDiv.appendChild(contentDiv);
        
        if (resultsDiv) {
            resultsDiv.scrollIntoView({ behavior: 'smooth' });
        }
    }
});