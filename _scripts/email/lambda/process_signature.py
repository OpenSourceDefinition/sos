import boto3
import email
import os
import yaml
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from bs4 import BeautifulSoup
import re
from github import Github
import hashlib
import base64
import json
from datetime import datetime
import requests
from config import config

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

def log_email(s3_client, email_content, direction):
    """Log email in mbox format
    direction: 'inbound' or 'outbound'
    """
    try:
        timestamp = datetime.utcnow()
        s3_client.put_object(
            Bucket=os.environ['LOG_BUCKET_NAME'],
            Key=f"emails/{direction}/{timestamp.strftime('%Y/%m/%d')}.mbox",
            Body=format_mbox_entry(email_content, timestamp),
            ContentType='application/mbox'
        )
    except Exception as e:
        print(f"Warning: Failed to log {direction} email: {str(e)}")

def send_confirmation_email(ses_client, email_addr, name, revocation_token):
    """Send confirmation email with revocation link"""
    template = get_template('confirmation_email')
    if not template:
        raise Exception("Could not load email template")

    msg = MIMEMultipart()
    msg['Subject'] = CONFIG['email']['subjects']['confirmation']
    msg['From'] = CONFIG['email']['from']
    msg['To'] = email_addr

    # Replace template variables
    revocation_url = f"{CONFIG['urls']['base']}/revoke?token={revocation_token}&email={email_addr}"
    signature_file = f"{CONFIG['paths']['signatures']}/{sanitize_filename(email_addr)}.yaml"
    
    body = template.format(
        name=name,
        email=email_addr,
        signature_file=signature_file,
        revocation_url=revocation_url,
        github_repo=CONFIG['urls']['github_repo']
    )
    
    msg.attach(MIMEText(body, 'plain'))
    raw_email = msg.as_string()

    try:
        ses_client.send_raw_email(
            Source=CONFIG['email']['from'],
            Destinations=[email_addr],
            RawMessage={'Data': raw_email}
        )
        # Log outbound email
        log_email(boto3.client('s3'), raw_email, 'outbound')
        return True
    except Exception as e:
        print(f"Error sending confirmation email: {str(e)}")
        return False

def create_codeberg_pr(email_addr, signature_data):
    """Create a branch and PR in Codeberg for the new signature"""
    api_token = os.environ['CODEBERG_TOKEN']
    headers = {
        'Authorization': f'token {api_token}',
        'Content-Type': 'application/json'
    }
    base_url = 'https://codeberg.org/api/v1'
    repo = 'osd/sos'
    
    branch_name = f"signature/{sanitize_filename(email_addr)}"
    file_path = f"{CONFIG['paths']['signatures']}/{sanitize_filename(email_addr)}.yaml"
    
    try:
        # 1. Get the current main branch SHA
        r = requests.get(f'{base_url}/repos/{repo}/branches/main', headers=headers)
        r.raise_for_status()
        main_sha = r.json()['commit']['sha']
        
        # 2. Create new branch
        data = {
            'ref': f'refs/heads/{branch_name}',
            'sha': main_sha
        }
        r = requests.post(f'{base_url}/repos/{repo}/git/refs', headers=headers, json=data)
        r.raise_for_status()
        
        # 3. Create file in new branch
        content = base64.b64encode(yaml.dump(signature_data).encode()).decode()
        data = {
            'branch': branch_name,
            'content': content,
            'message': f'Add signature via email for {email_addr}'
        }
        r = requests.post(f'{base_url}/repos/{repo}/contents/{file_path}', 
                         headers=headers, json=data)
        r.raise_for_status()
        
        # 4. Create PR
        data = {
            'title': f'Add signature for {email_addr}',
            'body': f'Signature request received via email from {email_addr}',
            'head': branch_name,
            'base': 'main'
        }
        r = requests.post(f'{base_url}/repos/{repo}/pulls', headers=headers, json=data)
        r.raise_for_status()
        
        return r.json()['html_url']  # Return PR URL
        
    except requests.exceptions.RequestException as e:
        raise Exception(f"Failed to create PR: {str(e)}")

def process_email(event, context):
    s3_client = boto3.client('s3')
    ses = boto3.client('ses')
    
    # Get the email from S3
    bucket = event['Records'][0]['s3']['bucket']['name']
    key = event['Records'][0]['s3']['object']['key']
    email_obj = s3_client.get_object(Bucket=bucket, Key=key)
    email_content = email_obj['Body'].read().decode('utf-8')
    
    # Log the incoming email
    log_email(s3_client, email_content, 'inbound')
    
    # Parse the email
    msg = email.message_from_string(email_content)
    
    # Extract sender info
    from_email = msg['from']
    name_match = re.match(r'"?([^"<]+)"?\s*<?([^>]+)>?', from_email)
    if name_match:
        name = name_match.group(1).strip()
        email_addr = name_match.group(2).strip()
    else:
        email_addr = from_email.strip()
        name = email_addr.split('@')[0]
    
    # Create signature data
    signature_data = {
        'name': name,
        'link': f'mailto:{email_addr}'
    }
    
    try:
        # Create PR in Codeberg
        pr_url = create_codeberg_pr(email_addr, signature_data)
        
        # Log the PR creation
        log_event(s3_client, 'signature_request', {
            'email': email_addr,
            'name': name,
            'pr_url': pr_url
        })
        
        # Send confirmation
        revocation_token = generate_revocation_token(email_addr)
        send_confirmation_email(ses, email_addr, name, revocation_token)
            
        return {
            'statusCode': 200,
            'body': f'Signature request received for {email_addr}, PR created at {pr_url}'
        }
    except Exception as e:
        return {
            'statusCode': 500,
            'body': f'Error processing signature request: {str(e)}'
        }
