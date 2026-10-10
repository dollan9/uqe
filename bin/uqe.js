#!/usr/bin/env node

const { spawnSync } = require('child_process');
const path = require('path');
const os = require('os');

const rootDir = path.resolve(__dirname, '..');
const args = process.argv.slice(2);

const isWin = os.platform() === 'win32';
const pyCmd = isWin ? 'python' : 'python3';

const env = {
  ...process.env,
  PYTHONPATH: rootDir + (process.env.PYTHONPATH ? path.delimiter + process.env.PYTHONPATH : '')
};

const pyRes = spawnSync(pyCmd, ['-m', 'uqe.cli', ...args], { stdio: 'inherit', env });

if (!pyRes.error && pyRes.status !== null) {
  process.exit(pyRes.status);
}

// Fallback to native shell installer for 'init'
if (args[0] === 'init' || args.length === 0) {
  if (isWin) {
    const psScript = path.join(rootDir, 'install.ps1');
    const psRes = spawnSync('powershell', ['-ExecutionPolicy', 'Bypass', '-File', psScript, ...args.slice(1)], { stdio: 'inherit' });
    process.exit(psRes.status || 0);
  } else {
    const shScript = path.join(rootDir, 'install.sh');
    const shRes = spawnSync(shScript, args.slice(1), { stdio: 'inherit' });
    process.exit(shRes.status || 0);
  }
}

console.error('[uqe][ERROR] Python 3.9+ is required to execute full uqe CLI commands.');
process.exit(1);
