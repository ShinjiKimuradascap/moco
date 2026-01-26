const { pack } = require('@vscode/vsce');
global.File = class {};
pack().then(() => console.log('VSIX generated')).catch(e => {
    console.error(e);
    process.exit(1);
});
