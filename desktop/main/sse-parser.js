export function createSseParser(onEvent) {
  let buffer = "";

  const emitFrame = (frame) => {
    let eventName = "message";
    const dataLines = [];

    for (const line of frame.split(/\r\n|\n|\r/)) {
      if (line.startsWith("event:")) eventName = line.slice(6).trim();
      else if (line.startsWith("data:")) dataLines.push(line.slice(5).trimStart());
    }

    if (!dataLines.length) return;
    const rawData = dataLines.join("\n");
    let data = rawData;
    try {
      data = JSON.parse(rawData);
    } catch {
      // SSE permits plain-text data as well as JSON.
    }
    onEvent(eventName, data);
  };

  return {
    push(chunk) {
      buffer += chunk;
      let boundary;
      while ((boundary = buffer.search(/\r?\n\r?\n/)) !== -1) {
        const frame = buffer.slice(0, boundary);
        const separator = buffer.slice(boundary).match(/^\r?\n\r?\n/)[0];
        buffer = buffer.slice(boundary + separator.length);
        emitFrame(frame);
      }
    },
    end() {
      if (buffer.trim()) emitFrame(buffer);
      buffer = "";
    },
  };
}
