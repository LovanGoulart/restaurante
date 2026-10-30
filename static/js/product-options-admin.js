"use strict";
(() => {
  const form = document.querySelector("#options-config"),
    container = document.querySelector("#options-groups");
  const data = JSON.parse(
    document.querySelector("#options-config-data").textContent,
  );
  let version = data.version,
    saving = false;
  const groups = data.config.groups;
  const message = document.querySelector("#options-message");
  const uid = () => crypto.randomUUID().replaceAll("-", "");
  const check = (value) => (value ? "checked" : "");
  const safe = escapeHTML;
  const choice = (label = "Nova escolha") => ({
    id: uid(),
    label,
    price: 0,
    enabled: true,
  });
  const group = (title, labels) => ({
    id: uid(),
    title,
    enabled: true,
    required: true,
    type: "single",
    max: 1,
    choices: labels.map(choice),
  });
  groups.forEach((g) =>
    g.choices.forEach(
      (c) => (c.amount = (c.price / 100).toFixed(2).replace(".", ",")),
    ),
  );
  document.querySelector("#notes-enabled").checked = data.config.notes.enabled;
  document.querySelector("#notes-label").value = data.config.notes.label;
  document.querySelector("#notes-placeholder").value =
    data.config.notes.placeholder;
  function show(text, failure = false) {
    message.textContent = text;
    message.hidden = false;
    message.className = failure ? "error" : "success";
  }
  function render() {
    container.innerHTML =
      groups
        .map(
          (g, index) =>
            `<fieldset class="options-group-editor" data-group="${g.id}"><legend>Grupo ${index + 1}</legend><div class="options-group-heading"><label>Título do grupo<input data-field="title" value="${safe(g.title)}" maxlength="48" required></label><button type="button" class="secondary" data-remove-group="${g.id}">Remover grupo</button></div><div class="options-settings"><label class="check"><input type="checkbox" data-field="enabled" ${check(g.enabled)}> Exibir este grupo</label><label class="check"><input type="checkbox" data-field="required" ${check(g.required)}> Preenchimento obrigatório</label><label>Tipo de opção<select data-field="type">${[
              ["single", "Uma escolha"],
              ["multiple", "Várias escolhas"],
              ["text", "Texto curto"],
            ]
              .map(
                ([v, t]) =>
                  `<option value="${v}" ${g.type === v ? "selected" : ""}>${t}</option>`,
              )
              .join(
                "",
              )}</select></label>${g.type === "multiple" ? `<label>Máximo de escolhas<input type="number" data-field="max" min="1" max="20" value="${g.max}" required></label>` : ""}</div>${g.type === "text" ? '<p class="muted">Campo de texto com até 60 caracteres. Não altera o preço.</p>' : `<p class="muted">Acréscimo por unidade. Use 0,00 para uma escolha sem custo adicional.</p><div class="options-choice-list">${g.choices.map((c) => `<div class="options-choice-editor" data-choice="${c.id}"><label>Escolha<input data-choice-field="label" value="${safe(c.label)}" maxlength="60" required></label><label>Acréscimo (R$)<input data-choice-field="amount" inputmode="decimal" value="${safe(c.amount ?? "0,00")}" placeholder="0,00" required></label><label class="check"><input data-choice-field="enabled" type="checkbox" ${check(c.enabled)}> Exibir</label><button type="button" class="secondary" data-remove-choice="${c.id}" aria-label="Remover escolha">×</button></div>`).join("")}</div><button type="button" class="secondary" data-add-choice="${g.id}">+ Adicionar escolha</button>`}</fieldset>`,
        )
        .join("") ||
      '<p class="empty">Nenhum grupo configurado. O produto poderá ser adicionado com sua observação livre, se permitida.</p>';
  }
  container.addEventListener("input", (e) => {
    const field = e.target,
      g = groups.find(
        (g) => g.id === field.closest("[data-group]")?.dataset.group,
      );
    if (!g) return;
    const value =
      field.type === "checkbox"
        ? field.checked
        : field.type === "number"
          ? Number(field.value)
          : field.value;
    if (field.dataset.field) g[field.dataset.field] = value;
    if (field.dataset.choiceField) {
      const c = g.choices.find(
        (c) => c.id === field.closest("[data-choice]").dataset.choice,
      );
      c[field.dataset.choiceField] = value;
    }
  });
  container.addEventListener("change", (e) => {
    if (e.target.dataset.field === "type") {
      const g = groups.find(
        (g) => g.id === e.target.closest("[data-group]").dataset.group,
      );
      g.type = e.target.value;
      if (g.type !== "text" && !g.choices.length) g.choices.push(choice());
      render();
    }
  });
  container.addEventListener("click", (e) => {
    const b = e.target.closest("button");
    if (!b || saving) return;
    const gid = b.closest("[data-group]")?.dataset.group,
      g = groups.find((g) => g.id === gid);
    if (b.dataset.removeGroup) groups.splice(groups.indexOf(g), 1);
    if (b.dataset.addChoice) {
      if (g.choices.length >= 20) {
        show("Use até vinte escolhas no grupo.", true);
        return;
      }
      g.choices.push(choice());
    }
    if (b.dataset.removeChoice)
      g.choices = g.choices.filter((c) => c.id !== b.dataset.removeChoice);
    render();
  });
  document.querySelectorAll("[data-preset]").forEach(
    (b) =>
      (b.onclick = () => {
        if (saving) return;
        if (groups.length >= 8) {
          show("Use até oito grupos por produto.", true);
          return;
        }
        const presets = {
          pizza: () =>
            group("Tamanho e fatias", [
              "Broto · 4 fatias",
              "Média · 8 fatias",
              "Grande · 12 fatias",
            ]),
          border: () => group("Borda", ["Sem borda", "Requeijão", "Chocolate"]),
          meat: () =>
            group("Ponto da carne", ["Mal passado", "Ao ponto", "Bem passado"]),
          custom: () => group("Personalize o título", ["Primeira escolha"]),
        };
        groups.push(presets[b.dataset.preset]());
        render();
      }),
  );
  form.addEventListener("submit", async (e) => {
    e.preventDefault();
    if (saving) return;
    let payload;
    try {
      payload = {
        version,
        notes: {
          enabled: document.querySelector("#notes-enabled").checked,
          label: document.querySelector("#notes-label").value.trim(),
          placeholder: document
            .querySelector("#notes-placeholder")
            .value.trim(),
        },
        groups: groups.map((g) => ({
          ...g,
          choices:
            g.type === "text"
              ? []
              : g.choices.map((c) => {
                  const amount = String(c.amount ?? "0,00").trim();
                  if (!/^\d{1,6}(?:,\d{1,2})?$/.test(amount))
                    throw Error(
                      "Use valores como 0,00 ou 5,50, sem ponto de milhar.",
                    );
                  const [whole, fraction = ""] = amount.split(",");
                  return {
                    id: c.id,
                    label: c.label,
                    enabled: c.enabled,
                    price:
                      Number(whole) * 100 + Number(fraction.padEnd(2, "0")),
                  };
                }),
        })),
      };
    } catch (e) {
      show(e.message, true);
      return;
    }
    saving = true;
    form
      .querySelectorAll("input,select,button")
      .forEach((el) => (el.disabled = true));
    try {
      const response = await api(form.dataset.url, payload);
      version = response.version;
      show("Opções salvas. Elas já estão disponíveis no cardápio e no PDV.");
    } catch (e) {
      show(
        e.message +
          " Se a liberação da área expirou, volte a Produtos e confirme sua senha.",
        true,
      );
    } finally {
      saving = false;
      form
        .querySelectorAll("input,select,button")
        .forEach((el) => (el.disabled = false));
    }
  });
  render();
})();
