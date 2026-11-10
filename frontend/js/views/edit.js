import { api, ApiError } from "../api.js";
import { fmtDate } from "../format.js";
import { navigate, setExpandTarget } from "../router.js";
import { el, icon, hint, errorBanner, replaceBanner, openConfirmDelete } from "../ui.js";

export async function renderEditView(container, id) {
  const content = el("div", { class: "content" });
  container.append(content);

  let rx;
  try {
    rx = await api.get(id);
  } catch (error) {
    const message =
      error instanceof ApiError && error.status === 404
        ? `Назначение №${id} не найдено.`
        : error.message || "Не удалось загрузить назначение";
    content.append(errorBanner(message));
    setTimeout(() => navigate("#/"), 1500);
    return;
  }

  buildForm(content, rx);
}

function buildForm(content, rx) {
  const draft = {
    start_date: rx.start_date,
    medicines: (rx.medicines ?? []).map((m) => ({
      name: m.name ?? "",
      num_pills: m.num_pills != null ? String(m.num_pills) : "",
      per_day: m.per_day != null ? String(m.per_day) : "",
      depletion_date: m.depletion_date ?? null,
      pick_ups: (m.pick_ups ?? []).map((p) => ({
        date: p.date ?? "",
        num_pills: p.num_pills != null ? String(p.num_pills) : "",
        next_date: p.next_date ?? null,
      })),
    })),
  };

  const errorSlot = el("div");
  content.append(
    el("a", { class: "back-link", href: "#/" }, [icon("arrow-left", 16), el("span", { text: "Назначения" })])
  );
  content.append(
    el("div", { class: "page-head" }, [
      el("div", { class: "page-head-texts" }, [
        el("h1", { class: "page-title", text: "Редактирование назначения" }),
        el("p", { class: "page-description", text: "Изменения сохраняются при выходе из поля" }),
      ]),
    ])
  );
  content.append(errorSlot);

  /* ---------- field factories ---------- */

  function editableField(label, input, extraClass = "") {
    const errorEl = el("div", { class: "field-error-text", hidden: true });
    const wrap = el("div", { class: "field-input" }, [input]);
    const field = el("div", { class: extraClass ? `field ${extraClass}` : "field" }, [
      el("label", { class: "field-label", text: label }),
      wrap,
      errorEl,
    ]);
    const ref = {
      field,
      input,
      setError(message) {
        errorEl.textContent = message ?? "";
        errorEl.hidden = !message;
        field.classList.toggle("field-error", Boolean(message));
      },
    };
    input.addEventListener("input", () => ref.setError(null));
    return ref;
  }

  function lockedField(label, value, extraClass = "") {
    const valueNode = el("span", { text: value });
    const field = el("div", { class: extraClass ? `field ${extraClass}` : "field" }, [
      el("label", { class: "field-label", text: label }),
      el("div", { class: "field-locked" }, [valueNode, icon("lock-keyhole", 15)]),
    ]);
    return { field, setValue(v) { valueNode.textContent = v; } };
  }

  /* ---------- main prescription card ---------- */

  const startDateInput = el("input", { type: "date", value: draft.start_date });
  const startDateRef = editableField("Дата назначения", startDateInput, "field-grow");
  startDateInput.addEventListener("change", () => {
    draft.start_date = startDateInput.value;
    scheduleSave();
  });

  const lockedEndRef = lockedField("Окончание срока", fmtDate(rx.end_date), "field-grow");
  const lockedNextRef = lockedField("Следующее назначение", fmtDate(rx.next_date), "field-grow");

  content.append(
    el("div", { class: "card edit-fields-card" }, [
      el("h2", { class: "card-title", text: "Данные назначения" }),
      el("div", { class: "edit-main-fields" }, [
        lockedField("ID назначения", String(rx.id), "field-id").field,
        startDateRef.field,
        lockedEndRef.field,
        lockedNextRef.field,
      ]),
      hint("ID не меняется. Даты окончания и следующего назначения рассчитываются автоматически: по самому раннему израсходованию назначенного количества и за 14 дней до окончания."),
    ])
  );

  /* ---------- medicines section ---------- */

  const medsContainer = el("div", { class: "meds-cards" });
  const medsCountNode = el("span", { class: "meds-section-count", text: String(draft.medicines.length) });

  const addMedBtn = el("button", { class: "btn btn-secondary", type: "button" }, [
    icon("plus", 16),
    el("span", { text: "Добавить лекарство" }),
  ]);

  const medsSection = el("div", { class: "meds-section" }, [
    el("div", { class: "meds-section-head" }, [
      el("div", { class: "meds-section-title" }, [el("h2", { text: "Лекарства" }), medsCountNode]),
      addMedBtn,
    ]),
    medsContainer,
    hint("Поля с замком не редактируются. Израсходование полученного лекарства определяется по количеству, суточной дозе и первому получению. Следующее получение — за 7 дней до израсходования."),
  ]);
  content.append(medsSection);

  function updateMedsCount() {
    medsCountNode.textContent = String(draft.medicines.length);
  }

  /* ---------- pick-up row ---------- */

  function renderPickUpRow(med, pickUp) {
    const dateInput = el("input", { type: "date", value: pickUp.date });
    const pillsInput = el("input", { type: "number", min: "1", step: "1", value: pickUp.num_pills, placeholder: "0" });
    const dateRef = editableField("Дата получения", dateInput, "field-date");
    const pillsRef = editableField("Количество таблеток", pillsInput, "field-pills");
    const nextRef = lockedField("Следующее получение", fmtDate(pickUp.next_date ?? null), "field-next");

    dateInput.addEventListener("change", () => {
      pickUp.date = dateInput.value;
      scheduleSave();
    });
    pillsInput.addEventListener("input", () => {
      pickUp.num_pills = pillsInput.value;
    });
    pillsInput.addEventListener("change", () => {
      pickUp.num_pills = pillsInput.value;
      scheduleSave();
    });

    const deleteBtn = el("button", { class: "btn-icon", type: "button", title: "Удалить получение" }, [icon("x", 14)]);
    deleteBtn.addEventListener("click", () => {
      const index = med.pick_ups.indexOf(pickUp);
      if (index !== -1) med.pick_ups.splice(index, 1);
      row.remove();
      scheduleSave();
    });

    const row = el("div", { class: "pickup-edit-row" }, [
      dateRef.field,
      pillsRef.field,
      nextRef.field,
      el("div", { class: "pickup-row-delete" }, [deleteBtn]),
    ]);

    pickUp._refs = { root: row, date: dateRef, pills: pillsRef, next: nextRef };
    return row;
  }

  /* ---------- medicine card ---------- */

  function renderMedCard(med) {
    const titleNode = el("span", { text: med.name || "Новое лекарство" });

    const nameInput = el("input", { type: "text", value: med.name, placeholder: "Название" });
    const numPillsInput = el("input", { type: "number", min: "1", step: "1", value: med.num_pills });
    const perDayInput = el("input", { type: "number", min: "0", step: "any", value: med.per_day });
    const nameRef = editableField("Название лекарства", nameInput, "field-name");
    const numPillsRef = editableField("Всего таблеток", numPillsInput, "field-num");
    const perDayRef = editableField("Таблеток в сутки", perDayInput, "field-num");
    const depletionRef = lockedField("Дата израсходования", fmtDate(med.depletion_date ?? null), "field-depletion");

    nameInput.addEventListener("input", () => {
      med.name = nameInput.value;
      titleNode.textContent = med.name.trim() || "Новое лекарство";
    });
    nameInput.addEventListener("change", () => {
      med.name = nameInput.value;
      scheduleSave();
    });
    numPillsInput.addEventListener("input", () => { med.num_pills = numPillsInput.value; });
    numPillsInput.addEventListener("change", () => { med.num_pills = numPillsInput.value; scheduleSave(); });
    perDayInput.addEventListener("input", () => { med.per_day = perDayInput.value; });
    perDayInput.addEventListener("change", () => { med.per_day = perDayInput.value; scheduleSave(); });

    const pickUpsContainer = el("div", { class: "pickups-rows" });
    for (const pickUp of med.pick_ups) pickUpsContainer.append(renderPickUpRow(med, pickUp));

    const addPickUpBtn = el("button", { class: "btn btn-secondary", type: "button" }, [
      icon("plus", 16),
      el("span", { text: "Добавить получение" }),
    ]);
    addPickUpBtn.addEventListener("click", () => {
      const pickUp = { date: "", num_pills: "" };
      med.pick_ups.push(pickUp);
      pickUpsContainer.append(renderPickUpRow(med, pickUp));
      pickUp._refs.date.input.focus();
    });

    const deleteMedBtn = el("button", { class: "btn btn-danger-text", type: "button", text: "Удалить лекарство" });
    deleteMedBtn.addEventListener("click", () => {
      const index = draft.medicines.indexOf(med);
      if (index !== -1) draft.medicines.splice(index, 1);
      card.remove();
      updateMedsCount();
      scheduleSave();
    });

    const card = el("div", { class: "card med-edit-card" }, [
      el("div", { class: "med-edit-head" }, [
        el("div", { class: "med-edit-title" }, [icon("pill", 18), titleNode]),
        deleteMedBtn,
      ]),
      el("div", { class: "med-params" }, [nameRef.field, numPillsRef.field, perDayRef.field, depletionRef.field]),
      el("hr", { class: "separator" }),
      el("div", { class: "pickups-section" }, [
        el("h3", { class: "pickups-section-title", text: "Получения" }),
        pickUpsContainer,
        addPickUpBtn,
      ]),
    ]);

    med._refs = {
      root: card,
      name: nameRef,
      numPills: numPillsRef,
      perDay: perDayRef,
      depletion: depletionRef,
      titleNode,
    };
    return card;
  }

  for (const med of draft.medicines) medsContainer.append(renderMedCard(med));

  addMedBtn.addEventListener("click", () => {
    const med = { name: "", num_pills: "", per_day: "", pick_ups: [] };
    draft.medicines.push(med);
    medsContainer.append(renderMedCard(med));
    updateMedsCount();
    med._refs.name.input.focus();
  });

  /* ---------- footer ---------- */

  const saveState = el("span", { class: "save-state" });
  const saveBtn = el("button", { class: "btn btn-primary", type: "button", text: "Сохранить" });
  const deleteRxBtn = el("button", { class: "btn btn-danger-text", type: "button", text: "Удалить назначение" });

  content.append(
    el("div", { class: "edit-footer" }, [
      el("div", { class: "form-actions" }, [saveBtn, saveState]),
      deleteRxBtn,
    ])
  );

  deleteRxBtn.addEventListener("click", () => {
    openConfirmDelete({
      prescription: rx,
      onConfirm: async () => {
        try {
          await api.remove(rx.id);
        } catch (error) {
          if (!(error instanceof ApiError && error.status === 404)) throw error;
        }
        navigate("#/");
      },
    });
  });

  /* ---------- validation & autosave ---------- */

  let saveChain = Promise.resolve();
  let lastSavedJson = null;

  function clearAllErrors() {
    startDateRef.setError(null);
    for (const med of draft.medicines) {
      if (!med._refs) continue;
      med._refs.name.setError(null);
      med._refs.numPills.setError(null);
      med._refs.perDay.setError(null);
      for (const pickUp of med.pick_ups) {
        if (!pickUp._refs) continue;
        pickUp._refs.date.setError(null);
        pickUp._refs.pills.setError(null);
      }
    }
  }

  function buildPayload() {
    clearAllErrors();
    let ok = true;

    if (!draft.start_date) {
      startDateRef.setError("Укажите дату назначения.");
      ok = false;
    }

    const medicines = [];
    const medMap = [];

    for (const med of draft.medicines) {
      const name = med.name.trim();
      const npRaw = med.num_pills.trim();
      const pdRaw = med.per_day.trim();
      const hasPickUpData = med.pick_ups.some((p) => p.date || p.num_pills.trim());
      if (!name && !npRaw && !pdRaw && !hasPickUpData) continue;

      if (!name && med._refs) {
        med._refs.name.setError("Введите название лекарства.");
        ok = false;
      }

      let num_pills = null;
      if (npRaw) {
        if (/^\d+$/.test(npRaw) && Number(npRaw) >= 1) num_pills = Number(npRaw);
        else {
          med._refs?.numPills.setError("Целое число не меньше 1.");
          ok = false;
        }
      }

      let per_day = null;
      if (pdRaw) {
        const value = Number(pdRaw.replace(",", "."));
        if (Number.isFinite(value) && value > 0) per_day = value;
        else {
          med._refs?.perDay.setError("Число больше 0.");
          ok = false;
        }
      }

      const pick_ups = [];
      for (const pickUp of med.pick_ups) {
        const pickPillsRaw = pickUp.num_pills.trim();
        if (!pickUp.date && !pickPillsRaw) continue;
        let valid = true;
        if (!pickUp.date) {
          pickUp._refs?.date.setError("Укажите дату получения.");
          valid = false;
        }
        if (!pickPillsRaw) {
          pickUp._refs?.pills.setError("Укажите количество.");
          valid = false;
        } else if (!/^\d+$/.test(pickPillsRaw) || Number(pickPillsRaw) < 1) {
          pickUp._refs?.pills.setError("Целое число не меньше 1.");
          valid = false;
        }
        if (!valid) ok = false;
        else pick_ups.push({ date: pickUp.date, num_pills: Number(pickPillsRaw) });
      }

      medicines.push({ name, num_pills, per_day, pick_ups });
      medMap.push(med);
    }

    return { ok, payload: { start_date: draft.start_date, medicines }, medMap };
  }

  function applyServerState(updated, medMap) {
    rx = updated;
    lockedEndRef.setValue(fmtDate(updated.end_date));
    lockedNextRef.setValue(fmtDate(updated.next_date));

    (updated.medicines ?? []).forEach((serverMed, i) => {
      const med = medMap[i];
      if (!med || !med._refs) return;
      med._refs.depletion.setValue(fmtDate(serverMed.depletion_date ?? null));

      const nextQueues = new Map();
      for (const serverPickUp of serverMed.pick_ups ?? []) {
        const key = `${serverPickUp.date}|${serverPickUp.num_pills}`;
        if (!nextQueues.has(key)) nextQueues.set(key, []);
        nextQueues.get(key).push(serverPickUp.next_date ?? null);
      }
      for (const pickUp of med.pick_ups) {
        if (!pickUp._refs) continue;
        const key = `${pickUp.date}|${Number(pickUp.num_pills)}`;
        const queue = nextQueues.get(key);
        const nextDate = queue && queue.length ? queue.shift() : null;
        pickUp._refs.next.setValue(fmtDate(nextDate));
      }
    });
  }

  async function doSave() {
    const built = buildPayload();
    if (!built.ok) {
      replaceBanner(errorSlot, "Проверьте выделенные поля: изменения не сохранены.");
      saveState.textContent = "";
      return;
    }
    const json = JSON.stringify(built.payload);
    if (json === lastSavedJson) {
      replaceBanner(errorSlot, null);
      return;
    }

    saveState.textContent = "Сохранение…";
    try {
      const updated = await api.update(rx.id, built.payload);
      lastSavedJson = json;
      applyServerState(updated, built.medMap);
      replaceBanner(errorSlot, null);
      saveState.textContent = "Сохранено";
    } catch (error) {
      saveState.textContent = "";
      if (error instanceof ApiError && error.status === 404) {
        replaceBanner(errorSlot, `Назначение №${rx.id} не найдено. Возврат к списку…`);
        setTimeout(() => navigate("#/"), 1500);
        return;
      }
      replaceBanner(errorSlot, error.message || "Не удалось сохранить изменения");
    }
  }

  function scheduleSave() {
    saveChain = saveChain.then(doSave).catch(() => {});
  }

  saveBtn.addEventListener("click", () => {
    const built = buildPayload();
    if (!built.ok) {
      replaceBanner(errorSlot, "Исправьте ошибки в выделенных полях — изменения не сохранены.");
      return;
    }
    replaceBanner(errorSlot, null);
    scheduleSave();
    saveChain = saveChain.then(() => {
      setExpandTarget(rx.id);
      navigate("#/");
    });
  });

  const initial = buildPayload();
  if (initial.ok) lastSavedJson = JSON.stringify(initial.payload);
}
