import { fmtDate, plural } from "./format.js";

const ICON = "assets/icons";

export function el(tag, attrs = {}, children = []) {
  const node = document.createElement(tag);
  for (const [key, value] of Object.entries(attrs)) {
    if (key === "class") node.className = value;
    else if (key === "text") node.textContent = value;
    else if (key.startsWith("on") && typeof value === "function") {
      node.addEventListener(key.slice(2).toLowerCase(), value);
    } else if (value !== null && value !== undefined) {
      node.setAttribute(key, value);
    }
  }
  for (const child of [].concat(children)) {
    if (child === null || child === undefined) continue;
    node.append(child.nodeType ? child : document.createTextNode(String(child)));
  }
  return node;
}

export function icon(name, size = 16, alt = "") {
  return el("img", { src: `${ICON}/${name}.svg`, alt, width: size, height: size });
}

export function hint(text, cls = "hint") {
  return el("div", { class: cls }, [icon("info", 16), el("span", { text })]);
}

export function errorBanner(message) {
  return el("div", { class: "banner-error", role: "alert", text: message });
}

export function replaceBanner(container, message) {
  const old = container.querySelector(".banner-error");
  if (old) old.remove();
  if (message) container.prepend(errorBanner(message));
}

export function openConfirmDelete({ prescription, onConfirm }) {
  const root = document.getElementById("modal-root");
  root.textContent = "";

  const medicines = prescription.medicines ?? [];
  const pickUpsCount = medicines.reduce((acc, m) => acc + (m.pick_ups?.length ?? 0), 0);
  const names = medicines.map((m) => m.name).filter(Boolean).join(", ");

  const errorSlot = el("div");

  function summaryRow(iconName, title, sub) {
    return el("div", { class: "modal-summary-row" }, [
      el("div", { class: "modal-summary-icon" }, [icon(iconName, iconName === "calendar-days" ? 16 : 18)]),
      el("div", { class: "modal-summary-texts" }, [
        el("div", { class: "modal-summary-title", text: title }),
        el("div", { class: "modal-summary-sub", text: sub }),
      ]),
    ]);
  }

  const cancelBtn = el("button", { class: "btn btn-secondary", type: "button", text: "Отмена" });
  const deleteBtn = el("button", { class: "btn btn-danger", type: "button", text: "Удалить" });

  const card = el("div", { class: "modal-card", role: "dialog", "aria-modal": "true" }, [
    el("div", { class: "modal-head" }, [
      el("h2", { class: "modal-title", text: "Удалить назначение?" }),
      el("p", {
        class: "modal-description",
        text: `Будет удалено назначение №${prescription.id} и все связанные с ним лекарства и записи о получении.`,
      }),
    ]),
    el("div", { class: "modal-summary" }, [
      summaryRow("pill", `Назначение №${prescription.id}`, `Дата назначения: ${fmtDate(prescription.start_date)}`),
      summaryRow("pill", `${medicines.length} ${plural(medicines.length, "лекарство", "лекарства", "лекарств")}`, names || "Лекарств нет"),
      summaryRow("calendar-days", `${pickUpsCount} ${plural(pickUpsCount, "запись о получении", "записи о получении", "записей о получении")}`, "Все связанные даты и количества будут удалены вместе с назначением"),
    ]),
    hint("Удаление назначения нельзя отменить. После подтверждения данные будут удалены без возможности восстановления."),
    errorSlot,
    el("div", { class: "modal-actions" }, [cancelBtn, deleteBtn]),
  ]);

  const overlay = el("div", { class: "modal-overlay" }, [card]);

  function close() {
    document.removeEventListener("keydown", onKeydown);
    overlay.remove();
  }

  function onKeydown(event) {
    if (event.key === "Escape") close();
  }

  overlay.addEventListener("click", (event) => {
    if (event.target === overlay) close();
  });
  cancelBtn.addEventListener("click", close);
  deleteBtn.addEventListener("click", async () => {
    deleteBtn.disabled = true;
    replaceBanner(errorSlot, null);
    try {
      await onConfirm();
      close();
    } catch (error) {
      replaceBanner(errorSlot, error.message || "Не удалось удалить назначение");
      deleteBtn.disabled = false;
    }
  });

  document.addEventListener("keydown", onKeydown);
  root.append(overlay);
}
