"use strict";
document.addEventListener("DOMContentLoaded", () => {
  const cpf = document.querySelector('[name="cpf"]');
  if (cpf) {
    cpf.maxLength = 14;
    cpf.addEventListener("input", () => {
      cpf.value = cpf.value
        .replace(/\D/g, "")
        .slice(0, 11)
        .replace(/^(\d{3})(\d)/, "$1.$2")
        .replace(/^(\d{3})\.(\d{3})(\d)/, "$1.$2.$3")
        .replace(/(\d{3})\.(\d{3})\.(\d{3})(\d)/, "$1.$2.$3-$4");
    });
  }
  document
    .querySelectorAll('input[type="date"],input[type="number"][step="0.01"]')
    .forEach((original) => {
      const date = original.type === "date",
        display = document.createElement("input");
      display.type = "text";
      display.inputMode = date ? "numeric" : "decimal";
      display.placeholder = date ? "dd/mm/aaaa" : "0,00";
      display.required = original.required;
      display.maxLength = date ? 10 : 20;
      display.setAttribute(
        "aria-label",
        original.getAttribute("aria-label") ||
          (date ? "Data (dd/mm/aaaa)" : "Valor em reais"),
      );
      if (original.id) {
        display.id = original.id + "-br";
        document
          .querySelectorAll('label[for="' + original.id + '"]')
          .forEach((l) => (l.htmlFor = display.id));
      }
      display.dataset.brField = "1";
      original.type = "hidden";
      original.required = false;
      original.after(display);
      const d = Object.getOwnPropertyDescriptor(HTMLInputElement.prototype, "value");
      function format() {
        const v = d.get.call(original);
        display.value = !v
          ? ""
          : date
            ? v.split("-").reverse().join("/")
            : Number(v).toLocaleString("pt-BR", {
                minimumFractionDigits: 2,
                maximumFractionDigits: 2,
              });
      }
      Object.defineProperty(original, "value", {
        configurable: true,
        get() {
          return d.get.call(this);
        },
        set(v) {
          d.set.call(this, v);
          format();
        },
      });
      function sync() {
        let v = display.value.trim(),
          valid = !v;
        if (date && v) {
          const m = /^(\d{2})\/(\d{2})\/(\d{4})$/.exec(v);
          if (m) {
            const x = new Date(+m[3], +m[2] - 1, +m[1]);
            valid =
              x.getFullYear() === +m[3] &&
              x.getMonth() === +m[2] - 1 &&
              x.getDate() === +m[1];
            v = m[3] + "-" + m[2] + "-" + m[1];
          }
        } else if (v) {
          valid = /^(?:\d+|\d{1,3}(?:\.\d{3})+)(?:,\d{1,2})?$/.test(v);
          v = v.replace(/\./g, "").replace(",", ".");
        }
        display.setCustomValidity(
          valid
            ? ""
            : date
              ? "Informe uma data válida: dd/mm/aaaa."
              : "Use um valor como 1.234,56.",
        );
        d.set.call(original, valid ? v : "");
        original.dispatchEvent(new Event("input", { bubbles: true }));
        if (valid) original.dispatchEvent(new Event("change", { bubbles: true }));
      }
      display.addEventListener("input", () => {
        if (date)
          display.value = display.value
            .replace(/\D/g, "")
            .slice(0, 8)
            .replace(/^(\d{2})(\d)/, "$1/$2")
            .replace(/^(\d{2})\/(\d{2})(\d)/, "$1/$2/$3");
        sync();
      });
      display.addEventListener("blur", () => {
        sync();
        if (display.checkValidity()) format();
      });
      format();
    });
  document.addEventListener(
    "click",
    (event) => {
      if (!event.target.closest("#send")) return;
      const invalid = [...document.querySelectorAll("[data-br-field]")].find(
        (i) => !i.disabled && !i.closest("[hidden]") && !i.checkValidity(),
      );
      if (invalid) {
        event.preventDefault();
        event.stopImmediatePropagation();
        invalid.reportValidity();
      }
    },
    true,
  );
  const emoji = document.querySelector("#product-emoji"),
    buttons = document.querySelectorAll("[data-product-icon]");
  const selected = () =>
    buttons.forEach((b) =>
      b.setAttribute("aria-pressed", String(b.dataset.productIcon === emoji?.value)),
    );
  buttons.forEach((b) =>
    b.addEventListener("click", () => {
      emoji.value = b.dataset.productIcon;
      selected();
    }),
  );
  emoji?.addEventListener("input", selected);
  selected();
});
