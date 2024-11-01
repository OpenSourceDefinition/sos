import * as cdk from 'aws-cdk-lib';
import * as lambda from 'aws-cdk-lib/aws-lambda';
import * as s3 from 'aws-cdk-lib/aws-s3';
import * as ses from 'aws-cdk-lib/aws-ses';
import * as sesActions from 'aws-cdk-lib/aws-ses-actions';
import * as apigateway from 'aws-cdk-lib/aws-apigateway';
import * as iam from 'aws-cdk-lib/aws-iam';
import * as acm from 'aws-cdk-lib/aws-certificatemanager';
import * as fs from 'fs';
import * as yaml from 'js-yaml';
import * as path from 'path';
import { Construct } from 'constructs';

interface SignatureStackProps extends cdk.StackProps {
  config: {
    storage: {
      email_bucket: string;
      log_bucket: string;
    };
    domain: {
      mail: string;
    };
    email: {
      sign_address: string;
      from_address?: string;
      reply_to_address?: string;
      notification_address?: string;
    };
    github?: {
      repository?: string;
      owner?: string;
    };
    codeberg?: {
      repository?: string;
      owner?: string;
    };
  };
}

export class SignatureStack extends cdk.Stack {
  constructor(scope: Construct, id: string, props: SignatureStackProps) {
    super(scope, id, props);

    const { config } = props;

    // Create certificate
    const cert = new acm.Certificate(this, 'Certificate', {
      domainName: config.domain.mail,
      validation: acm.CertificateValidation.fromDns(),
    });

    // S3 bucket for incoming emails
    const emailBucket = new s3.Bucket(this, 'EmailBucket', {
      bucketName: config.storage.email_bucket,
      removalPolicy: cdk.RemovalPolicy.DESTROY,
      autoDeleteObjects: true,
    });

    // S3 bucket for email logs
    const logBucket = new s3.Bucket(this, 'EmailLogBucket', {
      bucketName: config.storage.log_bucket,
      removalPolicy: cdk.RemovalPolicy.RETAIN,
      lifecycleRules: [
        {
          expiration: cdk.Duration.days(90),
        },
      ],
    });

    // Lambda layer for dependencies
    const layer = new lambda.LayerVersion(this, 'DependenciesLayer', {
      code: lambda.Code.fromAsset('email/lambda-layer'),
      compatibleRuntimes: [lambda.Runtime.PYTHON_3_11],
      description: 'Dependencies for signature processing',
    });

    // Process signature Lambda
    const processSignatureLambda = new lambda.Function(this, 'ProcessSignature', {
      runtime: lambda.Runtime.PYTHON_3_11,
      code: lambda.Code.fromAsset('email/lambda', {
        exclude: ['*', '!*.py'],
        bundling: {
          image: lambda.Runtime.PYTHON_3_11.bundlingImage,
          command: [
            'bash', '-c',
            'pip install -r requirements.txt -t /asset-output && cp -au . /asset-output'
          ]
        }
      }),
      handler: 'process_signature.process_email',
      timeout: cdk.Duration.seconds(30),
      environment: {
        // Only secrets in environment
        GITHUB_TOKEN: process.env.GITHUB_TOKEN || '',
        GITHUB_REPO: process.env.GITHUB_REPO || '',
        CODEBERG_TOKEN: process.env.CODEBERG_TOKEN || '',
        REVOCATION_SECRET: process.env.REVOCATION_SECRET || '',
      },
      layers: [layer],
    });

    // Update revocation Lambda
    const revokeSignatureLambda = new lambda.Function(this, 'RevokeSignature', {
      runtime: lambda.Runtime.PYTHON_3_11,  // Update Python version
      code: lambda.Code.fromAsset('email/lambda', {  // Include config here too
        exclude: ['*', '!*.py'],
        bundling: {
          image: lambda.Runtime.PYTHON_3_11.bundlingImage,
          command: [
            'bash', '-c',
            'pip install -r requirements.txt -t /asset-output && cp -au . /asset-output'
          ]
        }
      }),
      handler: 'revoke_signature.revoke_signature',
      timeout: cdk.Duration.seconds(30),
      environment: {
        GITHUB_TOKEN: process.env.GITHUB_TOKEN || '',
        GITHUB_REPO: process.env.GITHUB_REPO || '',
        REVOCATION_SECRET: process.env.REVOCATION_SECRET || '',
      },
      layers: [layer],
    });

    // API Gateway for revocation endpoint
    const api = new apigateway.RestApi(this, 'SignatureApi', {
      restApiName: 'Signature Service',
    });

    const revoke = api.root.addResource('revoke');
    revoke.addMethod('GET', new apigateway.LambdaIntegration(revokeSignatureLambda));

    // Grant permissions
    emailBucket.grantRead(processSignatureLambda);
    processSignatureLambda.addToRolePolicy(new iam.PolicyStatement({
      actions: ['ses:SendRawEmail'],
      resources: ['*'],
    }));
    revokeSignatureLambda.addToRolePolicy(new iam.PolicyStatement({
      actions: ['ses:SendRawEmail'],
      resources: ['*'],
    }));
    logBucket.grantWrite(processSignatureLambda);  // Allow Lambda to write logs

    // SES Rule Set
    const ruleSet = new ses.ReceiptRuleSet(this, 'RuleSet', {
      receiptRuleSetName: 'signature-rules',
    });

    new ses.ReceiptRule(this, 'EmailRule', {
      ruleSet,
      recipients: [config.email.sign_address],
      actions: [
        new sesActions.S3({
          bucket: emailBucket,
          objectKeyPrefix: 'emails/',
        }),
        new sesActions.Lambda({
          function: processSignatureLambda,
        }),
      ],
    });

    // Custom domain for API Gateway
    const domain = new apigateway.DomainName(this, 'CustomDomain', {
      domainName: config.domain.mail,
      certificate: cert,
    });

    domain.addBasePathMapping(api);

    // Add outputs to help with DNS configuration
    new cdk.CfnOutput(this, 'ApiDomainTarget', {
      value: domain.domainNameAliasDomainName,
      description: 'Target domain name for CNAME record'
    });

    new cdk.CfnOutput(this, 'DKIMRecords', {
      value: 'Check SES console for DKIM records after deployment'
    });
  }
}
