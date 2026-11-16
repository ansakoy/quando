import { api } from "../api.js";
import { fmtDate, fmtPerDay } from "../format.js";
import { consumeExpandTarget } from "../router.js";
import { el, icon, hint, errorBanner } from "../ui.js";

function medAccordion(med) {
  const body = el("div", { class: "med-body" });

  const summaryRow = el("div", { class: "med-summary-row" });
  summaryRow.append(
    el("div", {
      class: "med-summary",
      text: `Назначено таблеток: ${med.num_pills ?? "—"}, по ${fmtPerDay(med.per_day)} в день`,
    })
  );
  if (med.next_pick_up_date) {
    summaryRow.append(
      el("div", { class: "next-pickup-plaque" }, [
        icon("calendar-clock", 16),
        el("span", { text: `Желательно получить еще к ${fmtDate(med.next_pick_up_date)}` }),
      ])
    );
  }
  body.append(summaryRow);

  const pickUps = med.pick_ups ?? [];
  const pickUpsList = el("div", { class: "pickups-list" }, [
    el("div", { class: "pickups-title", text: "Получено:" }),
  ]);
  if (pickUps.length === 0) {
    pickUpsList.append(el("div", { class: "empty-note", text: "Получений пока нет." }));
  } else {
    for (const pickUp of pickUps) {
      pickUpsList.append(
        el("div", { class: "pickup-line" }, [
          el("span", { class: "pickup-marker" }),
          el("span", { text: `${fmtDate(pickUp.date)}: ${pickUp.num_pills}` }),
        ])
      );
    }
  }
  body.append(pickUpsList);

  const head = el("button", { class: "med-head", type: "button" });
  const chevron = icon("chevron-down", 18, "");
  chevron.classList.add("med-head-chevron");
  head.append(
    el("div", { class: "med-icon" }, [icon("pill", 17)]),
    el("div", {
      class: "med-head-title",
      text: `${med.name}: до ${med.depletion_date ? fmtDate(med.depletion_date) : "—"}`,
    }),
    chevron
  );

  const item = el("div", { class: "med-item" }, [head, body]);
  head.addEventListener("click", () => item.classList.toggle("open"));
  return item;
}

function rxAccordion(rx) {
  const head = el("button", { class: "rx-head", type: "button" }, [
    icon("chevron-down", 20, ""),
    el("div", { class: "rx-head-title", text: `Назначение от ${fmtDate(rx.start_date)}` }),
    el("div", { class: "rx-badge", text: `№ ${rx.id}` }),
  ]);
  head.querySelector("img").classList.add("rx-head-chevron");

  function dateBlock(label, value, accent = false) {
    return el("div", { class: accent ? "rx-date rx-date-accent" : "rx-date" }, [
      el("div", { class: "rx-date-label", text: label }),
      el("div", { class: "rx-date-value", text: fmtDate(value) }),
    ]);
  }

  const datesRow = el("div", { class: "rx-dates-row" }, [
    dateBlock("Назначение", rx.start_date),
    dateBlock("Окончание срока", rx.end_date),
    dateBlock("Следующее назначение", rx.next_date, true),
    el("a", { class: "btn btn-secondary rx-edit-btn", href: `#/edit/${rx.id}` }, [
      icon("pencil", 16),
      el("span", { text: "Редактировать" }),
    ]),
  ]);

  const meds = rx.medicines ?? [];
  const medsSection = el("div", { class: "rx-meds" }, [
    el("div", { class: "rx-meds-head" }, [
      el("div", { class: "rx-meds-title", text: "Лекарства" }),
      el("div", { class: "rx-meds-count", text: String(meds.length) }),
    ]),
  ]);
  if (meds.length === 0) {
    medsSection.append(el("div", { class: "empty-note", text: "Лекарств пока нет." }));
  } else {
    for (const med of meds) medsSection.append(medAccordion(med));
  }

  const body = el("div", { class: "rx-body" }, [
    datesRow,
    el("hr", { class: "separator" }),
    medsSection,
  ]);

  const card = el("div", { class: "card rx-card", id: `rx-${rx.id}` }, [head, body]);
  head.addEventListener("click", () => card.classList.toggle("open"));
  return card;
}

export async function renderListView(container) {
  const content = el("div", { class: "content" });
  container.append(content);

  content.append(
    el("div", { class: "page-head" }, [
      el("div", { class: "page-head-texts" }, [
        el("h1", { class: "page-title", text: "Назначения" }),
      ]),
      el("a", { class: "btn btn-primary", href: "#/new" }, [
        icon("plus-white", 16),
        el("span", { text: "Добавить назначение" }),
      ]),
    ])
  );

  let prescriptions;
  try {
    prescriptions = await api.list();
  } catch (error) {
    content.append(errorBanner(error.message || "Не удалось загрузить список назначений"));
    return;
  }

  const expandTarget = consumeExpandTarget();
  const expandId = expandTarget ?? prescriptions[0]?.id ?? null;

  if (prescriptions.length === 0) {
    content.append(
      el("div", { class: "card card-padded empty-note", text: "Назначений пока нет. Нажмите «Добавить назначение», чтобы создать первое." })
    );
  } else {
    for (const rx of prescriptions) {
      const card = rxAccordion(rx);
      if (rx.id === expandId) card.classList.add("open");
      content.append(card);
    }
  }

  content.append(hint("Сроки рассчитываются автоматически. Раскройте лекарство, чтобы посмотреть получения."));

  if (expandTarget !== null) {
    const target = document.getElementById(`rx-${expandTarget}`);
    if (target) target.scrollIntoView({ behavior: "smooth", block: "start" });
  }
}
