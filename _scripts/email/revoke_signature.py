import os
import yaml
from github import Github
import hashlib
import base64
import boto3
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart

# Load config once when Lambda container starts
with open('config.yml', 'r') as f:
    CONFIG = yaml.safe_load(f)

def sanitize_filename(email_addr):
    """Convert email address to valid filename"""
    return email_addr.lower().replace('@', '-').replace('.', '-')

def generate_revocation_token(email_addr):
    """Generate a unique token for signature revocation"""
    secret = os.environ['REVOCATION_SECRET']
    message = f"{email_addr}:{secret}".encode()
    return base64.urlsafe_b64encode(hashlib.sha256(message).digest()).decode()

def get_template(template_name):
    """Get email template from local files"""
    template_path = f"templates/{template_name}.txt"
    try:
        with open(template_path, 'r') as f:
            return f.read()
    except Exception as e:
        print(f"Error reading template {template_name}: {str(e)}")
        return None

def send_revocation_confirmation(ses_client, email_addr):
    """Send revocation confirmation email"""
    template = get_template('revocation_email')
    if not template:
        raise Exception("Could not load revocation template")

    msg = MIMEMultipart()
    msg['Subject'] = CONFIG['email']['subjects']['revocation']
    msg['From'] = CONFIG['email']['from']
    msg['To'] = email_addr
    
    body = template.format(
        email=email_addr,
        sign_address=CONFIG['email']['sign_address']
    )
    
    msg.attach(MIMEText(body, 'plain'))

    try:
        ses_client.send_raw_email(
            Source=CONFIG['email']['from'],
            Destinations=[email_addr],
            RawMessage={'Data': msg.as_string()}
        )
        return True
    except Exception as e:
        print(f"Error sending revocation confirmation: {str(e)}")
        return False

def revoke_signature(event, context):
    token = event['queryStringParameters'].get('token')
    email = event['queryStringParameters'].get('email')
    
    if not token or not email:
        return {
            'statusCode': 400,
            'body': 'Missing token or email'
        }
    
    # Verify token
    expected_token = generate_revocation_token(email)
    if token != expected_token:
        return {
            'statusCode': 403,
            'body': 'Invalid revocation token'
        }
    
    try:
        g = Github(os.environ['GITHUB_TOKEN'])
        repo = g.get_repo(os.environ['GITHUB_REPO'])
        ses = boto3.client('ses')
        
        file_path = f"{CONFIG['paths']['signatures']}/{sanitize_filename(email)}.yaml"
        file = repo.get_contents(file_path)
        
        repo.delete_file(
            path=file_path,
            message=f"Revoke signature for {email}",
            sha=file.sha,
            branch="main"
        )
        
        # Send confirmation email
        send_revocation_confirmation(ses, email)
        
        return {
            'statusCode': 200,
            'body': 'Signature successfully revoked'
        }
    except Exception as e:
        return {
            'statusCode': 500,
            'body': f'Error revoking signature: {str(e)}'
        }
