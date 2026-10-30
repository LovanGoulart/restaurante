"use strict";
window.ProductPicker = (() => {
  const node = document.querySelector("#product-catalog-data");
  if (!node) return;
  const products = new Map(JSON.parse(node.textContent).map((p) => [p.id, p]));
  const dialog = document.querySelector("#product-picker");
  const form = document.querySelector("#picker-form");
  const groups = document.querySelector("#picker-groups");
  const notes = document.querySelector("#picker-note");
  const error = document.querySelector("#picker-error");
  let current,
    quantity = 1,
    callback,
    previous,
    adapter;
  const safe = escapeHTML;
  const normal = (s) =>
    String(s)
      .normalize("NFD")
      .replace(/[\u0300-\u036f]/g, "")
      .toLocaleLowerCase("pt-BR");
  function read() {
    const selections = {};
    for (const g of current.groups) {
      const field = groups.querySelector(`[data-group="${g.id}"]`);
      selections[g.id] =
        g.type === "text"
          ? field.querySelector("input").value.trim()
          : [...field.querySelectorAll("input:checked")].map((i) => i.value);
    }
    return selections;
  }
  function price(product, selected) {
    return (
      product.preco +
      product.groups.reduce(
        (sum, g) =>
          sum +
          (g.type === "text"
            ? 0
            : g.choices
                .filter((c) => (selected[g.id] || []).includes(c.id))
                .reduce((n, c) => n + c.price, 0)),
        0,
      )
    );
  }
  function summary(product, selected) {
    return product.groups
      .map((g) => {
        const v = selected[g.id];
        const text =
          g.type === "text"
            ? v
            : g.choices
                .filter((c) => (v || []).includes(c.id))
                .map((c) => c.label)
                .join(", ");
        return text ? g.title + ": " + text : "";
      })
      .filter(Boolean)
      .join(" | ");
  }
  function choicePrice(group, choice) {
    // Nos tamanhos, mostra o preço da pizza (base + acréscimo do tamanho).
    // Bordas e outros complementos continuam mostrando seu próprio acréscimo.
    const isSize = /tamanho|fatias/.test(normal(group.title));
    if (isSize) return `<small>${money(current.preco + choice.price)}</small>`;
    return choice.price ? `<small>+ ${money(choice.price)}</small>` : "";
  }
  function update() {
    const selected = read();
    document.querySelector("#picker-quantity").textContent = quantity;
    document.querySelector("#picker-unit-price").textContent = money(
      price(current, selected),
    );
    document.querySelector("#picker-total").textContent = money(
      price(current, selected) * quantity,
    );
    document.querySelector("#picker-minus").disabled = quantity === 1;
    document.querySelector("#picker-plus").disabled = quantity === 99;
    for (const g of current.groups) {
      const field = groups.querySelector(`[data-group="${g.id}"]`);
      if (g.type !== "text")
        field.querySelector(".picker-count").textContent =
          `${selected[g.id].length} / ${g.max}`;
    }
  }
  function open(id, item, done) {
    if (!adapter.canEdit()) return;
    current = products.get(id);
    if (!current) return;
    callback = done;
    previous = document.activeElement;
    quantity = item?.quantidade || 1;
    document.querySelector("#picker-name").textContent = current.nome;
    document.querySelector("#picker-description").textContent =
      current.descricao;
    const photo = document.querySelector(`[data-product="${id}"] .food`);
    document
      .querySelector("#picker-photo")
      .replaceChildren(
        ...[...(photo?.childNodes || [])].map((n) => n.cloneNode(true)),
      );
    groups.innerHTML = current.groups
      .map(
        (g) =>
          `<fieldset class="picker-group" data-group="${g.id}"><legend>${safe(g.title)} <span class="picker-count">${g.type === "text" ? "Texto" : "0 / " + g.max}</span></legend><small>${g.required ? "Obrigatório" : "Opcional"}${g.type === "multiple" ? " · Até " + g.max + " escolhas" : ""}</small>${g.type === "text" ? `<input type="text" maxlength="60" aria-label="${safe(g.title)}" ${g.required ? "required" : ""}>` : g.choices.map((c) => `<label class="picker-choice"><span>${safe(c.label)}${choicePrice(g, c)}</span><input type="${g.type === "single" ? "radio" : "checkbox"}" name="${g.id}" value="${c.id}"></label>`).join("") + (!g.required && g.type === "single" ? `<button type="button" class="picker-clear" data-clear="${g.id}">Limpar escolha</button>` : "")}</fieldset>`,
      )
      .join("");
    for (const g of current.groups) {
      const field = groups.querySelector(`[data-group="${g.id}"]`);
      const value = item?.opcoes?.[g.id];
      if (g.type === "text")
        field.querySelector("input").value =
          typeof value === "string" ? value : "";
      else
        field.querySelectorAll("input").forEach((i) => {
          i.checked = Array.isArray(value) && value.includes(i.value);
        });
    }
    document.querySelector("#picker-note-label").hidden =
      !current.notes.enabled;
    document.querySelector("#picker-note-title").textContent =
      current.notes.label;
    notes.placeholder = current.notes.placeholder;
    notes.value = current.notes.enabled ? item?.observacao || "" : "";
    error.hidden = true;
    document.querySelector("#picker-submit").firstChild.textContent = item
      ? "Salvar · "
      : "Adicionar · ";
    update();
    document.body.classList.add("product-picker-open");
    dialog.showModal();
  }
  dialog.addEventListener("close", () => {
    document.body.classList.remove("product-picker-open");
    previous?.focus();
  });
  document.querySelector("#picker-close").onclick = () => dialog.close();
  document.querySelector("#picker-minus").onclick = () => {
    quantity = Math.max(1, quantity - 1);
    update();
  };
  document.querySelector("#picker-plus").onclick = () => {
    quantity = Math.min(99, quantity + 1);
    update();
  };
  groups.addEventListener("change", (e) => {
    const field = e.target.closest("[data-group]");
    const g = current.groups.find((g) => g.id === field.dataset.group);
    if (
      g.type === "multiple" &&
      field.querySelectorAll("input:checked").length > g.max
    ) {
      e.target.checked = false;
      error.textContent = `Escolha no máximo ${g.max} em ${g.title}.`;
      error.hidden = false;
    } else error.hidden = true;
    update();
  });
  groups.addEventListener("click", (e) => {
    const b = e.target.closest("[data-clear]");
    if (b) {
      b.closest("fieldset")
        .querySelectorAll("input")
        .forEach((i) => (i.checked = false));
      update();
    }
  });
  form.addEventListener("submit", (e) => {
    e.preventDefault();
    if (!adapter.canEdit()) return;
    const selected = read();
    for (const g of current.groups) {
      if (g.required && !selected[g.id].length) {
        error.textContent = "Preencha " + g.title + ".";
        error.hidden = false;
        groups.querySelector(`[data-group="${g.id}"] input`).focus();
        return;
      }
    }
    const details = summary(current, selected),
      note = current.notes.enabled ? notes.value.trim() : "";
    const stored = [
      details,
      note
        ? (details || current.notes.label !== "Observação"
            ? current.notes.label + ": "
            : "") + note
        : "",
    ]
      .filter(Boolean)
      .join(" | ");
    if (stored.length > 300) {
      error.textContent =
        "Resuma os textos: opções e observações podem somar até 300 caracteres.";
      error.hidden = false;
      return;
    }
    callback({
      id: current.id,
      nome: current.nome,
      preco: price(current, selected),
      quantidade: quantity,
      observacao: note,
      opcoes: selected,
      opcoes_versao: current.version,
      resumo: details,
    });
    dialog.close();
  });
  function restore(item) {
    const p = products.get(item.id);
    if (
      !p ||
      !Number.isInteger(item.quantidade) ||
      item.quantidade < 1 ||
      item.quantidade > 99
    )
      return null;
    if (p.groups.length && item.opcoes_versao !== p.version) return null;
    const selected = item.opcoes || {};
    if (
      typeof selected !== "object" ||
      Array.isArray(selected) ||
      Object.keys(selected).some((id) => !p.groups.some((g) => g.id === id))
    )
      return null;
    for (const g of p.groups) {
      const value = selected[g.id];
      if (g.type === "text") {
        if (
          typeof value !== "string" ||
          value.length > 60 ||
          (g.required && !value.trim())
        )
          return null;
      } else if (
        !Array.isArray(value) ||
        value.length > g.max ||
        new Set(value).size !== value.length ||
        (g.required && !value.length) ||
        value.some((id) => !g.choices.some((c) => c.id === id))
      )
        return null;
    }
    return {
      ...item,
      nome: p.nome,
      preco: price(p, selected),
      opcoes: selected,
      opcoes_versao: p.version,
      observacao: p.notes.enabled
        ? String(item.observacao || "").slice(0, 300)
        : "",
      resumo: summary(p, selected),
    };
  }
  function bind(value) {
    adapter = value;
    document.querySelectorAll("[data-product]").forEach((card) => {
      card.onclick = () => open(+card.dataset.product, null, value.onAdd);
      card.onkeydown = (e) => {
        if (e.target === card && ["Enter", " "].includes(e.key)) {
          e.preventDefault();
          open(+card.dataset.product, null, value.onAdd);
        }
      };
    });
    let category = "all";
    const filter = () => {
      const q = normal(document.querySelector("#search").value.trim());
      let count = 0;
      document.querySelectorAll("[data-product]").forEach((p) => {
        p.hidden =
          (category !== "all" && category !== p.dataset.category) ||
          !normal(p.dataset.name).includes(q);
        if (!p.hidden) count++;
      });
      document
        .querySelectorAll("[data-category-section]")
        .forEach(
          (s) =>
            (s.hidden = ![...s.querySelectorAll("[data-product]")].some(
              (p) => !p.hidden,
            )),
        );
      document.querySelector("#empty-search").hidden = count > 0;
    };
    document.querySelector("#search").oninput = filter;
    document.querySelectorAll(".catalog-chips .chip").forEach((button) => {
      button.onclick = () => {
        category = button.dataset.category;
        document.querySelectorAll(".catalog-chips .chip").forEach((chip) => {
          chip.classList.toggle("active", chip === button);
          chip.setAttribute("aria-pressed", String(chip === button));
        });
        filter();
      };
    });
  }
  function line(i, k) {
    return `<div class="cart-item"><b>${safe(i.nome)}</b>${i.resumo ? `<p class="cart-options-summary">${safe(i.resumo)}</p>` : ""}${i.observacao ? `<p class="cart-options-summary">${safe(products.get(i.id)?.notes.label || "Observação")}: ${safe(i.observacao)}</p>` : ""}<div class="quantity"><button data-change="-1" data-index="${k}" aria-label="Diminuir ${safe(i.nome)}">−</button><span>${i.quantidade}</span><button data-change="1" data-index="${k}" aria-label="Aumentar ${safe(i.nome)}">+</button><strong>${money(i.preco * i.quantidade)}</strong></div><button type="button" class="cart-edit-options" data-edit="${k}">Editar opções e observação</button></div>`;
  }
  return { bind, restore, line, edit: (i, done) => open(i.id, i, done) };
})();
