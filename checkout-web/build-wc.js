const esbuild = require('esbuild');
esbuild.build({
  entryPoints: ['src/wc-bridge.js'],
  bundle: true,
  outfile: 'public/wc-bundle.js',
  minify: true,
  format: 'iife',
  globalName: 'TangemBridge'
}).then(() => console.log('Tangem WC Bridge build complete')).catch(err => {
  console.error(err);
  process.exit(1);
});
