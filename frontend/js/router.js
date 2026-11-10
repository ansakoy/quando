export function parseRoute() {
  const hash = location.hash || "#/";
  const path = hash.replace(/^#/, "");
  if (path === "/" || path === "") return { name: "list" };
  if (path === "/new") return { name: "add" };
  const editMatch = path.match(/^\/edit\/(\d+)\/?$/);
  if (editMatch) return { name: "edit", id: Number(editMatch[1]) };
  return { name: "list" };
}

let expandTargetId = null;

export function setExpandTarget(id) {
  expandTargetId = id;
}

export function consumeExpandTarget() {
  const id = expandTargetId;
  expandTargetId = null;
  return id;
}

export function navigate(hash) {
  if (location.hash === hash) {
    window.dispatchEvent(new HashChangeEvent("hashchange"));
  } else {
    location.hash = hash;
  }
}
