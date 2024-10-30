import * as cdk from 'aws-cdk-lib';
import * as lambda from 'aws-cdk-lib/aws-lambda';
import * as s3 from 'aws-cdk-lib/aws-s3';
import * as ses from 'aws-cdk-lib/aws-ses';
import * as sesActions from 'aws-cdk-lib/aws-ses-actions';
import * as apigateway from 'aws-cdk-lib/aws-apigateway';
import * as iam from 'aws-cdk-lib/aws-iam';
import * as route53 from 'aws-cdk-lib/aws-route53';
import * as targets from 'aws-cdk-lib/aws-route53-targets';
import * as acm from 'aws-cdk-lib/aws-certificatemanager';
import { Construct } from 'constructs';

export class SignatureStack extends cdk.Stack {
  constructor(scope: Construct, id: string, props?: cdk.StackProps) {
    super(scope, id, props);

    // Lookup hosted zone
    const zone = route53.HostedZone.fromLookup(this, 'Zone', {
      domainName: 'opensourcedeclaration.org'
    });

    // Certificate for custom domain
    const cert = new acm.Certificate(this, 'Certificate', {
      domainName: 'mail.opensourcedeclaration.org',
      validation: acm.CertificateValidation.fromDns(zone),
    });

    // S3 bucket for incoming emails
    const emailBucket = new s3.Bucket(this, 'EmailBucket', {
      removalPolicy: cdk.RemovalPolicy.DESTROY,
      autoDeleteObjects: true,
    });

    // Lambda layer for dependencies
    const layer = new lambda.LayerVersion(this, 'DependenciesLayer', {
      code: lambda.Code.fromAsset('lambda-layer'),
      compatibleRuntimes: [lambda.Runtime.PYTHON_3_9],
      description: 'Dependencies for signature processing',
    });

    // Process signature Lambda
    const processSignatureLambda = new lambda.Function(this, 'ProcessSignature', {
      runtime: lambda.Runtime.PYTHON_3_9,
      code: lambda.Code.fromAsset('lambda'),
      handler: 'process_signatures.process_email',
      timeout: cdk.Duration.seconds(30),
      environment: {
        GITHUB_TOKEN: process.env.GITHUB_TOKEN || '',
        GITHUB_REPO: process.env.GITHUB_REPO || '',
        REVOCATION_SECRET: process.env.REVOCATION_SECRET || '',
      },
      layers: [layer],
    });

    // Revocation Lambda
    const revokeSignatureLambda = new lambda.Function(this, 'RevokeSignature', {
      runtime: lambda.Runtime.PYTHON_3_9,
      code: lambda.Code.fromAsset('lambda'),
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

    // SES Rule Set
    const ruleSet = new ses.ReceiptRuleSet(this, 'RuleSet', {
      receiptRuleSetName: 'signature-rules',
    });

    new ses.ReceiptRule(this, 'EmailRule', {
      ruleSet,
      recipients: [process.env.SIGN_EMAIL || 'sign@your-domain.com'],
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
      domainName: 'mail.opensourcedeclaration.org',
      certificate: cert,
    });

    domain.addBasePathMapping(api);

    // DNS record for custom domain
    new route53.ARecord(this, 'ApiDomain', {
      zone,
      recordName: 'mail',
      target: route53.RecordTarget.fromAlias(
        new targets.ApiGatewayDomain(domain)
      ),
    });

    // Output the DKIM records
    new cdk.CfnOutput(this, 'DKIMRecords', {
      value: 'Check SES console for DKIM records after deployment'
    });
  }
}
