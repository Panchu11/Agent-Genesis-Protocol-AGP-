// Configuration for trait sliders
const TRAITS = [
    'Creativity',
    'Empathy', 
    'Curiosity',
    'Ambition',
    'Patience',
    'Humor',
    'Intelligence',
    'Risk-Tolerance',
    'Loyalty',
    'Assertiveness'
];

// Initialize the builder UI
document.addEventListener('DOMContentLoaded', function() {
    // Create trait sliders
    const slidersContainer = document.querySelector('.trait-sliders');
    
    TRAITS.forEach(trait => {
        const sliderGroup = document.createElement('div');
        sliderGroup.className = 'trait-slider';
        
        sliderGroup.innerHTML = `
            <div class="slider-container">
                <span class="slider-label">${trait}</span>
                <input type="range" min="0" max="100" value="50" class="trait-slider" 
                       id="trait-${trait.toLowerCase()}" data-trait="${trait}">
                <span class="slider-value">50</span>
            </div>
        `;
        
        slidersContainer.appendChild(sliderGroup);
    });

    // Set up event listeners for real-time preview
    setupPreviewUpdates();
    
    // Set up create agent button
    document.getElementById('create-agent-btn').addEventListener('click', createAgent);
});

function setupPreviewUpdates() {
    // Update preview when inputs change
    document.querySelectorAll('input').forEach(input => {
        input.addEventListener('input', updatePreview);
    });
    
    // Initial preview update
    updatePreview();
}

function updatePreview() {
    const previewContainer = document.getElementById('agent-preview');
    const name = document.getElementById('agent-name').value || 'New Agent';
    const role = document.getElementById('agent-role').value || 'General Purpose';
    
    // Get all trait values
    const traits = {};
    TRAITS.forEach(trait => {
        const slider = document.getElementById(`trait-${trait.toLowerCase()}`);
        traits[trait] = slider.value;
        // Update displayed value
        slider.nextElementSibling.textContent = slider.value;
    });
    
    // Generate preview HTML
    let previewHTML = `
        <div class="preview-item">
            <div class="preview-label">Name</div>
            <div class="preview-value">${name}</div>
        </div>
        <div class="preview-item">
            <div class="preview-label">Role</div>
            <div class="preview-value">${role}</div>
        </div>
        <div class="preview-item">
            <div class="preview-label">Key Traits</div>
    `;
    
    // Add top 3 traits by value
    const sortedTraits = Object.entries(traits)
        .sort((a, b) => b[1] - a[1])
        .slice(0, 3);
        
    sortedTraits.forEach(([trait, value]) => {
        previewHTML += `
            <div class="preview-value">
                ${trait}: ${value}%
            </div>
        `;
    });
    
    previewHTML += `</div>`;
    previewContainer.innerHTML = previewHTML;
}

function createAgent() {
    const name = document.getElementById('agent-name').value;
    const role = document.getElementById('agent-role').value;
    const deploy = document.getElementById('deploy-checkbox').checked;
    const sandbox = document.getElementById('sandbox-checkbox').checked;
    
    if (!name) {
        alert('Please enter an agent name');
        return;
    }
    
    // Collect all trait values
    const traits = {};
    TRAITS.forEach(trait => {
        traits[trait] = parseInt(
            document.getElementById(`trait-${trait.toLowerCase()}`).value
        );
    });
    
    // Prepare agent data
    const agentData = {
        name: name,
        role: role,
        traits: traits,
        deploy: deploy,
        sandbox: sandbox
    };
    
    // Send to backend
    fetch('/create-agent', {
        method: 'POST',
        headers: {
            'Content-Type': 'application/json',
        },
        body: JSON.stringify(agentData)
    })
    .then(response => response.json())
    .then(data => {
        if (data.error) {
            alert(`Error: ${data.error}`);
        } else {
            alert(`Agent ${name} created successfully!`);
            // Reset form
            document.getElementById('agent-name').value = '';
            document.getElementById('agent-role').value = '';
            document.querySelectorAll('.trait-slider').forEach(slider => {
                slider.value = 50;
            });
            updatePreview();
        }
    })
    .catch(error => {
        console.error('Error:', error);
        alert('Failed to create agent');
    });
}
