import test from 'node:test';
import assert from 'node:assert/strict';
import { readFileSync } from 'node:fs';
import { resolve } from 'node:path';

test('frontend parses typed SSE payload from default message events', () => {
  const file = resolve('src/components/ResearchConsole.tsx');
  const content = readFileSync(file, 'utf8');

  assert.match(content, /const data = JSON\.parse\(event\.data\)/);
  assert.match(content, /const eventType = data\.type/);
  assert.match(content, /eventType === PipelineEventType\.PIPELINE_DONE/);
});

test('backend emits standard message payload containing PipelineEvent JSON', () => {
  const file = resolve('ai-service/reasoning_graph.py');
  const content = readFileSync(file, 'utf8');

  assert.match(content, /PipelineEvent\(/);
  assert.match(content, /return \{"data": event_obj\.model_dump_json\(\)\}/);
});
