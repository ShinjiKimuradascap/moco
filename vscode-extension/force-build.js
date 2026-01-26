const { execSync } = require('child_process');
const fs = require('fs');
const path = require('path');

// 1. VSCE needs 'File' in global context for some reasons in Node 18
const buildScript = `
const { execSync } = require('child_process');
global.File = class extends Blob {
    constructor(parts, filename, options = {}) {
        super(parts, options);
        this.name = filename;
        this.lastModified = options.lastModified || Date.now();
    }
};
console.log('Starting vsce package within shimmed environment...');
execSync('npx @vscode/vsce package --no-dependencies --out moco-latest.vsix', { stdio: 'inherit' });
`;

fs.writeFileSync('shim-vsce.js', buildScript);

try {
    console.log('Running vsce with File shim...');
    execSync('node shim-vsce.js', { stdio: 'inherit' });
    console.log('Success: moco-latest.vsix created.');
} catch (e) {
    console.error('Failed to create VSIX.');
} finally {
    if (fs.existsSync('shim-vsce.js')) fs.unlinkSync('shim-vsce.js');
}
