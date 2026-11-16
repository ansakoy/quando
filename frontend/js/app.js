import { fmtLongDate } from "./format.js";
import { parseRoute } from "./router.js";
import { renderListView } from "./views/list.js";
import { renderAddView } from "./views/add.js";
import { renderEditView } from "./views/edit.js";

document.getElementById("today-date").textContent = fmtLongDate();

const app = document.getElementById("app");

async function render() {
  const route = parseRoute();
  app.textContent = "";
  window.scrollTo(0, 0);
  if (route.name === "add") {
    await renderAddView(app);
  } else if (route.name === "edit") {
    await renderEditView(app, route.id);
  } else {
    await renderListView(app);
  }
}

window.addEventListener("hashchange", render);
render();
