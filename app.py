import os
import subprocess
import tempfile
import uuid
import logging
from io import BytesIO
import zipfile
from flask import Flask, render_template, request, send_file
from werkzeug.middleware.proxy_fix import ProxyFix
DEFAULT_JKS_PASS = os.getenv('DEFAULT_JKS_PASS', '')

# Initialize Flask app
app = Flask(__name__)
app.config['MAX_CONTENT_LENGTH'] = 5 * 1024 * 1024  # 5MB limit
app.wsgi_app = ProxyFix(app.wsgi_app, x_for=1, x_proto=1, x_host=1, x_prefix=1)
app.config['PROPAGATE_EXCEPTIONS'] = False

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler('app.log'),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger(__name__)

def cleanup_temp(temp_dir):
    """Safely remove temporary directory and contents"""
    try:
        if os.path.exists(temp_dir):
            for root, dirs, files in os.walk(temp_dir, topdown=False):
                for name in files:
                    os.remove(os.path.join(root, name))
                for name in dirs:
                    os.rmdir(os.path.join(root, name))
            os.rmdir(temp_dir)
    except Exception as e:
        logger.error("Error cleaning up temp directory: [REDACTED]")

def secure_log_command(cmd):
    """Redact sensitive information from commands before logging"""
    return cmd.split(' -srcstorepass ')[0].split(' -deststorepass ')[0].split(' -password pass:')[0]

def run_secure_command(cmd, operation_name):
    """Execute command with secure logging"""
    logger.info(f"Executing: {secure_log_command(cmd)}")
    result = subprocess.run(cmd, shell=True, capture_output=True, text=True)
    if result.returncode != 0:
        logger.error(f"Command failed during {operation_name}. Exit code: {result.returncode}")
        logger.error(f"Command error output: {result.stderr}")
        raise Exception(f"Operation failed during {operation_name}")
    return result

def validate_jks_file(file_path, password=None):
    """Validate JKS file integrity"""
    try:
        cmd = f"keytool -list -keystore {file_path}"
        if password:
            cmd += f" -storepass {password}"
        result = subprocess.run(cmd, shell=True, capture_output=True, text=True, timeout=10)
        return result.returncode == 0
    except subprocess.SubprocessError:
        return False

@app.route('/')
def index():
    return render_template('index.html')

@app.route('/convert', methods=['POST'])
def convert():
    conversion_type = request.form.get('conversion_type')
    temp_dir = tempfile.mkdtemp()
    prefix = str(uuid.uuid4())
    
    try:
        if conversion_type == 'jks-to-pem':
            return handle_jks_to_pem(request, temp_dir, prefix)
        elif conversion_type == 'pem-to-jks':
            return handle_pem_to_jks(request, temp_dir, prefix)
        else:
            raise ValueError("Invalid conversion type specified")
    except Exception as e:
        logger.error(f"Conversion error: {str(e)}", exc_info=False)
        return render_template('error.html', error_message="Conversion failed. Please check your inputs."), 400
    finally:
        cleanup_temp(temp_dir)

def handle_jks_to_pem(request, temp_dir, prefix):
    jks_file = request.files['jks_file']
    jks_path = os.path.join(temp_dir, f"{prefix}.jks")
    jks_file.save(jks_path)
    
    alias = request.form['alias']
    jks_pass = request.form['jks_password']
    p12_pass = jks_pass
    
    # Validate JKS file before processing
    if not validate_jks_file(jks_path, jks_pass):
        raise ValueError("Invalid JKS file or password")
    
    p12_path = os.path.join(temp_dir, f"{prefix}.p12")
    key_path = os.path.join(temp_dir, f"{prefix}.key")
    pem_path = os.path.join(temp_dir, f"{prefix}.pem")
    
    commands = [
        f"keytool -importkeystore -srckeystore {jks_path} -destkeystore {p12_path} "
        f"-deststoretype PKCS12 -srcalias {alias} -srcstorepass {jks_pass} "
        f"-deststorepass {p12_pass}",
        
        f"openssl pkcs12 -in {p12_path} -nocerts -nodes "
        f"-out {key_path} -password pass:{p12_pass}",
        
        f"openssl pkcs12 -in {p12_path} -clcerts -nokeys "
        f"-out {pem_path} -password pass:{p12_pass}"
    ]
    
    for cmd in commands:
        run_secure_command(cmd, "JKS to PEM conversion")
    
    # Create in-memory zip file
    zip_buffer = BytesIO()
    with zipfile.ZipFile(zip_buffer, 'w', zipfile.ZIP_DEFLATED) as zip_file:
        zip_file.write(key_path, 'private.key')
        zip_file.write(pem_path, 'certificate.pem')
    
    zip_buffer.seek(0)
    return send_file(
        zip_buffer,
        as_attachment=True,
        download_name='converted_files.zip',
        mimetype='application/zip'
    )

def handle_pem_to_jks(request, temp_dir, prefix):
    pem_file = request.files['pem_file']
    key_file = request.files['key_file']
    pem_path = os.path.join(temp_dir, f"{prefix}.pem")
    key_path = os.path.join(temp_dir, f"{prefix}.key")
    pem_file.save(pem_path)
    key_file.save(key_path)
    
    alias = request.form['alias']
    jks_pass = request.form['jks_password']
    jks_path = os.path.join(temp_dir, f"{prefix}.jks")
    p12_path = os.path.join(temp_dir, f"{prefix}.p12")
    
    commands = [
        f"openssl pkcs12 -export -in {pem_path} -inkey {key_path} "
        f"-out {p12_path} -name {alias} -password pass:{jks_pass}",
        
        f"keytool -importkeystore -srckeystore {p12_path} "
        f"-srcstoretype PKCS12 -destkeystore {jks_path} -deststoretype JKS "
        f"-srcstorepass {jks_pass} -deststorepass {jks_pass}"
    ]
    
    for cmd in commands:
        run_secure_command(cmd, "PEM to JKS conversion")
    
    return send_file(jks_path, as_attachment=True, download_name='keystore.jks')

@app.errorhandler(404)
def not_found(e):
    return render_template('404.html'), 404

@app.errorhandler(500)
def server_error(e):
    logger.error("Internal server error occurred")
    return render_template('500.html'), 500

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=5000, debug=False)
