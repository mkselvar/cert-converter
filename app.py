import os
import subprocess
import tempfile
import uuid
import logging
import base64
from io import BytesIO
import zipfile
from flask import Flask, render_template, request, send_file, jsonify
from werkzeug.middleware.proxy_fix import ProxyFix

app = Flask(__name__)
app.config['MAX_CONTENT_LENGTH'] = 10 * 1024 * 1024  # 10MB limit
app.wsgi_app = ProxyFix(app.wsgi_app, x_for=1, x_proto=1, x_host=1, x_prefix=1)

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
        logger.error(f"Error cleaning up temp dir: {str(e)}")

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

# Certificate Conversion Endpoints
@app.route('/convert/jks-to-pem', methods=['POST'])
def convert_jks_to_pem():
    temp_dir = tempfile.mkdtemp()
    try:
        if 'jks_file' not in request.files:
            return jsonify({"error": "No JKS file provided"}), 400
        
        jks_file = request.files['jks_file']
        alias = request.form.get('alias', '1')
        password = request.form.get('password', '')
        
        jks_path = os.path.join(temp_dir, "temp.jks")
        jks_file.save(jks_path)
        
        if not validate_jks_file(jks_path, password):
            return jsonify({"error": "Invalid JKS file or password"}), 400
        
        p12_path = os.path.join(temp_dir, "temp.p12")
        key_path = os.path.join(temp_dir, "private.key")
        pem_path = os.path.join(temp_dir, "certificate.pem")
        
        # Convert JKS to PKCS12
        subprocess.run(
            f"keytool -importkeystore -srckeystore {jks_path} -destkeystore {p12_path} "
            f"-deststoretype PKCS12 -srcalias {alias} -srcstorepass {password} "
            f"-deststorepass {password}",
            shell=True, check=True
        )
        
        # Extract private key
        subprocess.run(
            f"openssl pkcs12 -in {p12_path} -nocerts -nodes "
            f"-out {key_path} -password pass:{password}",
            shell=True, check=True
        )
        
        # Extract certificate
        subprocess.run(
            f"openssl pkcs12 -in {p12_path} -clcerts -nokeys "
            f"-out {pem_path} -password pass:{password}",
            shell=True, check=True
        )
        
        # Create zip file
        zip_buffer = BytesIO()
        with zipfile.ZipFile(zip_buffer, 'w', zipfile.ZIP_DEFLATED) as zip_file:
            zip_file.write(key_path, 'private.key')
            zip_file.write(pem_path, 'certificate.pem')
        
        zip_buffer.seek(0)
        return send_file(
            zip_buffer,
            as_attachment=True,
            download_name='converted.zip',
            mimetype='application/zip'
        )
        
    except subprocess.CalledProcessError as e:
        logger.error(f"Conversion error: {str(e)}")
        return jsonify({"error": "Conversion failed"}), 500
    except Exception as e:
        logger.error(f"Unexpected error: {str(e)}")
        return jsonify({"error": "Internal server error"}), 500
    finally:
        cleanup_temp(temp_dir)

@app.route('/convert/pem-to-jks', methods=['POST'])
def convert_pem_to_jks():
    temp_dir = tempfile.mkdtemp()
    try:
        if 'cert_file' not in request.files or 'key_file' not in request.files:
            return jsonify({"error": "Certificate and key files required"}), 400
        
        cert_file = request.files['cert_file']
        key_file = request.files['key_file']
        alias = request.form.get('alias', '1')
        password = request.form.get('password', 'changeit')
        
        cert_path = os.path.join(temp_dir, "cert.pem")
        key_path = os.path.join(temp_dir, "key.pem")
        p12_path = os.path.join(temp_dir, "temp.p12")
        jks_path = os.path.join(temp_dir, "keystore.jks")
        
        cert_file.save(cert_path)
        key_file.save(key_path)
        
        # Create PKCS12
        subprocess.run(
            f"openssl pkcs12 -export -in {cert_path} -inkey {key_path} "
            f"-out {p12_path} -name {alias} -password pass:{password}",
            shell=True, check=True
        )
        
        # Convert to JKS
        subprocess.run(
            f"keytool -importkeystore -srckeystore {p12_path} "
            f"-srcstoretype PKCS12 -destkeystore {jks_path} -deststoretype JKS "
            f"-srcstorepass {password} -deststorepass {password}",
            shell=True, check=True
        )
        
        return send_file(
            jks_path,
            as_attachment=True,
            download_name='keystore.jks',
            mimetype='application/octet-stream'
        )
        
    except subprocess.CalledProcessError as e:
        logger.error(f"Conversion error: {str(e)}")
        return jsonify({"error": "Conversion failed"}), 500
    except Exception as e:
        logger.error(f"Unexpected error: {str(e)}")
        return jsonify({"error": "Internal server error"}), 500
    finally:
        cleanup_temp(temp_dir)

# Base64 Utilities
@app.route('/base64/encode', methods=['POST'])
def base64_encode():
    try:
        if 'file' not in request.files:
            return jsonify({"error": "No file provided"}), 400
        
        file = request.files['file']
        if file.filename == '':
            return jsonify({"error": "No selected file"}), 400
        
        file_content = file.read()
        encoded = base64.b64encode(file_content).decode('utf-8')
        
        return jsonify({
            "filename": file.filename,
            "base64": encoded,
            "type": "base64"
        })
    except Exception as e:
        logger.error(f"Base64 encode error: {str(e)}")
        return jsonify({"error": str(e)}), 500

@app.route('/base64/decode', methods=['POST'])
def base64_decode():
    try:
        if not request.is_json:
            return jsonify({"error": "Request must be JSON"}), 400
        
        data = request.get_json()
        if 'base64' not in data or 'filename' not in data:
            return jsonify({"error": "Missing base64 data or filename"}), 400
        
        decoded = base64.b64decode(data['base64'])
        return send_file(
            BytesIO(decoded),
            as_attachment=True,
            download_name=data['filename'],
            mimetype='application/octet-stream'
        )
    except Exception as e:
        logger.error(f"Base64 decode error: {str(e)}")
        return jsonify({"error": str(e)}), 500

# Vault Utilities
@app.route('/vault/encode-jks', methods=['POST'])
def vault_encode_jks():
    temp_dir = tempfile.mkdtemp()
    try:
        if 'file' not in request.files:
            return jsonify({"error": "No file provided"}), 400
        
        jks_file = request.files['file']
        password = request.form.get('password', '')
        
        jks_path = os.path.join(temp_dir, "temp.jks")
        jks_file.save(jks_path)
        
        if not validate_jks_file(jks_path, password):
            return jsonify({"error": "Invalid JKS file or password"}), 400
        
        with open(jks_path, 'rb') as f:
            jks_content = f.read()
        
        encoded = base64.b64encode(jks_content).decode('utf-8')
        
        return jsonify({
            "filename": jks_file.filename,
            "base64": encoded,
            "type": "jks",
            "vault_path_suggestion": f"secret/jks/{os.path.splitext(jks_file.filename)[0]}",
            "payload": {
                "data": {
                    "content": encoded,
                    "password": password
                }
            }
        })
    except Exception as e:
        logger.error(f"Vault JKS encode error: {str(e)}")
        return jsonify({"error": str(e)}), 500
    finally:
        cleanup_temp(temp_dir)

@app.route('/vault/encode-pem', methods=['POST'])
def vault_encode_pem():
    try:
        if 'file' not in request.files:
            return jsonify({"error": "No file provided"}), 400
        
        pem_file = request.files['file']
        pem_content = pem_file.read()
        encoded = base64.b64encode(pem_content).decode('utf-8')
        
        return jsonify({
            "filename": pem_file.filename,
            "base64": encoded,
            "type": "pem",
            "vault_path_suggestion": f"secret/certs/{os.path.splitext(pem_file.filename)[0]}",
            "payload": {
                "data": {
                    "content": encoded
                }
            }
        })
    except Exception as e:
        logger.error(f"Vault PEM encode error: {str(e)}")
        return jsonify({"error": str(e)}), 500

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=5000, debug=False)