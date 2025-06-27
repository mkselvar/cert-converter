// Base64 Encoding
document.getElementById('base64EncodeForm').addEventListener('submit', function(e) {
    e.preventDefault();
    const formData = new FormData(this);
    
    fetch('/api/base64/encode', {
        method: 'POST',
        body: formData
    })
    .then(response => response.json())
    .then(data => {
        if (data.error) throw new Error(data.error);
        document.getElementById('base64Output').value = data.base64;
        document.getElementById('base64Result').style.display = 'block';
    })
    .catch(error => alert(error.message));
});

// Other utility form handlers...