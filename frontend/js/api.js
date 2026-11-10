export class ApiError extends Error {
  constructor(status, detail, message) {
    super(message);
    this.status = status;
    this.detail = detail;
  }
}

function detailToMessage(detail, fallback) {
  if (typeof detail === "string") return detail;
  if (Array.isArray(detail)) {
    const parts = detail.map((e) => {
      const loc = Array.isArray(e.loc) ? e.loc.filter((p) => p !== "body").join(".") : "";
      return loc ? `${loc}: ${e.msg}` : String(e.msg ?? "");
    });
    if (parts.length) return parts.join("; ");
  }
  return fallback;
}

async function request(method, path, body) {
  let response;
  try {
    response = await fetch(path, {
      method,
      headers: body === undefined ? undefined : { "Content-Type": "application/json" },
      body: body === undefined ? undefined : JSON.stringify(body),
    });
  } catch {
    throw new ApiError(0, null, "Не удалось связаться с сервером");
  }
  if (response.status === 204) return null;
  let data = null;
  const text = await response.text();
  if (text) {
    try {
      data = JSON.parse(text);
    } catch {
      data = null;
    }
  }
  if (!response.ok) {
    const detail = data && "detail" in data ? data.detail : null;
    throw new ApiError(response.status, detail, detailToMessage(detail, `Ошибка сервера (${response.status})`));
  }
  return data;
}

export const api = {
  list: () => request("GET", "/api/prescriptions/"),
  get: (id) => request("GET", `/api/prescriptions/${id}/`),
  create: (data) => request("POST", "/api/prescriptions/", data),
  update: (id, data) => request("PUT", `/api/prescriptions/${id}/`, data),
  remove: (id) => request("DELETE", `/api/prescriptions/${id}/`),
};
