import assert from 'node:assert/strict';
import { spawn } from 'node:child_process';
import { once } from 'node:events';
import { setTimeout as delay } from 'node:timers/promises';
import { test, before, after } from 'node:test';

const port = 8123;
const baseUrl = `http://127.0.0.1:${port}`;
let backendProcess;
let startupLogs = '';

function parseSseFrame(frameText) {
  const frame = {};
  for (const line of frameText.split('\n')) {
    if (!line) {
      continue;
    }

    const separatorIndex = line.indexOf(': ');
    if (separatorIndex === -1) {
      continue;
    }

    const key = line.slice(0, separatorIndex);
    const value = line.slice(separatorIndex + 2);
    frame[key] = frame[key] ? `${frame[key]}\n${value}` : value;
  }

  return frame;
}

async function waitForBackendReady() {
  for (let attempt = 0; attempt < 60; attempt += 1) {
    try {
      const response = await fetch(`${baseUrl}/health`);
      if (response.ok) {
        return;
      }
    } catch {
      // Retry until the server is ready.
    }

    await delay(100);
  }

  throw new Error(`Backend did not become ready. Logs:\n${startupLogs}`);
}

before(async () => {
  const pythonExecutable = process.env.HEXAMIND_PYTHON ?? '.venv/bin/python';

  backendProcess = spawn(
    pythonExecutable,
    ['-m', 'uvicorn', 'main:app', '--app-dir', 'ai-service', '--host', '127.0.0.1', '--port', String(port)],
    {
      env: {
        ...process.env,
        PYTHONUNBUFFERED: '1',
        HEXAMIND_WEB_RESEARCH: '0',
        HEXAMIND_MODEL_PROVIDER: 'deterministic',
        HEXAMIND_DISABLE_FAILSAFE_FALLBACK: '0',
      },
      stdio: ['ignore', 'pipe', 'pipe'],
    },
  );

  backendProcess.stdout.on('data', (chunk) => {
    startupLogs += chunk.toString();
  });

  backendProcess.stderr.on('data', (chunk) => {
    startupLogs += chunk.toString();
  });

  await waitForBackendReady();
});

after(async () => {
  if (!backendProcess) {
    return;
  }

  backendProcess.kill('SIGTERM');
  await once(backendProcess, 'exit').catch(() => {});
});

test('backend health and agents endpoint are available', async () => {
  const healthResponse = await fetch(`${baseUrl}/health`);
  assert.equal(healthResponse.status, 200);
  const healthPayload = await healthResponse.json();
  assert.equal(healthPayload.status, 'ok');
  assert.ok(Object.hasOwn(healthPayload, 'activeProvider'));
  assert.ok(Object.hasOwn(healthPayload, 'isFallback'));

  const agentsResponse = await fetch(`${baseUrl}/api/agents`);
  assert.equal(agentsResponse.status, 200);
  const agents = await agentsResponse.json();
  assert.equal(agents.length, 5);
  assert.deepEqual(agents.map((agent) => agent.id), ['advocate', 'skeptic', 'synthesiser', 'oracle', 'verifier']);
});

test('pipeline stream emits a final synthesis for the submitted query', async () => {
  const startResponse = await fetch(`${baseUrl}/api/pipeline/start`, {
    method: 'POST',
    headers: {
      'Content-Type': 'application/json',
    },
    body: JSON.stringify({ query: 'How should we ship the MVP?' }),
  });

  assert.equal(startResponse.status, 200);
  const { sessionId } = await startResponse.json();
  assert.ok(sessionId);

  const streamResponse = await fetch(`${baseUrl}/api/pipeline/${sessionId}/stream`);
  assert.equal(streamResponse.status, 200);
  assert.ok(streamResponse.body);

  const reader = streamResponse.body.getReader();
  const decoder = new TextDecoder();
  let buffer = '';
  let finalPayload = null;

  try {
    while (true) {
      const { value, done } = await reader.read();
      if (done) {
        break;
      }

      buffer += decoder.decode(value, { stream: true });
      buffer = buffer.replace(/\r\n/g, '\n');

      let separatorIndex = buffer.indexOf('\n\n');
      while (separatorIndex !== -1) {
        const frameText = buffer.slice(0, separatorIndex);
        buffer = buffer.slice(separatorIndex + 2);
        const frame = parseSseFrame(frameText);

        if (frame.event === 'pipeline_done') {
          finalPayload = JSON.parse(frame.data);
          await reader.cancel();
          break;
        }

        separatorIndex = buffer.indexOf('\n\n');
      }

      if (finalPayload) {
        break;
      }
    }
  } finally {
    reader.releaseLock();
  }

  assert.ok(finalPayload);
  assert.equal(finalPayload.agentId, 'output');
  assert.match(finalPayload.fullContent, /## (Executive Summary|Abstract)/);
});
