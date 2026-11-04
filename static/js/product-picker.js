"use strict";
window.ProductPicker = (() => {
  const node = document.querySelector("#product-catalog-data");
  if (!node) return;
  const products = new Map(JSON.parse(node.textContent).map((p) => [p.id, p]));
  const dialog = document.querySelector("#product-picker"),
    form = document.querySelector("#picker-form"),
    groups = document.querySelector("#picker-groups"),
    notes = document.querySelector("#picker-note"),
    error = document.querySelector("#picker-error"),
    search = document.querySelector("#picker-choice-search"),
    dots = document.querySelector("#pizza-step-dots");
  let current,
    adapter,
    callback,
    previous,
    pizza,
    editing,
    quantity = 1,
    units = [],
    unitIndex = 0,
    stepIndex = 0,
    steps = [];
  form.noValidate = true;
  const safe = escapeHTML;
  const normal = (text) =>
    String(text)
      .normalize("NFD")
      .replace(/[\u0300-\u036f]/g, "")
      .toLocaleLowerCase("pt-BR");
  const pizzaGroups = (product) => {
    const sizes = product?.groups.find((g) => g.type === "sizes"),
      flavors = product?.groups.find((g) => g.type === "flavors");
    return sizes && flavors ? { sizes, flavors } : null;
  };
  const unitNav = document.createElement("div");
  unitNav.id = "pizza-unit-nav";
  unitNav.className = "chips";
  unitNav.hidden = true;
  unitNav.setAttribute("aria-label", "Escolher pizza para personalizar");
  dots.after(unitNav);
  function read() {
    return Object.fromEntries(
      current.groups.map((g) => {
        const field = groups.querySelector(`[data-group="${g.id}"]`);
        return [
          g.id,
          g.type === "text"
            ? field.querySelector("input").value.trim()
            : [...field.querySelectorAll("input:checked")].map((i) => i.value),
        ];
      }),
    );
  }
  function price(product, selected) {
    let base = product.preco,
      extra = 0;
    for (const g of product.groups) {
      if (g.type === "text") continue;
      const chosen = g.choices.filter((c) =>
        (selected[g.id] || []).includes(c.id),
      );
      if (g.type === "flavors") {
        const sum = chosen.reduce((n, c) => n + c.price, 0),
          count = chosen.length;
        base = product.pricing_mode === "fixed" ? 0 : count
          ? Math.floor((2 * sum + count) / (2 * count))
          : Math.min(...g.choices.map((c) => c.price));
      } else
        extra += chosen.length
          ? chosen.reduce((n, c) => n + c.price, 0)
          : pizzaGroups(product) &&
              g.required &&
              g.type !== "sizes" &&
              g.choices.length
            ? Math.min(...g.choices.map((c) => c.price))
            : 0;
    }
    return base + extra;
  }
  function summary(product, selected) {
    return product.groups
      .map((g) => {
        const v = selected[g.id],
          text =
            g.type === "text"
              ? v
              : g.choices
                  .filter((c) => (v || []).includes(c.id))
                  .map((c) => c.label)
                  .join(", ");
        return text
          ? g.title +
              (g.type === "flavors" ? ` (${v.length})` : "") +
              ": " +
              text
          : "";
      })
      .filter(Boolean)
      .join(" | ");
  }
  function sizeFor(selected) {
    return pizza?.sizes.choices.find((c) =>
      (selected[pizza.sizes.id] || []).includes(c.id),
    );
  }
  function limitFor(selected) {
    return sizeFor(selected)?.max_flavors || 1;
  }
  function capture() {
    if (!pizza || !units[unitIndex]) return;
    units[unitIndex].selected = read();
    units[unitIndex].note = notes.value;
  }
  function load() {
    if (!pizza) return;
    const unit = units[unitIndex];
    for (const g of current.groups) {
      const field = groups.querySelector(`[data-group="${g.id}"]`),
        v = unit.selected[g.id];
      if (g.type === "text") field.querySelector("input").value = v || "";
      else
        field
          .querySelectorAll("input")
          .forEach((i) => (i.checked = (v || []).includes(i.value)));
    }
    notes.value = unit.note || "";
  }
  function showError(text) {
    error.textContent = text;
    error.hidden = false;
  }
  function scrollStep() {
    search.value = "";
    document.querySelector(".picker-body").scrollTop = 0;
    error.hidden = true;
  }
  function selectUnit(index) {
    capture();
    unitIndex = index;
    stepIndex = 0;
    load();
    scrollStep();
    update();
  }
  function changeQuantity(delta) {
    capture();
    quantity = Math.max(1, Math.min(99, quantity + delta));
    if (pizza) {
      const size = read()[pizza.sizes.id];
      while (units.length < quantity)
        units.push({
          selected: { [pizza.sizes.id]: [...size] },
          note: "",
          count: units[unitIndex].count,
        });
      units.length = quantity;
      unitIndex = Math.min(unitIndex, quantity - 1);
      load();
    }
    update();
  }
  function choicePrice(g, c, selected) {
    if (g.type === "flavors" && current.pricing_mode === "fixed") return `<small>Incluído · ${money(sizeFor(selected)?.price || 0)} por pizza</small>`;
    if (g.type === "flavors")
      return `<small>${money(c.price + (sizeFor(selected)?.price || 0))} · pizza inteira</small>`;
    if (g.type === "sizes")
      return `<small>A partir de ${money((current.pricing_mode === "fixed" ? 0 : Math.min(...pizza.flavors.choices.map((c) => c.price))) + c.price)} · Até ${c.max_flavors || 1} sabores</small>`;
    if (/tamanho|fatias/.test(normal(g.title)))
      return `<small>${money(current.preco + c.price)}</small>`;
    return c.price ? `<small>+ ${money(c.price)}</small>` : "";
  }
  function update() {
    const selected = read();
    capture();
    if (pizza) document.querySelector("#picker-description").textContent =
      `Até ${limitFor(selected)} sabores neste tamanho${pizza.flavors.choices.length < limitFor(selected) ? ` · ${pizza.flavors.choices.length} ${pizza.flavors.choices.length === 1 ? "sabor disponível" : "sabores disponíveis"}` : ""}`;
    dialog.classList.toggle("pizza-wizard", !!pizza);
    const step = pizza
      ? stepIndex === -1
        ? pizza.sizes
        : steps[stepIndex]
      : null;
    for (const g of current.groups) {
      const field = groups.querySelector(`[data-group="${g.id}"]`);
      field.hidden = !!pizza && step?.id !== g.id;
      if (g.type !== "text") {
        const max = g.type === "flavors" ? units[unitIndex].count : g.max;
        const count = (selected[g.id] || []).length;
        field.querySelector(".picker-count").textContent = g.type === "flavors" && count < max ? `Falta${max-count === 1 ? "" : "m"} ${max-count}` : `${count} / ${max}`;
        field
          .querySelector(".picker-count")
          .classList.toggle(
            "incomplete",
            g.required && (g.type === "flavors" ? count !== max : !count),
          );
        field.querySelectorAll(".picker-choice").forEach((label) => {
          const input = label.querySelector("input"),
            c = g.choices.find((c) => c.id === input.value);
          label.querySelector(".picker-choice-price").innerHTML = choicePrice(
            g,
            c,
            selected,
          );
          label.classList.toggle("chosen", input.checked);
          const toggle = label.querySelector(".picker-choice-toggle");
          if (toggle) toggle.textContent = input.checked ? "−" : "+";
          label.hidden = !normal(c.label + " " + (c.description || "")).includes(normal(search.value));
        });
      }
    }
    const last = pizza && stepIndex === steps.length - 1;
    document.querySelector("#picker-name").textContent = pizza
      ? (stepIndex === -1 ? "Escolha o tamanho da pizza" : sizeFor(selected)?.label || current.nome)
      : current.nome;
    document.querySelector("#picker-photo").hidden = !!pizza && stepIndex > 0;
    document.querySelector("#picker-description").hidden =
      !!pizza && stepIndex > 0;
    document.querySelector("#pizza-progress").hidden = !pizza;
    document.querySelector("#pizza-progress").textContent = pizza
      ? `Pizza ${unitIndex + 1} de ${quantity} · ${stepIndex === -1 ? "Escolha o tamanho" : `Etapa ${stepIndex + 1} de ${steps.length} · ${step.title}`}`
      : "";
    dots.hidden = !pizza;
    if (pizza)
      dots.innerHTML = steps
        .map(
          (s, i) =>
            `<button type="button" data-step="${i}" class="pizza-step-dot ${i === stepIndex ? "active" : ""}" aria-label="Etapa ${i + 1}: ${safe(s.title)}" aria-current="${i === stepIndex ? "step" : "false"}" ${i > stepIndex ? "disabled" : ""}>${i + 1}</button>`,
        )
        .join("");
    unitNav.hidden = !pizza || quantity === 1;
    if (!unitNav.hidden)
      unitNav.innerHTML = units
        .map(
          (u, i) =>
            `<button type="button" class="chip ${i === unitIndex ? "active" : ""}" data-pizza-unit="${i}" aria-pressed="${i === unitIndex}">Pizza ${i + 1}${!current.groups.some(g => invalidGroup(g, u.selected, u.count)) ? " ✓" : ""}</button>`,
        )
        .join("");
    search.hidden =
      !pizza || !step || step.type === "text" || step.id === "__notes";
    search.placeholder = step ? `Buscar em ${step.title}…` : "Buscar opções…";
    document.querySelector("#picker-back").hidden = !pizza;
    document.querySelector("#picker-back").textContent =
      stepIndex > 0 ? "← Etapa anterior" : "← Alterar tamanho";
    document.querySelector("#picker-back").disabled = stepIndex === -1;
    document.querySelector("#picker-note-label").hidden =
      !current.notes.enabled || (!!pizza && step?.id !== "__notes");
    document.querySelector("#pizza-count-label").hidden =
      !pizza || step?.type !== "flavors";
    if (pizza) {
      const max = Math.min(limitFor(selected), pizza.flavors.choices.length),
        count = document.querySelector("#pizza-flavor-count");
      units[unitIndex].count = Math.max(
        1,
        Math.min(max, units[unitIndex].count),
      );
      count.innerHTML = Array.from(
        { length: max },
        (_, i) =>
          `<option value="${i + 1}">${i + 1} ${i ? "sabores" : "sabor"}</option>`,
      ).join("");
      count.value = String(units[unitIndex].count);
      document.querySelector("#pizza-count-help").textContent =
        `Escolha exatamente ${units[unitIndex].count} sabores para esta pizza. Limite do tamanho: ${limitFor(selected)}. ${max < limitFor(selected) ? `Há ${max} ${max === 1 ? "sabor disponível" : "sabores disponíveis"} no cardápio. ` : ""}${current.pricing_mode === "fixed" ? "O preço é o do tamanho, mais os complementos." : "O valor final é a média dos sabores escolhidos, mais os complementos."}`;
    }
    document.querySelector("#picker-submit").firstChild.textContent = pizza
      ? !last
        ? "Próximo · "
        : unitIndex < quantity - 1
          ? "Próxima pizza · "
          : editing
            ? "Salvar · "
            : "Inserir · "
      : editing
        ? "Salvar · "
        : "Adicionar · ";
    document.querySelector("#picker-quantity").textContent = quantity;
    document.querySelector("#picker-unit-price").textContent = money(
      price(current, selected),
    );
    document.querySelector(".picker-unit-line > span").textContent =
      pizza && current.pricing_mode !== "fixed" && !(selected[pizza.flavors.id] || []).length
        ? "A partir de, por pizza"
        : "Valor por unidade";
    document.querySelector("#picker-total").textContent = money(
      pizza
        ? units.reduce((sum, u) => sum + price(current, u.selected), 0)
        : price(current, selected) * quantity,
    );
    document.querySelector("#picker-minus").disabled = quantity === 1;
    document.querySelector("#picker-plus").disabled = quantity === 99;
  }
  function open(id, item, done, sizeId) {
    if (!adapter.canEdit()) return;
    current = products.get(id);
    if (!current) return;
    callback = done;
    pizza = pizzaGroups(current);
    editing = !!item;
    quantity = item?.quantidade || 1;
    unitIndex = 0;
    stepIndex = pizza && !sizeId && !item ? -1 : 0;
    previous = document.activeElement;
    const size =
      pizza?.sizes.choices.find(
        (c) => c.id === (sizeId || item?.opcoes?.[pizza.sizes.id]?.[0]),
      ) || pizza?.sizes.choices[0];
    const order = (g) =>
      g.type === "flavors"
        ? 2
        : /massa/.test(normal(g.title))
          ? 0
          : /borda/.test(normal(g.title))
            ? 1
            : 3;
    steps = pizza
      ? current.groups
          .filter((g) => g.type !== "sizes")
          .sort((a, b) => order(a) - order(b))
      : [];
    if (pizza && current.notes.enabled)
      steps.push({
        id: "__notes",
        type: "notes",
        title: current.notes.label || "Observação",
      });
    units = pizza
      ? Array.from({ length: quantity }, (_, i) => ({
          selected:
            i < (item?.quantidade_original ?? item?.quantidade ?? 0)
              ? JSON.parse(JSON.stringify(item.opcoes))
              : { [pizza.sizes.id]: sizeId ? [size.id] : [] },
          note: item?.observacao || "",
          count:
            item?.quantidade_sabores ||
            Math.min(size.max_flavors || 1, pizza.flavors.choices.length),
        }))
      : [];
    document.querySelector("#picker-description").textContent =
      current.descricao +
      (pizza
        ? ` · Até ${Math.min(size.max_flavors || 1, pizza.flavors.choices.length)} sabores neste tamanho`
        : "");
    const photo = document.querySelector(`[data-product="${id}"] .food`);
    document
      .querySelector("#picker-photo")
      .replaceChildren(
        ...[...(photo?.childNodes || [])].map((n) => n.cloneNode(true)),
      );
    groups.innerHTML = current.groups
      .map(
        (g) =>
          `<fieldset class="picker-group" data-group="${g.id}"><legend>${safe(g.title)} <span class="picker-count">${g.type === "text" ? "Texto" : "0 / " + g.max}</span></legend><small>${g.required ? "Obrigatório" : "Opcional"}${g.type === "multiple" ? " · Até " + g.max + " escolhas" : ""}</small>${g.type === "flavors" ? `<p class="pizza-flavor-rule">${current.pricing_mode === "fixed" ? "O preço é definido pelo tamanho. Os sabores estão incluídos." : "O valor final será a média dos preços dos sabores escolhidos."}</p>` : ""}${g.type === "text" ? `<input type="text" maxlength="60" aria-label="${safe(g.title)}">` : g.choices.map((c) => `<label class="picker-choice ${pizza && ["flavors", "multiple"].includes(g.type) ? "pizza-counter-choice" : ""}"><span class="picker-choice-caption">${c.photo ? `<img class="pizza-flavor-photo" src="${safe(restaurantURL("/media/" + encodeURIComponent(c.photo)))}" alt="${safe(c.label)}" loading="lazy">` : ""}${safe(c.label)}${c.description ? `<small class="picker-choice-description">${safe(c.description)}</small>` : ""}<span class="picker-choice-price"></span></span><input type="${["single", "sizes"].includes(g.type) ? "radio" : "checkbox"}" name="${g.id}" value="${c.id}">${pizza && ["flavors", "multiple"].includes(g.type) ? '<span class="picker-choice-toggle" aria-hidden="true">+</span>' : ""}</label>`).join("") + (!g.required && g.type === "single" ? `<button type="button" class="picker-clear" data-clear="${g.id}">Limpar escolha</button>` : "")}</fieldset>`,
      )
      .join("");
    for (const g of current.groups) {
      const field = groups.querySelector(`[data-group="${g.id}"]`),
        v = item?.opcoes?.[g.id];
      if (g.type === "text")
        field.querySelector("input").value = typeof v === "string" ? v : "";
      else
        field
          .querySelectorAll("input")
          .forEach(
            (i) => (i.checked = Array.isArray(v) && v.includes(i.value)),
          );
    }
    if (pizza) load();
    notes.value = current.notes.enabled ? item?.observacao || "" : "";
    document.querySelector("#picker-note-title").textContent =
      current.notes.label;
    notes.placeholder = current.notes.placeholder;
    scrollStep();
    update();
    document.body.classList.add("product-picker-open");
    dialog.showModal();
  }
  function invalidGroup(g, selected, count) {
    const v = selected[g.id] || (g.type === "text" ? "" : []);
    if (g.type === "flavors" && v.length !== count)
      return `Escolha exatamente ${count} sabores para esta pizza.`;
    if (g.required && !v.length) return "Preencha " + g.title + ".";
    return null;
  }
  function finish() {
    capture();
    if (pizza)
      for (let index = 0; index < units.length; index++)
        for (const g of current.groups) {
          const message = invalidGroup(
            g,
            units[index].selected,
            units[index].count,
          );
          if (message) {
            selectUnit(index);
            stepIndex =
              g.type === "sizes" ? -1 : steps.findIndex((s) => s.id === g.id);
            update();
            showError(message);
            return;
          }
        }
    function makeItem(selected, note, count, flavorCount) {
      const details = summary(current, selected);
      note = current.notes.enabled ? note.trim() : "";
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
      if (stored.length > (current.pizza_menu ? 2000 : 300)) return null;
      return {
        id: current.id,
        nome: current.nome,
        preco: price(current, selected),
        quantidade: count,
        quantidade_sabores: pizza ? flavorCount : undefined,
        observacao: note,
        opcoes: selected,
        opcoes_versao: current.version,
        resumo: details,
      };
    }
    const items = pizza
      ? units.map((u) => makeItem(u.selected, u.note, 1, u.count))
      : [makeItem(read(), notes.value, quantity)];
    if (items.some((i) => !i)) {
      showError(
        `Resuma os textos: as opções e a observação de cada pizza podem somar até ${current.pizza_menu ? 2000 : 300} caracteres.`,
      );
      return;
    }
    if (callback(pizza ? items : items[0]) === false) return;
    dialog.close();
  }
  form.addEventListener("submit", (event) => {
    event.preventDefault();
    if (!adapter.canEdit()) return;
    const selected = read();
    if (!pizza) {
      for (const g of current.groups) {
        const message = invalidGroup(g, selected);
        if (message) {
          showError(message);
          return;
        }
      }
      finish();
      return;
    }
    const step = stepIndex === -1 ? pizza.sizes : steps[stepIndex];
    if (step?.id !== "__notes") {
      const message = invalidGroup(step, selected, units[unitIndex].count);
      if (message) {
        showError(message);
        return;
      }
    }
    capture();
    if (stepIndex < steps.length - 1) {
      stepIndex++;
      scrollStep();
      update();
      return;
    }
    if (unitIndex < quantity - 1) {
      selectUnit(unitIndex + 1);
      return;
    }
    finish();
  });
  groups.addEventListener("change", (event) => {
    const field = event.target.closest("[data-group]"),
      g = current.groups.find((g) => g.id === field.dataset.group);
    if (pizza && g.type === "sizes") {
      const size = event.target.value;
      for (const u of units) {
        u.selected[pizza.sizes.id] = [size];
        u.selected[pizza.flavors.id] = [];
        u.count = Math.min(
          pizza.sizes.choices.find((c) => c.id === size).max_flavors || 1,
          pizza.flavors.choices.length,
        );
      }
      load();
    }
    const max = g.type === "flavors" ? units[unitIndex].count : g.max;
    if (
      ["multiple", "flavors"].includes(g.type) &&
      field.querySelectorAll("input:checked").length > max
    ) {
      event.target.checked = false;
      showError(`Escolha no máximo ${max} em ${g.title}.`);
    } else error.hidden = true;
    update();
  });
  groups.addEventListener("click", (event) => {
    const b = event.target.closest("[data-clear]");
    if (b) {
      b.closest("fieldset")
        .querySelectorAll("input")
        .forEach((i) => (i.checked = false));
      update();
    }
  });
  notes.addEventListener("input", capture);
  search.oninput = update;
  document.querySelector("#picker-back").onclick = () => {
    capture();
    stepIndex--;
    scrollStep();
    update();
  };
  document.querySelector("#pizza-flavor-count").onchange = (event) => {
    capture();
    units[unitIndex].count = Number(event.target.value);
    units[unitIndex].selected[pizza.flavors.id] = [];
    load();
    update();
  };
  dots.onclick = (event) => {
    const b = event.target.closest("[data-step]");
    if (b && !b.disabled) {
      capture();
      stepIndex = Number(b.dataset.step);
      scrollStep();
      update();
    }
  };
  unitNav.onclick = (event) => {
    const b = event.target.closest("[data-pizza-unit]");
    if (b) selectUnit(Number(b.dataset.pizzaUnit));
  };
  document.querySelector("#picker-close").onclick = () => dialog.close();
  document.querySelector("#picker-minus").onclick = () => changeQuantity(-1);
  document.querySelector("#picker-plus").onclick = () => changeQuantity(1);
  dialog.addEventListener("close", () => {
    document.body.classList.remove("product-picker-open");
    previous?.focus();
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
      const v = selected[g.id];
      if (g.type === "text") {
        if (typeof v !== "string" || v.length > 60 || (g.required && !v.trim()))
          return null;
      } else if (
        !Array.isArray(v) ||
        v.length > g.max ||
        new Set(v).size !== v.length ||
        (g.required && !v.length) ||
        v.some((id) => !g.choices.some((c) => c.id === id))
      )
        return null;
    }
    const info = pizzaGroups(p);
    if (info) {
      const size = info.sizes.choices.find((c) =>
        (selected[info.sizes.id] || []).includes(c.id),
      );
      if (
        !size ||
        !Number.isInteger(item.quantidade_sabores) ||
        item.quantidade_sabores < 1 ||
        item.quantidade_sabores > size.max_flavors ||
        selected[info.flavors.id].length !== item.quantidade_sabores
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
      const choose = () =>
        open(+card.dataset.product, null, value.onAdd, card.dataset.size);
      card.onclick = choose;
      card.onkeydown = (event) => {
        if (event.target === card && ["Enter", " "].includes(event.key)) {
          event.preventDefault();
          choose();
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
    document.querySelectorAll(".catalog-chips .chip").forEach(
      (button) =>
        (button.onclick = () => {
          category = button.dataset.category;
          document.querySelectorAll(".catalog-chips .chip").forEach((chip) => {
            chip.classList.toggle("active", chip === button);
            chip.setAttribute("aria-pressed", String(chip === button));
          });
          filter();
        }),
    );
  }
  function line(item, index) {
    const p = products.get(item.id),
      info = pizzaGroups(p);
    if (info) {
      const size = info.sizes.choices.find((c) =>
        (item.opcoes[info.sizes.id] || []).includes(c.id),
      );
      const photo = document.querySelector(
        `[data-product="${item.id}"] .food img`,
      );
      const sections = p.groups
        .filter((g) => g.type !== "sizes")
        .map((g) => {
          const v = item.opcoes[g.id],
            choices =
              g.type === "text"
                ? []
                : g.choices.filter((c) => (v || []).includes(c.id));
          const values =
            g.type === "text"
              ? v
                ? `<li>${safe(v)}</li>`
                : ""
              : choices
                  .map(
                    (c) =>
                      `<li>${safe(c.label)}${c.price && g.type !== "flavors" ? ` <small>(+ ${money(c.price)})</small>` : ""}</li>`,
                  )
                  .join("");
          return values
            ? `<div><strong>${safe(g.title)}</strong><ul>${values}</ul></div>`
            : "";
        })
        .join("");
      return `<article class="cart-item pizza-cart-item"><div class="pizza-cart-top"><div><h3>${item.quantidade}× ${safe(size?.label || p.nome)}</h3><small>${safe(p.nome)}</small></div>${photo ? `<img src="${safe(photo.src)}" alt="" loading="lazy">` : '<span class="pizza-cart-emoji" aria-hidden="true">🍕</span>'}</div><div class="pizza-cart-options">${sections}${item.observacao ? `<div><strong>${safe(p.notes.label)}</strong><p>${safe(item.observacao)}</p></div>` : ""}</div><div class="pizza-cart-actions"><button type="button" class="cart-edit-options" data-edit="${index}">✎ Editar</button><button type="button" class="cart-edit-options" data-remove="${index}">Remover</button><strong>${money(item.preco * item.quantidade)}</strong></div></article>`;
    }
    return `<div class="cart-item"><b>${safe(item.nome)}</b>${item.resumo ? `<p class="cart-options-summary">${safe(item.resumo)}</p>` : ""}${item.observacao ? `<p class="cart-options-summary">${safe(p?.notes.label || "Observação")}: ${safe(item.observacao)}</p>` : ""}<div class="quantity"><button data-change="-1" data-index="${index}" aria-label="Diminuir ${safe(item.nome)}">−</button><span>${item.quantidade}</span><button data-change="1" data-index="${index}" aria-label="Aumentar ${safe(item.nome)}">+</button><strong>${money(item.preco * item.quantidade)}</strong></div><button type="button" class="cart-edit-options" data-edit="${index}">Editar opções e observação</button></div>`;
  }
  return {
    bind,
    restore,
    line,
    isPizza: (item) => !!pizzaGroups(products.get(item.id)),
    edit: (item, done) => open(item.id, item, done),
  };
})();
