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

    try:
        ses_client.send_raw_email(
            Source=CONFIG['email']['from'],
            Destinations=[email_addr],
            RawMessage={'Data': msg.as_string()}
        )
        return True
    except Exception as e:
        print(f"Error sending confirmation email: {str(e)}")
        return False

def process_email(event, context):
    s3 = boto3.client('s3')
    ses = boto3.client('ses')
    
    # Get the email from S3
    bucket = event['Records'][0]['s3']['bucket']['name']
    key = event['Records'][0]['s3']['object']['key']
    email_obj = s3.get_object(Bucket=bucket, Key=key)
    email_content = email_obj['Body'].read().decode('utf-8')
    
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
    
    # Initialize GitHub client
    g = Github(os.environ['GITHUB_TOKEN'])
    repo = g.get_repo(os.environ['GITHUB_REPO'])
    
    try:
        # Create signature file
        file_path = f"{CONFIG['paths']['signatures']}/{sanitize_filename(email_addr)}.yaml"
        repo.create_file(
            path=file_path,
            message=f"Add signature via email for {email_addr}",
            content=yaml.dump(signature_data, default_flow_style=False),
            branch="main"
        )
        
        # Send confirmation
        revocation_token = generate_revocation_token(email_addr)
        send_confirmation_email(ses, email_addr, name, revocation_token)
            
        return {
            'statusCode': 200,
            'body': f'Signature added successfully for {email_addr} and confirmation sent'
        }
    except Exception as e:
        if "Not possible to fast-forward" in str(e):
            revocation_token = generate_revocation_token(email_addr)
            send_confirmation_email(ses, email_addr, name, revocation_token)
            return {
                'statusCode': 200,
                'body': f'Signature already exists for {email_addr}, confirmation sent'
            }
        return {
            'statusCode': 500,
            'body': f'Error processing signature: {str(e)}'
        }
