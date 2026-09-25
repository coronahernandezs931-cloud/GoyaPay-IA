const { SignClient } = require('@walletconnect/sign-client');
const QRCode = require('qrcode');

let signClient = null;

async function initClient() {
  if (signClient) return signClient;
  signClient = await SignClient.init({
    projectId: '3a8170812b534d0ff9d794f19a901d64',
    metadata: {
      name: 'GoyaPay AI',
      description: 'Pasarela de Pagos Tangem',
      url: 'https://checkout-web-seven.vercel.app',
      icons: ['https://checkout-web-seven.vercel.app/tangem-icon.png']
    }
  });
  return signClient;
}

module.exports = {
  renderQR: function(canvasEl, text) {
    return QRCode.toCanvas(canvasEl, text, { width: 220, margin: 1, color: { dark: '#020617', light: '#ffffff' } });
  },
  crearSesionReal: async function(onUri, onApproval) {
    const client = await initClient();
    const { uri, approval } = await client.connect({
      requiredNamespaces: {
        eip155: {
          methods: ['personal_sign', 'eth_sendTransaction'],
          chains: ['eip155:1'],
          events: ['chainChanged', 'accountsChanged']
        }
      }
    });
    if (uri && onUri) onUri(uri);
    try {
      const session = await approval();
      if (onApproval) onApproval(session);
      return session;
    } catch (e) {
      console.log('Sesion terminada:', e);
    }
  }
};
