// Certificate Conversion Handlers
document.getElementById('jksToPemForm').addEventListener('submit', async function(e) {
    e.preventDefault();
    const form = e.target;
    const submitBtn = form.querySelector('button[type="submit"]');
    const originalText = submitBtn.textContent;
    
    submitBtn.disabled = true;
    submitBtn.textContent = 'Converting...';
    
    try {
        const formData = new FormData(form);
        const response = await fetch('/convert/jks-to-pem', {
            method: 'POST',
            body: formData
        });
        
        if (!response.ok) {
            const error = await response.json();
            throw new Error(error.error || 'Conversion failed');
        }
        
        const blob = await response.blob();
        const url = window.URL.createObjectURL(blob);
        const a = document.createElement('a');
        a.href = url;
        a.download = 'converted.zip';
        document.body.appendChild(a);
        a.click();
        window.URL.revokeObjectURL(url);
    } catch (error) {
        alert(error.message);
        console.error('Conversion error:', error);
    } finally {
        submitBtn.disabled = false;
        submitBtn.textContent = originalText;
    }
});

document.getElementById('pemToJksForm').addEventListener('submit', async function(e) {
    e.preventDefault();
    const form = e.target;
    const submitBtn = form.querySelector('button[type="submit"]');
    const originalText = submitBtn.textContent;
    
    submitBtn.disabled = true;
    submitBtn.textContent = 'Converting...';
    
    try {
        const formData = new FormData(form);
        const response = await fetch('/convert/pem-to-jks', {
            method: 'POST',
            body: formData
        });
        
        if (!response.ok) {
            const error = await response.json();
            throw new Error(error.error || 'Conversion failed');
        }
        
        const blob = await response.blob();
        const url = window.URL.createObjectURL(blob);
        const a = document.createElement('a');
        a.href = url;
        a.download = 'keystore.jks';
        document.body.appendChild(a);
        a.click();
        window.URL.revokeObjectURL(url);
    } catch (error) {
        alert(error.message);
        console.error('Conversion error:', error);
    } finally {
        submitBtn.disabled = false;
        submitBtn.textContent = originalText;
    }
});

// Base64 Utilities
document.getElementById('base64EncodeForm').addEventListener('submit', async function(e) {
    e.preventDefault();
    const form = e.target;
    const submitBtn = form.querySelector('button[type="submit"]');
    const resultDiv = document.getElementById('base64Result');
    const outputTextarea = document.getElementById('base64Output');
    
    submitBtn.disabled = true;
    submitBtn.textContent = 'Encoding...';
    
    try {
        const formData = new FormData(form);
        const response = await fetch('/base64/encode', {
            method: 'POST',
            body: formData
        });
        
        if (!response.ok) {
            const error = await response.json();
            throw new Error(error.error || 'Encoding failed');
        }
        
        const data = await response.json();
        outputTextarea.value = data.base64;
        resultDiv.style.display = 'block';
    } catch (error) {
        alert(error.message);
        console.error('Encoding error:', error);
    } finally {
        submitBtn.disabled = false;
        submitBtn.textContent = 'Encode to Base64';
    }
});

document.getElementById('base64DecodeForm').addEventListener('submit', async function(e) {
    e.preventDefault();
    const form = e.target;
    const submitBtn = form.querySelector('button[type="submit"]');
    const filenameInput = document.getElementById('decodeFilename');
    const base64Input = document.getElementById('base64Data');
    
    submitBtn.disabled = true;
    submitBtn.textContent = 'Decoding...';
    
    try {
        const response = await fetch('/base64/decode', {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json',
            },
            body: JSON.stringify({
                filename: filenameInput.value,
                base64: base64Input.value
            })
        });
        
        if (!response.ok) {
            const error = await response.json();
            throw new Error(error.error || 'Decoding failed');
        }
        
        const blob = await response.blob();
        const url = window.URL.createObjectURL(blob);
        const a = document.createElement('a');
        a.href = url;
        a.download = filenameInput.value;
        document.body.appendChild(a);
        a.click();
        window.URL.revokeObjectURL(url);
    } catch (error) {
        alert(error.message);
        console.error('Decoding error:', error);
    } finally {
        submitBtn.disabled = false;
        submitBtn.textContent = 'Decode and Download';
    }
});

// Vault Utilities
document.getElementById('vaultJksForm').addEventListener('submit', async function(e) {
    e.preventDefault();
    const form = e.target;
    const submitBtn = form.querySelector('button[type="submit"]');
    const resultDiv = document.getElementById('vaultJksResult');
    const outputPre = document.getElementById('vaultJksOutput');
    const pathSpan = document.getElementById('vaultJksPath');
    
    submitBtn.disabled = true;
    submitBtn.textContent = 'Processing...';
    
    try {
        const formData = new FormData(form);
        const response = await fetch('/vault/encode-jks', {
            method: 'POST',
            body: formData
        });
        
        if (!response.ok) {
            const error = await response.json();
            throw new Error(error.error || 'Processing failed');
        }
        
        const data = await response.json();
        outputPre.textContent = JSON.stringify(data.payload, null, 2);
        pathSpan.textContent = data.vault_path_suggestion;
        resultDiv.style.display = 'block';
    } catch (error) {
        alert(error.message);
        console.error('Vault JKS error:', error);
    } finally {
        submitBtn.disabled = false;
        submitBtn.textContent = 'Generate Vault Payload';
    }
});

document.getElementById('vaultPemForm').addEventListener('submit', async function(e) {
    e.preventDefault();
    const form = e.target;
    const submitBtn = form.querySelector('button[type="submit"]');
    const resultDiv = document.getElementById('vaultPemResult');
    const outputPre = document.getElementById('vaultPemOutput');
    const pathSpan = document.getElementById('vaultPemPath');
    
    submitBtn.disabled = true;
    submitBtn.textContent = 'Processing...';
    
    try {
        const formData = new FormData(form);
        const response = await fetch('/vault/encode-pem', {
            method: 'POST',
            body: formData
        });
        
        if (!response.ok) {
            const error = await response.json();
            throw new Error(error.error || 'Processing failed');
        }
        
        const data = await response.json();
        outputPre.textContent = JSON.stringify(data.payload, null, 2);
        pathSpan.textContent = data.vault_path_suggestion;
        resultDiv.style.display = 'block';
    } catch (error) {
        alert(error.message);
        console.error('Vault PEM error:', error);
    } finally {
        submitBtn.disabled = false;
        submitBtn.textContent = 'Generate Vault Payload';
    }
});

// Helper Functions
function copyToClipboard(text) {
    navigator.clipboard.writeText(text).then(() => {
        alert('Copied to clipboard!');
    }).catch(err => {
        console.error('Failed to copy: ', err);
        alert('Failed to copy to clipboard');
    });
}

// Attach copy handlers
document.getElementById('copyBase64Btn')?.addEventListener('click', function() {
    const text = document.getElementById('base64Output').value;
    copyToClipboard(text);
});

document.getElementById('copyVaultJksBtn')?.addEventListener('click', function() {
    const text = document.getElementById('vaultJksOutput').textContent;
    copyToClipboard(text);
});

document.getElementById('copyVaultPemBtn')?.addEventListener('click', function() {
    const text = document.getElementById('vaultPemOutput').textContent;
    copyToClipboard(text);
});