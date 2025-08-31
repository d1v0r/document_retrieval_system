// Simple Markdown to plain text converter
function markdownToHtml(markdown) {
    // Remove markdown formatting
    let text = markdown
        .replace(/\*\*([^*]+)\*\*/g, '$1')  // Remove bold
        .replace(/\*([^*]+)\*/g, '$1')       // Remove italic
        .replace(/`([^`]+)`/g, '$1')          // Remove code
        .replace(/\[([^\]]+)\]\([^)]+\)/g, '$1')  // Remove links
        .replace(/^#+\s*/gm, '')              // Remove headers
        .replace(/\n{3,}/g, '\n\n')          // Normalize newlines
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
    if (!form) return;

    form.addEventListener('submit', async (e) => {
        e.preventDefault();
        
        const button = form.querySelector('button[type="submit"]');
        const buttonText = button.innerHTML;
        const resultsDiv = document.getElementById('results');
        
        // Show loading state
        button.disabled = true;
        button.innerHTML = `
            <svg class="animate-spin -ml-1 mr-2 h-5 w-5 text-white inline" xmlns="http://www.w3.org/2000/svg" fill="none" viewBox="0 0 24 24">
                <circle class="opacity-25" cx="12" cy="12" r="10" stroke="currentColor" stroke-width="4"></circle>
                <path class="opacity-75" fill="currentColor" d="M4 12a8 8 0 018-8V0C5.373 0 0 5.373 0 12h4zm2 5.291A7.962 7.962 0 014 12H0c0 3.042 1.135 5.824 3 7.938l3-2.647z"></path>
            </svg>
            Planning your trip...
        `;
        
        if (resultsDiv) resultsDiv.innerHTML = '';
        
        try {
            if (resultsDiv) {
                resultsDiv.classList.remove('hidden');
                resultsDiv.innerHTML = `
                    <div class="mt-8 p-6 bg-white rounded-lg shadow-md text-center">
                        <div class="flex flex-col items-center justify-center py-8">
                            <div class="animate-spin rounded-full h-12 w-12 border-t-2 border-b-2 border-blue-500 mb-4"></div>
                            <h3 class="text-lg font-medium text-gray-900 mb-2">Crafting your perfect itinerary</h3>
                            <p class="text-gray-500">This may take a moment as we gather the best recommendations for you...</p>
                        </div>
                    </div>
                `;
            }
            
            const response = await fetch('/api/generate-itinerary', {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json',
                },
                body: JSON.stringify({
                    city: form.city.value,
                    days: parseInt(form.days.value),
                    preferences: form.preferences.value
                })
            });
            
            if (!response.ok) {
                const error = await response.json();
                throw new Error(error.detail || 'Failed to generate itinerary');
            }
            
            const data = await response.json();
            
            if (data.status !== 'success') {
                throw new Error('Failed to generate itinerary');
            }
            
            // Get the response and convert markdown to HTML
            let formattedItinerary = markdownToHtml(data.data.answer);
            
            // Simple formatting for day sections
            let daySections = [];
            const dayRegex = /(?:<h[12]>\s*)?(?:Day\s+\d+)(?:\s*<\/h[12]>)?([\s\S]*?)(?=<h[12]>\s*Day\s+\d+\s*<\/h[12]>|$)/gi;
            let match;
            
            // Extract each day's content
            const dayContent = formattedItinerary;
            while ((match = dayRegex.exec(dayContent)) !== null) {
                const content = match[1].trim();
                if (content) {
                    daySections.push(content);
                }
            }
            
            let finalItinerary = '';
            
            if (daySections.length > 0) {
                finalItinerary = daySections.map((dayContent, index) => {
                    const activities = [];
                    let currentActivity = null;
                    
                    const lines = dayContent.split('\n').filter(line => line.trim());
                    
                    lines.forEach(line => {
                        line = line.trim();
                        const timeMatch = line.match(/\*\s*\*\*(.*?):\*\*/);
                        if (timeMatch) {
                            if (currentActivity) {
                                activities.push(currentActivity);
                            }
                            currentActivity = {
                                time: timeMatch[1].trim(),
                                description: line.replace(/\*\*.*?\*\*/, '').replace(/^[\s*:]+/, '').trim()
                            };
                        } else if (currentActivity) {
                            if (line.startsWith('+')) {
                                currentActivity.description += '<br>• ' + line.replace(/^[\s+]+/, '');
                            } else {
                                currentActivity.description += ' ' + line;
                            }
                        } else if (line) {
                            activities.push({
                                time: '',
                                description: line.replace(/\*\*/g, '')
                            });
                        }
                    });
                    
                    if (currentActivity) {
                        activities.push(currentActivity);
                    }
                    
                    if (activities.length === 0) return '';
                    
                    let dayHtml = `
                        <div class="mb-10">
                            <h3 class="text-xl font-bold text-gray-900 mb-4">Day ${index + 1}</h3>
                            <div class="space-y-6">
                    `;
                    
                    activities.forEach(activity => {
                        let timeText = '';
                        if (activity.time) {
                            const timeRangeMatch = activity.time.match(/(\d{1,2}:\d{2}\s*[AP]M)\s*-\s*(\d{1,2}:\d{2}\s*[AP]M)/i);
                            if (timeRangeMatch) {
                                timeText = `From ${timeRangeMatch[1].trim()} to ${timeRangeMatch[2].trim()}`;
                            } else {
                                timeText = activity.time;
                            }
                        }
                        
                        let description = activity.description
                            .replace(/\*\*/g, '')
                            .replace(/\s+/g, ' ')
                            .trim();
                        
                        dayHtml += `
                            <div class="mb-6">
                                <div class="text-blue-700 font-medium mb-2">${timeText}</div>
                                <div class="text-gray-800 pl-4">
                                    ${description}
                                </div>
                            </div>
                        `;
                    });
                    
                    dayHtml += `
                            </div>
                        </div>
                        ${index < daySections.length - 1 ? '<hr class="my-8 border-gray-200">' : ''}
                    `;
                });
                
                if (window.marked && typeof finalItinerary === 'string') {
                    finalItinerary = window.marked.parse(finalItinerary);
                }
            }
            
            if (resultsDiv) {
                resultsDiv.classList.remove('hidden');

                const printContent = document.createElement('div');
                printContent.style.display = 'none';
                printContent.innerHTML = `
                    <div style="font-family: Arial, sans-serif; padding: 20px;">
                        <h1 style="font-size: 1.5em; font-weight: bold; margin-bottom: 1em; text-align: center;">
                            Your ${data.data.days}-Day Itinerary for ${data.data.destination}
                        </h1>
                        <div style="white-space: pre-line; line-height: 1.6;">
                            ${typeof finalItinerary === 'string' ? finalItinerary : (formattedItinerary || 'No itinerary content available')}
                        </div>
                    </div>
                `;
                document.body.appendChild(printContent);
                
                resultsDiv.innerHTML = `
                    <div style="white-space: pre-line; font-family: monospace; line-height: 1.5; margin-bottom: 20px;">
                        ${typeof finalItinerary === 'string' ? finalItinerary : (formattedItinerary || 'No itinerary content available')}
                    </div>
                    <div style="display: flex; gap: 10px; margin-top: 1em;">
                        <button onclick="window.print()" style="flex: 1; padding: 10px; background: #3b82f6; color: white; border: none; border-radius: 4px; cursor: pointer;">
                            Print Itinerary
                        </button>
                        <button onclick="window.location.reload()" style="flex: 1; padding: 10px; background: #4b5563; color: white; border: none; border-radius: 4px; cursor: pointer;">
                            Plan Another Trip
                        </button>
                    </div>
                `;
                
                const originalPrint = window.print;
                window.print = function() {
                    document.body.innerHTML = printContent.innerHTML;
                    originalPrint();
                    window.location.reload();
                };
                
                window.onafterprint = function() {
                    window.location.reload();
                };
                
                resultsDiv.scrollIntoView({ behavior: 'smooth' });
            }
            
        } catch (error) {
            console.error('Error:', error);
            if (resultsDiv) {
                resultsDiv.innerHTML = `
                    <div class="mt-8 bg-red-50 border-l-4 border-red-400 p-4 rounded-lg">
                        <div class="flex">
                            <div class="flex-shrink-0">
                                <svg class="h-5 w-5 text-red-400" xmlns="http://www.w3.org/2000/svg" viewBox="0 0 20 20" fill="currentColor">
                                    <path fill-rule="evenodd" d="M10 18a8 8 0 100-16 8 8 0 000 16zM8.707 7.293a1 1 0 00-1.414 1.414L8.586 10l-1.293 1.293a1 1 0 101.414 1.414L10 11.414l1.293 1.293a1 1 0 001.414-1.414L11.414 10l1.293-1.293a1 1 0 00-1.414-1.414L10 8.586 8.707 7.293z" clip-rule="evenodd" />
                                </svg>
                            </div>
                            <div class="ml-3">
                                <p class="text-sm text-red-700">
                                    Error: ${error.message || 'Failed to generate itinerary. Please try again.'}
                                </p>
                            </div>
                        </div>
                    </div>
                `;
            }
        } finally {
            button.disabled = false;
            button.innerHTML = buttonText;
        }
    });
});