"use strict";
const bag = document.querySelector("#bag"),
  cartEl = document.querySelector("#cart"),
  send = document.querySelector("#send"),
  mobileCart = document.querySelector("#mobile-cart"),
  mode = document.querySelector("#online-mode"),
  payment = document.querySelector("#online-payment");
let cart = [],
  sending = false,
  pending = null,
  category = "all";
const storageKey = "restaurant-online-cart",
  tokenKey = "restaurant-online-attempt";
const catalog = new Map(
  [...document.querySelectorAll(".add")].map((b) => [
    +b.dataset.id,
    { id: +b.dataset.id, nome: b.dataset.name, preco: +b.dataset.price },
  ]),
);
function save() {
  try {
    sessionStorage.setItem(
      storageKey,
      JSON.stringify({
        itens: cart.map(({ id, quantidade, observacao }) => ({
          id,
          quantidade,
          observacao,
        })),
        modalidade: mode.value,
        pagamento: payment.value,
      }),
    );
  } catch {}
}
try {
  const data = JSON.parse(sessionStorage.getItem(storageKey) || "null");
  if (data && Array.isArray(data.itens)) {
    cart = data.itens
      .filter(
        (i) =>
          catalog.has(i.id) &&
          Number.isInteger(i.quantidade) &&
          i.quantidade > 0 &&
          i.quantidade <= 99,
      )
      .slice(0, 100)
      .map((i) => ({
        ...catalog.get(i.id),
        quantidade: i.quantidade,
        observacao: String(i.observacao || "").slice(0, 300),
      }));
    if ([...mode.options].some((o) => o.value === data.modalidade))
      mode.value = data.modalidade;
    if ([...payment.options].some((o) => o.value === data.pagamento))
      payment.value = data.pagamento;
  }
} catch {}
function setBag(open) {
  document.body.classList.toggle("bag-open", open);
  document.querySelector("#bag-backdrop").hidden = !open;
  mobileCart.setAttribute("aria-expanded", String(open));
  if (open) {
    bag.setAttribute("role", "dialog");
    bag.setAttribute("aria-modal", "true");
    bag.setAttribute("aria-label", "Sua sacola e finalização");
    document.querySelector(".bag-close").focus();
  } else {
    bag.removeAttribute("role");
    bag.removeAttribute("aria-modal");
    document.querySelector("#bag-backdrop").hidden = true;
    mobileCart.focus();
  }
}
mobileCart.onclick = () => setBag(true);
document.querySelector(".bag-close").onclick = () => setBag(false);
document.querySelector("#bag-backdrop").onclick = () => setBag(false);
window.addEventListener("keydown", (e) => {
  if (e.key === "Escape" && document.body.classList.contains("bag-open")) setBag(false);
  if (e.key === "Tab" && document.body.classList.contains("bag-open")) {
    const nodes = [
      ...bag.querySelectorAll(
        "button:not(:disabled), input:not(:disabled), textarea:not(:disabled), select:not(:disabled), a",
      ),
    ].filter((n) => n.offsetParent !== null);
    if (e.shiftKey && document.activeElement === nodes[0]) {
      e.preventDefault();
      nodes.at(-1).focus();
    } else if (!e.shiftKey && document.activeElement === nodes.at(-1)) {
      e.preventDefault();
      nodes[0].focus();
    }
  }
});
window.matchMedia("(min-width:851px)").addEventListener("change", (e) => {
  if (e.matches) {
    document.body.classList.remove("bag-open");
    document.querySelector("#bag-backdrop").hidden = true;
    bag.removeAttribute("role");
    bag.removeAttribute("aria-modal");
  }
});
function totals() {
  const subtotal = cart.reduce((sum, i) => sum + i.preco * i.quantidade, 0),
    fee = mode.value === "entrega" ? Number(bag.dataset.fee) : 0,
    count = cart.reduce((sum, i) => sum + i.quantidade, 0);
  document.querySelector("#subtotal").textContent = money(subtotal);
  document.querySelector("#delivery-fee").textContent = money(fee);
  document.querySelector("#total").textContent = money(subtotal + fee);
  document.querySelector("#mobile-total").textContent = money(subtotal + fee);
  document.querySelector("#mobile-count").textContent = count;
  document.querySelector("#cart-count").textContent = count;
  if (send) {
    send.disabled =
      !cart.length || sending || !navigator.onLine || bag.dataset.active !== "yes";
    send.textContent = sending
      ? "Enviando pedido…"
      : pending
        ? "Reenviar a mesma tentativa →"
        : bag.dataset.customer === "yes"
          ? "Confirmar meu pedido →"
          : "Entrar para fazer o pedido →";
  }
  return subtotal + fee;
}
function draw() {
  cartEl.innerHTML =
    cart
      .map(
        (i, k) => /* HTML */ `
          <div class="cart-item">
            <b>${escapeHTML(i.nome)}</b>
            <div class="quantity">
              <button
                data-change="-1"
                data-index="${k}"
                aria-label="Diminuir ${escapeHTML(i.nome)}"
              >
                −
              </button>
              <span>${i.quantidade}</span>
              <button
                data-change="1"
                data-index="${k}"
                aria-label="Aumentar ${escapeHTML(i.nome)}"
              >
                +
              </button>
              <strong>${money(i.preco * i.quantidade)}</strong>
            </div>
            <textarea
              rows="1"
              data-note="${k}"
              maxlength="300"
              placeholder="Observação (ex.: sem cebola)"
              aria-label="Observação para ${escapeHTML(i.nome)}"
            >
${escapeHTML(i.observacao)}</textarea>
          </div>
        `,
      )
      .join("") ||
    '<p class="empty">Sua sacola está vazia.<br>Escolha algo gostoso no cardápio.</p>';
  totals();
  save();
}
function lock(value) {
  bag
    .querySelectorAll(
      ".checkout-details input,.checkout-details select,#cart button,#cart textarea",
    )
    .forEach((e) => (e.disabled = value));
}
document.querySelectorAll(".add").forEach(
  (b) =>
    (b.onclick = () => {
      if (sending || pending) {
        toast(
          "Conclua a tentativa atual ou confira seus pedidos antes de alterar a sacola.",
        );
        return;
      }
      const item = cart.find((i) => i.id === +b.dataset.id);
      if (item) item.quantidade = Math.min(99, item.quantidade + 1);
      else cart.push({ ...catalog.get(+b.dataset.id), quantidade: 1, observacao: "" });
      draw();
      b.textContent = "✓";
      setTimeout(() => (b.textContent = "+"), 600);
    }),
);
cartEl.onclick = (e) => {
  if (sending || pending) return;
  const b = e.target.closest("[data-change]");
  if (!b) return;
  const k = +b.dataset.index;
  cart[k].quantidade = Math.min(99, cart[k].quantidade + +b.dataset.change);
  if (cart[k].quantidade <= 0) cart.splice(k, 1);
  draw();
};
cartEl.oninput = (e) => {
  if (e.target.dataset.note !== undefined) {
    cart[+e.target.dataset.note].observacao = e.target.value;
    save();
  }
};
function checkout() {
  const delivery = mode.value === "entrega",
    fields = document.querySelector("#checkout-address");
  fields.hidden = !delivery;
  fields
    .querySelectorAll("input")
    .forEach((input) => (input.required = delivery && input.name !== "telefone"));
  document.querySelector("#change-label").hidden = payment.value !== "dinheiro";
  totals();
  save();
}
mode.onchange = checkout;
payment.onchange = checkout;
function filter() {
  const q = document.querySelector("#search").value.toLocaleLowerCase("pt-BR");
  let count = 0;
  document.querySelectorAll(".product").forEach((p) => {
    p.hidden =
      !(category === "all" || p.dataset.category === category) ||
      !p.dataset.name.includes(q);
    if (!p.hidden) count++;
  });
  document.querySelector("#empty-search").hidden = !!count;
}
document.querySelector("#search").oninput = filter;
document.querySelectorAll(".chip").forEach(
  (b) =>
    (b.onclick = () => {
      category = b.dataset.category;
      document.querySelectorAll(".chip").forEach((c) => {
        c.classList.toggle("active", c === b);
        c.setAttribute("aria-pressed", String(c === b));
      });
      filter();
    }),
);
function token() {
  try {
    let t = sessionStorage.getItem(tokenKey);
    if (t) return t;
    const bytes = crypto.getRandomValues(new Uint8Array(16));
    t = Array.from(bytes, (b) => b.toString(16).padStart(2, "0")).join("");
    sessionStorage.setItem(tokenKey, t);
    return t;
  } catch {
    return Array.from(crypto.getRandomValues(new Uint8Array(16)), (b) =>
      b.toString(16).padStart(2, "0"),
    ).join("");
  }
}
function done(id) {
  cart = [];
  pending = null;
  try {
    sessionStorage.removeItem(storageKey);
    sessionStorage.removeItem(tokenKey);
  } catch {}
  toast("Pedido #" + id + " recebido!");
  window.location.assign("/meus-pedidos");
}
if (send)
  send.onclick = async () => {
    if (sending) return;
    if (bag.dataset.customer !== "yes") {
      save();
      window.location.assign("/login");
      return;
    }
    if (!pending) {
      const payload = {
        chave: token(),
        modalidade: mode.value,
        forma_pagamento: payment.value,
        troco_para:
          payment.value === "dinheiro"
            ? document.querySelector("#change-for").value
            : "",
        total_previsto: totals(),
        itens: cart.map(({ id, quantidade, observacao }) => ({
          id,
          quantidade,
          observacao,
        })),
      };
      if (mode.value === "entrega") {
        const fields = [...document.querySelectorAll("#checkout-address input")];
        for (const input of fields) {
          if (!input.checkValidity()) {
            input.reportValidity();
            return;
          }
          payload[input.name] = input.value.trim();
        }
      }
      pending = payload;
    }
    sending = true;
    lock(true);
    totals();
    try {
      const result = await api("/api/cliente/pedidos", pending);
      done(result.id);
    } catch (e) {
      if (e.status) {
        pending = null;
        lock(false);
        toast(e.message);
      } else {
        toast(
          "Não foi possível confirmar a resposta. Você pode reenviar a mesma tentativa com segurança ou conferir Meus pedidos.",
        );
      }
    } finally {
      sending = false;
      totals();
    }
  };
window.addEventListener("offline", totals);
window.addEventListener("online", totals);
draw();
checkout();
if (bag.dataset.customer === "yes") {
  try {
    const savedToken = sessionStorage.getItem(tokenKey);
    if (savedToken)
      api("/api/cliente/envios/" + encodeURIComponent(savedToken))
        .then((result) => {
          if (result.id) done(result.id);
        })
        .catch(() => {});
  } catch {}
}
