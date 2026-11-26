const MAX_IMAGES = 4;
const MAX_IMAGE_BYTES = 4 * 1024 * 1024;
const MAX_TOTAL_BYTES = 8 * 1024 * 1024;

function imageType(bytes) {
  const matches = (signature, offset = 0) =>
    signature.every((byte, index) => bytes[offset + index] === byte);
  if (matches([0x89, 0x50, 0x4e, 0x47, 0x0d, 0x0a, 0x1a, 0x0a])) return "image/png";
  if (matches([0xff, 0xd8, 0xff])) return "image/jpeg";
  if (matches([0x52, 0x49, 0x46, 0x46]) && matches([0x57, 0x45, 0x42, 0x50], 8)) {
    return "image/webp";
  }
  return null;
}

export async function readChatImage(file) {
  if (file.size > MAX_IMAGE_BYTES) {
    throw new Error(`${file.name} exceeds 4 MiB per image.`);
  }
  let bytes;
  try {
    bytes = new Uint8Array(await file.arrayBuffer());
  } catch {
    throw new Error(`Could not read ${file.name}.`);
  }
  const media_type = imageType(bytes);
  if (!media_type) throw new Error(`${file.name} must be a PNG, JPEG, or WebP image.`);

  let binary = "";
  for (let offset = 0; offset < bytes.length; offset += 0x4000) {
    binary += String.fromCharCode(...bytes.subarray(offset, offset + 0x4000));
  }
  return { name: file.name, size: bytes.length, media_type, data: btoa(binary) };
}

export function bindChatImages({ panel, composer, picker, attach, previews, status, remote, getProvider, canAttach }) {
  let images = [];
  let revision = 0;
  let loading = false;
  let dragDepth = 0;

  function updateProvider() {
    const provider = getProvider();
    remote.hidden = !images.length || !provider?.is_remote;
    remote.textContent = remote.hidden ? "" : `Images will be sent to ${provider.label}.`;
  }

  function render() {
    previews.replaceChildren();
    previews.hidden = images.length === 0;
    for (const image of images) {
      const item = document.createElement("li");
      const thumbnail = document.createElement("img");
      thumbnail.alt = "";
      thumbnail.src = `data:${image.media_type};base64,${image.data}`;
      const name = document.createElement("span");
      name.textContent = image.name;
      name.title = image.name;
      const remove = document.createElement("button");
      remove.type = "button";
      remove.textContent = "×";
      remove.setAttribute("aria-label", `Remove ${image.name}`);
      remove.addEventListener("click", () => {
        images = images.filter((attached) => attached !== image);
        if (!loading) status.textContent = "";
        render();
        (previews.querySelector("button") ?? attach).focus();
      });
      item.append(thumbnail, name, remove);
      previews.append(item);
    }
    updateProvider();
  }

  function endDrag() {
    dragDepth = 0;
    composer.classList.remove("image-drop-active");
  }

  function reset() {
    revision += 1;
    loading = false;
    images = [];
    attach.disabled = false;
    picker.value = "";
    status.textContent = "";
    endDrag();
    render();
  }

  async function addFiles(files) {
    if (!canAttach() || !files.length || loading) return;
    const currentRevision = revision;
    loading = true;
    attach.disabled = true;
    status.textContent = "Reading images…";
    const errors = [];
    try {
      for (const file of files) {
        if (images.length >= MAX_IMAGES) {
          errors.push("Attach up to 4 images per message.");
          break;
        }
        const usedBytes = images.reduce((total, image) => total + image.size, 0);
        if (file.size <= MAX_IMAGE_BYTES && usedBytes + file.size > MAX_TOTAL_BYTES) {
          errors.push("Attachments must total 8 MiB or less.");
          continue;
        }

        try {
          const image = await readChatImage(file);
          if (currentRevision !== revision) return;
          images.push(image);
        } catch (error) {
          if (currentRevision !== revision) return;
          errors.push(error.message);
        }
      }
    } finally {
      if (currentRevision === revision) {
        loading = false;
        attach.disabled = false;
        status.textContent = errors[0] ?? "";
        render();
      }
    }
  }

  function isFileDrag(event) {
    return event.dataTransfer?.types.includes("Files");
  }

  attach.addEventListener("click", () => picker.click());
  picker.addEventListener("change", () => {
    const files = Array.from(picker.files);
    picker.value = "";
    void addFiles(files);
  });
  panel.addEventListener("dragenter", (event) => {
    if (!isFileDrag(event)) return;
    event.preventDefault();
    dragDepth += 1;
    if (canAttach() && !loading) composer.classList.add("image-drop-active");
  });
  panel.addEventListener("dragover", (event) => {
    if (!isFileDrag(event)) return;
    event.preventDefault();
    event.dataTransfer.dropEffect = canAttach() && !loading ? "copy" : "none";
  });
  panel.addEventListener("dragleave", () => {
    if (dragDepth > 0) dragDepth -= 1;
    if (!dragDepth) endDrag();
  });
  panel.addEventListener("drop", (event) => {
    if (!isFileDrag(event)) return;
    event.preventDefault();
    endDrag();
    void addFiles(Array.from(event.dataTransfer.files));
  });

  return {
    reset,
    updateProvider,
    get loading() { return loading; },
    payload: () => images.map(({ media_type, data }) => ({ media_type, data })),
  };
}
