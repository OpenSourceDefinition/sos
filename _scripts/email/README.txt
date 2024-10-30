Email Signature System
=====================

This system handles email-based signatures for the Open Source Definition Declaration,
using AWS services (Lambda, SES, API Gateway) for processing.

Prerequisites
------------
1. AWS CLI installed and configured
2. Node.js and npm installed
3. AWS CDK installed: `npm install -g aws-cdk`
4. Domain verified in AWS SES
5. GitHub token with repo access
6. Python 3.9+

Setup Steps
----------
1. Install dependencies:
   ```
   cd _scripts/email
   npm install
   ```

2. Create a virtual environment and install Python dependencies:
   ```
   python -m venv .venv
   source .venv/bin/activate  # or `.venv\Scripts\activate` on Windows
   pip install -r requirements.txt
   ```

3. Set required environment variables:
   ```
   export GITHUB_TOKEN="your-github-token"
   export GITHUB_REPO="OpenSourceDefinition/sos"
   export REVOCATION_SECRET="your-secret-key"
   ```

4. Bootstrap CDK (first time only):
   ```
   cdk bootstrap aws://{account-id}/{region}
   ```

5. Deploy the stack:
   ```
   cdk deploy
   ```

6. After deployment, configure DNS:
   - Add MX records for mail.opensourcedeclaration.org
   - Add DKIM records (shown in deployment output)
   - Add SPF record
   Example records:
   ```
   mail.opensourcedeclaration.org.    IN MX 10 inbound-smtp.{region}.amazonaws.com.
   mail.opensourcedeclaration.org.    IN TXT "v=spf1 include:amazonses.com ~all"
   ```

7. Verify email sending:
   - Test sending an email to sign@mail.opensourcedeclaration.org
   - Check S3 bucket for incoming email
   - Verify signature file creation in GitHub

Maintenance
----------
- Monitor CloudWatch logs for Lambda functions
- Check SES bounce/complaint notifications
- Rotate GitHub token and REVOCATION_SECRET periodically
- Update dependencies as needed

File Structure
-------------
.
├── README.txt              # This file
├── bin/
│   └── app.ts             # CDK app entry point
├── lib/
│   └── signature-stack.ts  # Main stack definition
├── lambda/                 # Lambda function code
│   ├── process_signatures.py
│   └── revoke_signature.py
├── templates/              # Email templates
│   ├── confirmation_email.txt
│   └── revocation_email.txt
└── config.yml             # System configuration

Troubleshooting
--------------
1. Email not received:
   - Check SES console for bounces
   - Verify MX records
   - Check SES sending limits

2. Signature not created:
   - Check Lambda logs
   - Verify GitHub token permissions
   - Check S3 bucket for email content

3. Revocation not working:
   - Verify API Gateway endpoint
   - Check Lambda logs
   - Verify token generation

Support
-------
For issues or questions, please open a GitHub issue at:
https://github.com/OpenSourceDefinition/sos/issues
