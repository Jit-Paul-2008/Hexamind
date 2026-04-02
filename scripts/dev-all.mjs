import { spawn } from 'node:child_process';
import { execSync } from 'node:child_process';
import { existsSync, rmSync } from 'node:fs';

function runQuiet(command) {
  try {
    return execSync(command, { stdio: ['ignore', 'pipe', 'ignore'] })
      .toString()
      .trim();
  } catch {
    return '';
  }
}

function killPort(port) {
  const pids = runQuiet(`lsof -ti:${port}`)
    .split('\n')
    .map((v) => v.trim())
    .filter(Boolean);

  if (pids.length === 0) {
    // Fallback for environments where lsof cannot detect the owner process.
    runQuiet(`fuser -k ${port}/tcp`);
    return;
  }

  console.log(`Clearing port ${port} (PIDs: ${pids.join(', ')})`);
  for (const pid of pids) {
    runQuiet(`kill ${pid}`);
  }
}

function clearNextLock() {
  const lockPath = '.next/dev/lock';
  if (existsSync(lockPath)) {
    rmSync(lockPath, { force: true });
    console.log('Removed stale .next/dev/lock');
  }

  const cachePath = '.next/dev/cache';
  if (existsSync(cachePath)) {
    rmSync(cachePath, { recursive: true, force: true });
    console.log('Cleared .next/dev/cache');
  }
}

clearNextLock();
killPort(3000);
killPort(8000);

const backendCommand = 'python3';
const backendArgs = [
  '-m',
  'uvicorn',
  'main:app',
  '--app-dir',
  'ai-service',
  '--host',
  '127.0.0.1',
  '--port',
  '8000',
];

const frontendCommand = 'npm';
const frontendArgs = ['run', 'dev'];

const backend = spawn(backendCommand, backendArgs, {
  stdio: 'inherit',
  env: process.env,
});

const frontend = spawn(frontendCommand, frontendArgs, {
  stdio: 'inherit',
  env: process.env,
});

let shuttingDown = false;

function stopChildren(code = 0) {
  if (shuttingDown) {
    return;
  }

  shuttingDown = true;
  backend.kill('SIGTERM');
  frontend.kill('SIGTERM');
  process.exit(code);
}

process.on('SIGINT', () => stopChildren(0));
process.on('SIGTERM', () => stopChildren(0));
process.on('exit', () => {
  backend.kill('SIGTERM');
  frontend.kill('SIGTERM');
});

backend.on('exit', (code) => {
  if (code && code !== 0) {
    console.error(`Backend exited with code ${code}`);
    stopChildren(code);
  }
});

frontend.on('exit', (code) => {
  if (code && code !== 0) {
    console.error(`Frontend exited with code ${code}`);
    stopChildren(code);
  }
});

console.log('\nOpen this link after both lines say they are ready: http://localhost:3000\n');
