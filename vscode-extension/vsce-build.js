// Node.js v18 compatibility wrapper for vsce
const { execSync } = require('child_process');

if (typeof global.File === 'undefined') {
    global.File = class extends Blob {
        constructor(parts, filename, options = {}) {
            super(parts, options);
            this.name = filename;
            this.lastModified = options.lastModified || Date.now();
        }
    };
}

try {
    console.log('Building VSIX...');
    execSync('npx @vscode/vsce package --no-dependencies --out moco-chat.vsix', { 
        stdio: 'inherit',
        env: { ...process.env, NODE_OPTIONS: '--no-warnings' }
    });
    console.log('Build successful: moco-chat.vsix');
} catch (e) {
    console.error('Build failed:', e.message);
}
