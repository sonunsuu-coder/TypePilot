(function () {
  "use strict";

  const languageTypes = {
    Gail: "gail_practice",
    Raavi: "raavi_practice",
    Inscript: "inscript_practice",
    Marathi: "marathi_practice",
    Bamini: "bamini_practice",
    "Mcl Bharathi": "bamini_practice",
    English: "eng_practice",
    Asees: "asees_practice",
    KrutiDev: "kruti_practice",
  };
  const durations = [1, 2, 3, 5, 10, 15, 20, 30];

  function getPracticeTable() {
    return [...document.querySelectorAll(".el-table")].find((table) => {
      const row = table.querySelector(".el-table__body tr");
      return row && row.querySelectorAll("td").length >= 5 && row.querySelector(".el-button");
    });
  }

  function getLanguage() {
    const known = Object.keys(languageTypes);
    const heading = [...document.querySelectorAll("h1,h2,h3,h4")]
      .map((el) => el.innerText.trim())
      .find((text) => known.includes(text));
    return heading || "Gail";
  }

  function makeButton(text, className, onClick) {
    const button = document.createElement("button");
    button.type = "button";
    button.className = `tp-lesson-button ${className}`;
    button.textContent = text;
    button.addEventListener("click", onClick);
    return button;
  }

  function addToolbar(table) {
    if (table.querySelector(":scope > .tp-lesson-toolbar")) return;
    const toolbar = document.createElement("div");
    toolbar.className = "tp-lesson-toolbar";
    const titleGroup = document.createElement("div");
    titleGroup.className = "tp-lesson-title-group";
    const title = document.createElement("strong");
    title.textContent = "▤  Practice Lessons";
    const badge = document.createElement("span");
    badge.className = "tp-lesson-language";
    badge.textContent = getLanguage().toUpperCase();
    titleGroup.append(title, badge);
    toolbar.append(titleGroup, makeButton("＋  Add Lesson", "tp-add-button", () => openEditor()));
    table.prepend(toolbar);
  }

  function tuneHeaders(table) {
    const headers = table.querySelectorAll(".el-table__header-wrapper thead th");
    const labels = ["#", "Description", "Lesson Preview", "Duration"];
    labels.forEach((label, index) => {
      const cell = headers[index]?.querySelector(".cell");
      if (cell && cell.textContent !== label) cell.textContent = label;
    });
    const headerRow = table.querySelector(".el-table__header-wrapper thead tr");
    if (headerRow && headers.length < 5) {
      const th = document.createElement("th");
      th.className = "tp-actions-header";
      th.innerHTML = '<div class="cell">Actions</div>';
      headerRow.append(th);
    } else if (headers[4]?.querySelector(".cell")) {
      const cell = headers[4].querySelector(".cell");
      if (cell.textContent !== "Actions") cell.textContent = "Actions";
    }
    // Give the description enough room for a single-line heading and keep
    // the preview as the flexible, widest column.
    const columnWidths = ["6%", "14%", "50%", "14%", "16%"];
    table.querySelectorAll("colgroup").forEach((group) => {
      [...group.children].forEach((column, index) => {
        if (columnWidths[index]) column.style.width = columnWidths[index];
      });
    });
  }

  function enhanceRows(table) {
    table.querySelectorAll(".el-table__body tr").forEach((row) => {
      const cells = row.querySelectorAll("td");
      if (cells.length < 5) return;
      const lessonId = cells[0].innerText.trim();
      const description = cells[1].innerText.trim();
      const preview = cells[2].textContent.trim();
      const fullText = cells[2].textContent.trim();
      cells[0].classList.add("tp-id-cell");
      cells[2].title = fullText;
      const actions = cells[cells.length - 1].querySelector(".cell");
      if (!actions || actions.dataset.tpActionsReady) return;
      actions.dataset.tpActionsReady = "true";
      actions.classList.add("tp-actions-cell");
      const run = actions.querySelector(".el-button");
      if (run) run.classList.add("tp-run-button");
    const edit = makeButton("✎  Edit", "tp-edit-button", () => openEditor({
        lesson_id: lessonId,
        lesson_desc: description,
        lesson_data: fullText,
        duration: cells[3].querySelector("input")?.value || "05:00 Mins",
      }));
      edit.title = `Edit ${description}`;
      actions.append(edit);
    });
  }

  function field(labelText, element) {
    const wrapper = document.createElement("label");
    wrapper.className = "tp-form-field";
    const label = document.createElement("span");
    label.textContent = labelText;
    wrapper.append(label, element);
    return wrapper;
  }

  function openEditor(record = {}) {
    document.querySelector(".tp-modal-backdrop")?.remove();
    const backdrop = document.createElement("div");
    backdrop.className = "tp-modal-backdrop";
    const dialog = document.createElement("form");
    dialog.className = "tp-lesson-dialog";
    const heading = document.createElement("h2");
    heading.textContent = record.lesson_id ? "Edit Lesson" : "Add Lesson";
    const helper = document.createElement("p");
    helper.textContent = `Practice lesson for ${getLanguage()}`;
    const description = document.createElement("input");
    description.required = true;
    description.maxLength = 160;
    description.placeholder = "Example: Lesson 1";
    description.value = record.lesson_desc || "";
    const data = document.createElement("textarea");
    data.required = true;
    data.rows = 10;
    data.placeholder = "Paste lesson text here";
    data.value = record.lesson_data || "";
    const duration = document.createElement("select");
    durations.forEach((minutes) => {
      const option = document.createElement("option");
      option.value = `${String(minutes).padStart(2, "0")}:00 Mins`;
      option.textContent = option.value;
      duration.append(option);
    });
    duration.value = durations.some((n) => duration.options && [...duration.options].some((o) => o.value === record.duration))
      ? record.duration : "05:00 Mins";

    const actions = document.createElement("div");
    actions.className = "tp-modal-actions";
    const cancel = makeButton("Cancel", "tp-cancel-button", () => backdrop.remove());
    cancel.type = "button";
    const save = document.createElement("button");
    save.type = "submit";
    save.className = "tp-lesson-button tp-save-button";
    save.textContent = record.lesson_id ? "Save Changes" : "Add Lesson";
    actions.append(cancel, save);
    const status = document.createElement("div");
    status.className = "tp-form-status";
    dialog.append(heading, helper,
      field("Description", description),
      field("Lesson Text", data),
      field("Duration", duration), status, actions);
    backdrop.append(dialog);
    backdrop.addEventListener("click", (event) => {
      if (event.target === backdrop) backdrop.remove();
    });
    dialog.addEventListener("submit", async (event) => {
      event.preventDefault();
      save.disabled = true;
      status.textContent = "Saving lesson…";
      try {
        const response = await fetch("/api/savelesson", {
          method: "POST",
          headers: { "Content-Type": "application/json" },
          body: JSON.stringify({
            lesson_id: record.lesson_id || "",
            lesson_type: languageTypes[getLanguage()] || "gail_practice",
            lesson_desc: description.value,
            lesson_data: data.value,
            duration: duration.value,
          }),
        });
        const result = await response.json();
        if (!response.ok) throw new Error(result.error || "Could not save this lesson.");
        status.textContent = "Saved. Reloading lessons…";
        // Replace the current document so Vue re-fetches lesson rows and the
        // just-saved text is visible in both the list and Tutor view.
        const refreshUrl = new URL(window.location.href);
        refreshUrl.searchParams.set("_lesson_refresh", String(Date.now()));
        window.location.replace(refreshUrl.href);
      } catch (error) {
        status.textContent = error.message;
        save.disabled = false;
      }
    });
    document.body.append(backdrop);
    description.focus();
  }

  function refresh() {
    const table = getPracticeTable();
    if (!table) return;
    addToolbar(table);
    tuneHeaders(table);
    enhanceRows(table);
  }

  new MutationObserver(refresh).observe(document.getElementById("app") || document.body, {
    childList: true,
    subtree: true,
  });
  refresh();
})();
