#!/usr/bin/env node
import 'source-map-support/register';
import * as cdk from 'aws-cdk-lib';
import * as yaml from 'js-yaml';
import * as fs from 'fs';
import * as path from 'path';
import { SignatureStack } from '../signature-stack';

const app = new cdk.App();

// Load config
const configPath = path.join(__dirname, '..', 'config.yml');
const config = yaml.load(fs.readFileSync(configPath, 'utf8')) as any;

new SignatureStack(app, 'SignatureStack', {
  env: { 
    account: process.env.CDK_DEFAULT_ACCOUNT, 
    region: 'us-west-2'
  },
  config,
});
