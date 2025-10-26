/**
 * Concordium Browser Wallet Integration
 *
 * Handles:
 * - Wallet connection
 * - Payment transactions (user-approved via wallet extension)
 * - Payment notification to server
 */

console.log('🔵 wallet.js is loading...');

// Wallet state
let connectedAccount = null;
let walletBalance = 0;

// Configuration
const PAYMENT_SERVICE_URL = window.location.protocol + '//' + window.location.host;
const NETWORK_ID = 100; // Concordium Testnet

/**
 * Check if Concordium Browser Wallet is installed
 */
function isWalletInstalled() {
    return typeof window.concordium !== 'undefined';
}

/**
 * Connect to Concordium Browser Wallet
 */
async function connectWallet() {
    if (!isWalletInstalled()) {
        alert('Concordium Browser Wallet not installed!\\nPlease install from:\\nhttps://chrome.google.com/webstore/detail/concordium-wallet');
        return false;
    }

    try {
        // Request account access
        const accounts = await window.concordium.requestAccounts();

        if (accounts && accounts.length > 0) {
            connectedAccount = accounts[0];
            console.log('Connected to wallet:', connectedAccount);

            // Get balance
            await updateBalance();

            // Update UI
            updateWalletUI();

            return true;
        } else {
            console.error('No accounts found');
            return false;
        }
    } catch (error) {
        console.error('Failed to connect wallet:', error);
        alert('Failed to connect wallet: ' + error.message);
        return false;
    }
}

/**
 * Disconnect wallet
 */
function disconnectWallet() {
    connectedAccount = null;
    walletBalance = 0;
    updateWalletUI();
}

/**
 * Get account balance from blockchain
 *
 * Note: Balance fetching requires the @concordium/web-sdk gRPC client.
 * For simplicity, we skip this and rely on the wallet extension to show balance.
 * The transaction will fail if there's insufficient balance anyway.
 */
async function updateBalance() {
    if (!connectedAccount) return;

    try {
        console.log('Balance check skipped - check your wallet extension for balance');
        console.log('Connected account:', connectedAccount);

        // Set a placeholder - actual balance shown in wallet extension
        walletBalance = -1; // -1 indicates balance not fetched

        updateWalletUI();
    } catch (error) {
        console.error('Failed to update UI:', error);
        walletBalance = -1;
        updateWalletUI();
    }
}


/**
 * Send CCD payment to recipient
 */
async function sendPayment(recipient, amountCCD, memo) {
    if (!connectedAccount) {
        throw new Error('Wallet not connected');
    }

    try {
        // Convert CCD to microCCD (Concordium's smallest unit)
        const amountMicroCCD = BigInt(Math.round(amountCCD * 1000000));

        console.log('Sending payment:', {
            from: connectedAccount,
            to: recipient,
            amount: amountCCD + ' CCD',
            amountMicroCCD: amountMicroCCD.toString(),
            memo: memo
        });

        // Create transfer transaction using Concordium Browser Wallet API
        console.log('Attempting transaction with parameters:', { recipient, amountCCD });

        // The wallet API expects amount as a string in CCD format, not BigInt
        const txHash = await window.concordium.sendTransaction(
            recipient,                    // receiver address
            amountCCD.toLocaleString('en-US', {useGrouping: false})  // amount as string in CCD
        );

        console.log('Transaction sent:', txHash);

        // Update balance after payment
        await updateBalance();

        return txHash;
    } catch (error) {
        console.error('Payment failed:', error);
        throw error;
    }
}

/**
 * Automatically process payment after inference
 */
async function autoPayInference(jobId, recipientAddress, amountCCD) {
    try {
        console.log('Processing payment for job:', jobId, 'Amount:', amountCCD, 'CCD');

        // Check if wallet is connected
        if (!connectedAccount) {
            return {
                success: false,
                error: 'Wallet not connected'
            };
        }

        // Send payment - user will approve in wallet extension
        const txHash = await sendPayment(recipientAddress, amountCCD, jobId);

        // Notify server that payment was sent
        await notifyPaymentSuccess(jobId, txHash, amountCCD);

        return {
            success: true,
            txHash: txHash,
            amount: amountCCD
        };

    } catch (error) {
        console.error('Payment failed:', error);
        return {
            success: false,
            error: error.message
        };
    }
}

/**
 * Notify server that payment was successful
 */
async function notifyPaymentSuccess(jobId, txHash, amount) {
    try {
        const response = await fetch(PAYMENT_SERVICE_URL + '/payment-confirmed', {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json'
            },
            body: JSON.stringify({
                job_id: jobId,
                transaction_hash: txHash,
                amount: amount
            })
        });

        if (!response.ok) {
            throw new Error('Server notification failed');
        }

        console.log('Payment notification sent to server');

        // Add to payment history
        addPaymentToHistory(jobId, amount, txHash);

        return true;
    } catch (error) {
        console.error('Failed to notify server:', error);
        return false;
    }
}

/**
 * Add payment to local history
 */
function addPaymentToHistory(jobId, amount, txHash) {
    try {
        let history = JSON.parse(localStorage.getItem('paymentHistory') || '[]');

        history.unshift({
            jobId: jobId,
            amount: amount,
            txHash: txHash,
            timestamp: new Date().toISOString(),
            explorerUrl: `https://testnet.ccdscan.io/transactions/${txHash}`
        });

        // Keep only last 50 payments
        history = history.slice(0, 50);

        localStorage.setItem('paymentHistory', JSON.stringify(history));
    } catch (error) {
        console.error('Failed to save payment history:', error);
    }
}

/**
 * Get payment history
 */
function getPaymentHistory() {
    try {
        return JSON.parse(localStorage.getItem('paymentHistory') || '[]');
    } catch (error) {
        console.error('Failed to load payment history:', error);
        return [];
    }
}

/**
 * Update wallet UI elements
 */
function updateWalletUI() {
    // This function will be called from the Gradio interface
    // to update UI elements based on wallet state

    const detail = {
        connected: !!connectedAccount,
        account: connectedAccount,
        balance: walletBalance
    };

    console.log('Dispatching walletStateChanged event:', detail);

    const event = new CustomEvent('walletStateChanged', {
        detail: detail
    });

    window.dispatchEvent(event);
}

/**
 * Initialize wallet on page load
 */
function initializeWallet() {
    // Check if wallet is installed
    if (!isWalletInstalled()) {
        console.warn('Concordium Browser Wallet not detected');
        return;
    }

    // Listen for account changes
    window.concordium.on('accountChanged', (account) => {
        console.log('Account changed:', account);
        connectedAccount = account;
        updateBalance();
    });

    // Listen for network changes
    window.concordium.on('chainChanged', (network) => {
        console.log('Network changed:', network);
        if (network !== NETWORK_ID) {
            alert('Please switch to Concordium Testnet');
        }
    });

    console.log('Wallet integration initialized');
}

// Set up UI event listeners
function setupUIListeners() {
    console.log('Setting up UI event listeners...');

    // Listen for wallet state changes and update UI
    window.addEventListener('walletStateChanged', function(e) {
        console.log('UI Event - Wallet state changed:', e.detail);

        // Update buttons using Tailwind classes
        const connectBtn = document.getElementById('connect-btn');
        const disconnectBtn = document.getElementById('disconnect-btn');

        if (connectBtn && disconnectBtn) {
            if (e.detail.connected) {
                connectBtn.classList.add('hidden');
                disconnectBtn.classList.remove('hidden');
                console.log('Updated buttons: showing disconnect, hiding connect');
            } else {
                connectBtn.classList.remove('hidden');
                disconnectBtn.classList.add('hidden');
                console.log('Updated buttons: showing connect, hiding disconnect');
            }
        } else {
            console.warn('Buttons not found yet, will retry...');
        }

        // Update status
        const status = document.getElementById('wallet-status');
        if (status) {
            if (e.detail.connected) {
                let balanceText = 'Check wallet extension for balance';
                if (e.detail.balance >= 0) {
                    balanceText = e.detail.balance.toFixed(4) + ' CCD';
                }
                status.innerHTML = '<strong>Status:</strong> Connected<br><strong>Account:</strong> ' + e.detail.account + '<br><strong>Balance:</strong> ' + balanceText;
                status.style.background = '#d4edda';
                console.log('Updated status to connected');
            } else {
                status.innerHTML = '<strong>Status:</strong> Not connected';
                status.style.background = '#f0f0f0';
                console.log('Updated status to disconnected');
            }
        } else {
            console.warn('Status element not found yet, will retry...');
        }
    });

    console.log('UI event listeners set up complete');
}

// Initialize when DOM is ready
if (document.readyState === 'loading') {
    document.addEventListener('DOMContentLoaded', function() {
        initializeWallet();
        setupUIListeners();
    });
} else {
    initializeWallet();
    setupUIListeners();
}

// Expose functions to global scope for Gradio to use
window.concordiumWallet = {
    isInstalled: isWalletInstalled,
    connect: connectWallet,
    disconnect: disconnectWallet,
    getBalance: () => walletBalance,
    getAccount: () => connectedAccount,
    autoPayInference: autoPayInference,
    getPaymentHistory: getPaymentHistory,
    updateBalance: updateBalance
};
