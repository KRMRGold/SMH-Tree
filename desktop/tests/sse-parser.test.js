import assert from "node:assert/strict";
import { test } from "node:test";

import { createSseParser } from "../main/sse-parser.js";

test("parses fragmented JSON events with CRLF separators", () => {
  const events = [];
  const parser = createSseParser((event, data) => events.push({ event, data }));

  parser.push('event: token\r\ndata: {"token":"hel');
  parser.push('lo"}\r\n\r\nevent: done\ndata: {"run_id":"r1"}\r\n\r\n');
  parser.end();

  assert.deepEqual(events, [
    { event: "token", data: { token: "hello" } },
    { event: "done", data: { run_id: "r1" } },
  ]);
});

test("supports LF frames, multiple data lines, and plain text", () => {
  const events = [];
  const parser = createSseParser((event, data) => events.push({ event, data }));

  parser.push("event: notice\ndata: first\ndata: second\n\n");
  parser.push("data: final-without-blank-line");
  parser.end();

  assert.deepEqual(events, [
    { event: "notice", data: "first\nsecond" },
    { event: "message", data: "final-without-blank-line" },
  ]);
});
