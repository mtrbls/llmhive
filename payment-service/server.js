#!/usr/bin/env node
/**
 * ODLA Payment Service - Concordium PLT Stablecoin Integration
 *
 * This microservice handles Concordium blockchain payments using PLT stablecoins.
 * PLT (Protocol-Level Tokens) are native to Concordium protocol - more secure than
 * smart contract tokens, no attack vectors, perfect for real-world payments.
 *
 * Supports: USDR, EURR, eUSD, eEUR, eGBP, eSGD, VEUR, VCHF, VGBP
 */

import express from 'express';
import cors from 'cors';
import dotenv from 'dotenv';

// Import from web-sdk/nodejs for Node.js backend
import { ConcordiumGRPCNodeClient, credentials } from '@concordium/web-sdk/nodejs';

import {
  AccountAddress,
  CcdAmount,
  TransactionExpiry,
  AccountTransactionType,
  buildAccountSigner,
  signTransaction,
} from '@concordium/web-sdk';

dotenv.config();

const app = express();
app.use(cors());
app.use(express.json());

// Configuration
const PORT = process.env.PORT || 3000;
const CONCORDIUM_NODE_HOST = process.env.CONCORDIUM_NODE_HOST || 'grpc.testnet.concordium.com';
const CONCORDIUM_NODE_PORT = parseInt(process.env.CONCORDIUM_NODE_PORT || '20000');
const NETWORK_ID = process.env.NETWORK_ID || '100'; // 100 = testnet, 1 = mainnet

// Initialize Concordium client with proper credentials
const client = new ConcordiumGRPCNodeClient(
    CONCORDIUM_NODE_HOST,
    CONCORDIUM_NODE_PORT,
    credentials.createSsl()
);

/**
 * Health check endpoint
 */
app.get('/health', (req, res) => {
  res.json({
    status: 'healthy',
    service: 'odla-payment-service',
    concordium_node: `${CONCORDIUM_NODE_HOST}:${CONCORDIUM_NODE_PORT}`,
    network_id: NETWORK_ID
  });
});

/**
 * Send payment using CCD or PLT stablecoin
 *
 * POST /pay
 * Body:
 * {
 *   "amount": 1.5,           // Amount in CCD/stablecoin units
 *   "recipient": "3sXy...",  // Concordium account address
 *   "memo": "job-123",       // Job ID for tracking (optional)
 *   "sender_key": "...",     // Private key as hex string
 *   "sender_address": "..."  // Sender account address
 * }
 *
 * Returns:
 * {
 *   "success": true,
 *   "transaction_hash": "abc123...",
 *   "amount": 1.5,
 *   "recipient": "3sXy...",
 *   "memo": "job-123"
 * }
 */
app.post('/pay', async (req, res) => {
  try {
    const { amount, recipient, memo, sender_key, sender_address } = req.body;

    // Validate inputs
    if (!amount || !recipient || !sender_key || !sender_address) {
      return res.status(400).json({
        error: 'Missing required fields: amount, recipient, sender_key, sender_address'
      });
    }

    // Convert amount to micro CCD (6 decimals)
    const microAmount = BigInt(Math.round(amount * 1_000_000));
    const ccdAmount = CcdAmount.fromMicroCcd(microAmount);

    // Parse addresses
    const recipientAddress = AccountAddress.fromBase58(recipient);
    const senderAddr = AccountAddress.fromBase58(sender_address);

    // Get next account nonce
    const accountInfo = await client.getAccountInfo(senderAddr);
    const nonce = accountInfo.accountNonce;

    // Build SimpleTransferPayload
    const payload = {
      amount: ccdAmount,
      toAddress: recipientAddress,
    };

    // Create transaction header
    const header = {
      expiry: TransactionExpiry.fromDate(new Date(Date.now() + 300000)), // 5 min
      nonce: nonce,
      sender: senderAddr,
    };

    // Construct AccountTransaction object
    const accountTransaction = {
      header: header,
      payload: payload,
      type: AccountTransactionType.Transfer,
    };

    // Build signer from private key hex string
    const signer = buildAccountSigner(sender_key);

    // Sign the transaction
    const signature = await signTransaction(accountTransaction, signer);

    // Send transaction to blockchain
    const txHash = await client.sendAccountTransaction(
      accountTransaction,
      signature
    );

    console.log(`Payment sent: ${amount} CCD to ${recipient}, tx: ${txHash}`);

    res.json({
      success: true,
      transaction_hash: txHash,
      amount: amount,
      recipient: recipient,
      memo: memo || null,
      explorer_url: `https://testnet.ccdscan.io/?dcount=1&dentity=transaction&dhash=${txHash}`
    });

  } catch (error) {
    console.error('Payment error:', error);
    res.status(500).json({
      error: 'Payment failed',
      message: error.message,
      details: error.toString()
    });
  }
});

/**
 * Get account balance
 *
 * GET /balance/:address
 */
app.get('/balance/:address', async (req, res) => {
  try {
    const address = AccountAddress.fromBase58(req.params.address);
    const accountInfo = await client.getAccountInfo(address);

    res.json({
      address: req.params.address,
      balance: accountInfo.accountAmount.microCcdAmount.toString(),
      balance_ccd: Number(accountInfo.accountAmount.microCcdAmount) / 1_000_000
    });

  } catch (error) {
    console.error('Balance check error:', error);
    res.status(500).json({
      error: 'Failed to get balance',
      message: error.message
    });
  }
});

/**
 * Get transaction status
 *
 * GET /transaction/:hash
 */
app.get('/transaction/:hash', async (req, res) => {
  try {
    const txHash = req.params.hash;
    const status = await client.getBlockItemStatus(txHash);

    res.json({
      transaction_hash: txHash,
      status: status,
      explorer_url: `https://testnet.ccdscan.io/?dcount=1&dentity=transaction&dhash=${txHash}`
    });

  } catch (error) {
    console.error('Transaction status error:', error);
    res.status(500).json({
      error: 'Failed to get transaction status',
      message: error.message
    });
  }
});

// Start server
app.listen(PORT, () => {
  console.log(`\n${'='.repeat(60)}`);
  console.log(`ODLA Payment Service - Concordium Integration`);
  console.log(`${'='.repeat(60)}`);
  console.log(`Status: Running on port ${PORT}`);
  console.log(`Network: ${NETWORK_ID === '100' ? 'Testnet' : 'Mainnet'}`);
  console.log(`Node: ${CONCORDIUM_NODE_HOST}:${CONCORDIUM_NODE_PORT}`);
  console.log(`\nEndpoints:`);
  console.log(`  GET  /health - Health check`);
  console.log(`  POST /pay - Send PLT stablecoin payment`);
  console.log(`  GET  /balance/:address - Check account balance`);
  console.log(`  GET  /transaction/:hash - Get transaction status`);
  console.log(`${'='.repeat(60)}\n`);
});
