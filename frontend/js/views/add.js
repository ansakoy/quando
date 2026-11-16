import { api, ApiError } from "../api.js";
import { todayISO } from "../format.js";
import { navigate } from "../router.js";
import { el, icon, hint, errorBanner } from "../ui.js";

export function renderAddView(container) {
  const content = el("div", { class: "content" });
  container.append(content);

  content.append(
    el("a", { class: "back-link", href: "#/" }, [icon("arrow-left", 16), el("span", { text: "Назначения" })])
  );

  content.append(
    el("div", { class: "page-head" }, [
      el("div", { class: "page-head-texts" }, [
        el("h1", { class: "page-title", text: "Добавить назначение" }),
        el("p", { class: "page-description", text: "Начните с даты назначения. Лекарства можно добавить после сохранения." }),
      ]),
    ])
  );

  const errorSlot = el("div");
  const fieldError = el("div", { class: "field-error-text", hidden: true });

  const dateInput = el("input", { type: "date", value: todayISO() });
  const dateField = el("div", { class: "field" }, [
    el("label", { class: "field-label", text: "Дата назначения" }),
    el("div", { class: "field-input" }, [dateInput]),
    fieldError,
  ]);

  const saveBtn = el("button", { class: "btn btn-primary", type: "button", text: "Сохранить" });
  const cancelBtn = el("button", { class: "btn btn-secondary", type: "button", text: "Отмена" });
  cancelBtn.addEventListener("click", () => navigate("#/"));

  saveBtn.addEventListener("click", async () => {
    errorSlot.textContent = "";
    fieldError.hidden = true;
    dateField.classList.remove("field-error");

    const value = dateInput.value;
    if (!value) {
      fieldError.textContent = "Укажите дату назначения.";
      fieldError.hidden = false;
      dateField.classList.add("field-error");
      return;
    }

    saveBtn.disabled = true;
    try {
      const created = await api.create({ start_date: value });
      navigate(`#/edit/${created.id}`);
    } catch (error) {
      saveBtn.disabled = false;
      if (error instanceof ApiError && error.status === 400 && Array.isArray(error.detail)) {
        fieldError.textContent = error.message;
        fieldError.hidden = false;
        dateField.classList.add("field-error");
      } else {
        errorSlot.append(errorBanner(error.message || "Не удалось сохранить назначение"));
      }
    }
  });

  content.append(
    el("div", { class: "card add-card" }, [
      errorSlot,
      el("div", { class: "add-field-block" }, [
        dateField,
        el("div", { class: "hint hint-13" }, [
          el("span", { text: "Укажите дату, с которой действует назначение." }),
        ]),
      ]),
      el("hr", { class: "separator" }),
      hint("ID будет назначен автоматически после создания: максимальный ID + 1."),
      el("div", { class: "form-actions" }, [saveBtn, cancelBtn]),
    ])
  );
}
